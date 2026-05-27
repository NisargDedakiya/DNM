"""
Scanner pipeline service.
Orchestrates nuclei, dalfox and ffuf runs with scope validation,
approval gating, live Redis streaming, and AI triage.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ai_triage_service import ai_triage
from backend.utils.approval_gate import ApprovalGate
from backend.utils.scope_validator import ScopeValidator, ScopeViolationError

logger = logging.getLogger(__name__)

# Temp directory for scan artefacts (logs, target lists, output files)
TMP = Path("/tmp/dnm_scans")
TMP.mkdir(parents=True, exist_ok=True)

# Maps detected tech stack to most relevant nuclei template directories
TECH_TEMPLATES: dict[str, list[str]] = {
    "wordpress": ["vulnerabilities/wordpress", "default-logins/cms", "exposures/"],
    "laravel":   ["technologies/laravel", "vulnerabilities/generic", "exposures/"],
    "django":    ["technologies/django", "vulnerabilities/python"],
    "rails":     ["technologies/ruby-on-rails"],
    "spring":    ["technologies/spring", "cves/"],
    "nodejs":    ["technologies/nodejs", "vulnerabilities/javascript"],
    "fastapi":   ["technologies/", "misconfiguration/", "exposures/"],
    "php":       ["technologies/php", "vulnerabilities/generic", "exposures/"],
    "default":   ["exposures/", "misconfiguration/", "default-logins/", "cves/"],
}


class ScannerService:
    """
    Thin orchestration layer that:
    1. Validates targets against program scope_json
    2. Requests human approval via ApprovalGate
    3. Runs the external tool (nuclei / dalfox / ffuf) via asyncio subprocess
    4. Streams every output line to Redis for WebSocket consumption
    5. Passes raw output to the AI triage engine
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _stream_to_redis(
        self,
        cmd: str,
        scan_id: UUID,
        log_label: str,
        org_id: UUID,
    ) -> str:
        """
        Execute *cmd* via shell, publish every non-empty output line to Redis
        on the scan-output channel, append to a local log file, and return
        the full concatenated output string for AI triage.

        Channel format: ``scan:<scan_id>:output``  (consumed by WebSocket manager)
        Alert channel : ``alerts:<org_id>``         (same as Phase-16 pattern)
        """
        from backend.core.redis import get_redis

        redis = await get_redis()
        channel = f"scan:{scan_id}:output"
        log_path = TMP / f"{scan_id}_{log_label}.log"
        all_lines: list[str] = []

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout is None:
            await proc.wait()
            logger.warning("%s: proc.stdout is None for scan %s", log_label, scan_id)
            return ""

        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            all_lines.append(line)
            await redis.publish(
                channel,
                json.dumps({"type": "output", "line": line, "tool": log_label}),
            )
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

        await proc.wait()
        full_output = " ".join(all_lines)
        logger.info(
            "%s completed for scan %s — %d lines captured",
            log_label,
            scan_id,
            len(all_lines),
        )
        return full_output

    # Keep the old private name as an alias so legacy callers still work
    async def _run(self, cmd: str, scan_id: UUID, label: str) -> str:
        """Backward-compat alias for _stream_to_redis (org_id not used for channel)."""
        from backend.core.redis import get_redis

        redis = await get_redis()
        channel = f"scan:{scan_id}"
        log_path = TMP / f"{scan_id}_{label}.log"
        output_lines: list[str] = []

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        if proc.stdout is None:
            await proc.wait()
            return ""

        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            output_lines.append(line)
            await redis.publish(channel, json.dumps({"type": "output", "line": line}))
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

        await proc.wait()
        return " ".join(output_lines)

    # ------------------------------------------------------------------
    # Public scanner methods
    # ------------------------------------------------------------------

    async def run_nuclei(
        self,
        db: AsyncSession,
        targets: list[str],
        tech_stack: str,
        scan_id: UUID,
        program_id: UUID,
        org_id: UUID,
        scope_json: dict,
        stealth: bool = False,
        created_by_id: UUID | None = None,
    ) -> list:
        """
        Run nuclei against *targets*.

        Steps:
        1. Scope validation — filter targets against program scope_json
        2. Approval gate — wait for human approval before ANY active scan
        3. Build nuclei command using tech-stack-specific templates
        4. Stream output to Redis; return AI-triaged findings
        """
        scope_json = scope_json or {}

        valid, invalid = ScopeValidator.filter_valid(targets, scope_json)
        if invalid:
            logger.warning(
                "%d targets out of scope and skipped (scan %s)", len(invalid), scan_id
            )
        if not valid:
            logger.error(
                "No valid targets after scope check — aborting nuclei scan %s", scan_id
            )
            return []

        approved = await ApprovalGate.request(
            scan_id,
            f"Run nuclei vulnerability scan on {len(valid)} targets? Tech: {tech_stack}",
            valid[:5],
            "nuclei",
            org_id,
        )
        if not approved:
            logger.info("Nuclei scan %s denied by user — not running", scan_id)
            return []

        tmpl_dirs = TECH_TEMPLATES.get(tech_stack.lower().strip(), TECH_TEMPLATES["default"])
        tmpls = " ".join(f"-t {t}" for t in tmpl_dirs)
        tfile = str(TMP / f"{scan_id}_nuclei_targets.txt")
        Path(tfile).write_text("\n".join(valid), encoding="utf-8")

        rl = "2" if stealth else "20"
        cc = "1" if stealth else "10"
        cmd = (
            f"nuclei -l {tfile} {tmpls} "
            f"-severity medium,high,critical -json "
            f"-rl {rl} -c {cc} -timeout 10 2>&1"
        )

        output = await self._stream_to_redis(cmd, scan_id, "nuclei", org_id)
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "nuclei", "tech_stack": tech_stack},
            created_by_id=created_by_id,
        )

    async def run_dalfox(
        self,
        db: AsyncSession,
        urls: list[str],
        scan_id: UUID,
        program_id: UUID,
        org_id: UUID,
        scope_json: dict,
        created_by_id: UUID | None = None,
    ) -> list:
        """
        Run dalfox XSS scanner against *urls*.
        Scope-checks, approval-gates, then streams output and triages findings.
        """
        scope_json = scope_json or {}

        valid, _ = ScopeValidator.filter_valid(urls, scope_json)
        if not valid:
            logger.info("No in-scope URLs for dalfox on scan %s", scan_id)
            return []

        approved = await ApprovalGate.request(
            scan_id,
            f"Run XSS scanning (dalfox) on {len(valid)} URLs?",
            valid[:5],
            "dalfox",
            org_id,
        )
        if not approved:
            logger.info("Dalfox scan %s denied by user — not running", scan_id)
            return []

        ufile = str(TMP / f"{scan_id}_dalfox_urls.txt")
        Path(ufile).write_text("\n".join(valid), encoding="utf-8")
        cmd = f"dalfox file {ufile} --silence 2>&1"

        output = await self._stream_to_redis(cmd, scan_id, "dalfox", org_id)
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "dalfox_xss"},
            created_by_id=created_by_id,
        )

    async def run_ffuf(
        self,
        db: AsyncSession,
        url: str,
        wordlist: str,
        scan_id: UUID,
        program_id: UUID,
        org_id: UUID,
        scope_json: dict,
        stealth: bool = False,
        created_by_id: UUID | None = None,
    ) -> list:
        """
        Run ffuf directory fuzzer against a single *url*.
        Scope-checks, approval-gates, then streams output and triages findings.
        """
        scope_json = scope_json or {}

        ScopeValidator.validate_or_raise(url, scope_json)

        approved = await ApprovalGate.request(
            scan_id,
            f"Run directory fuzzing (ffuf) on {url}?",
            [url],
            "ffuf",
            org_id,
        )
        if not approved:
            logger.info("Ffuf scan %s denied by user — not running", scan_id)
            return []

        threads = "3" if stealth else "40"
        rate = "5" if stealth else "100"
        output_file = str(TMP / f"{scan_id}_ffuf.json")
        rate_flag = f"-rate {rate} " if stealth else ""
        cmd = (
            f"ffuf -u {url}/FUZZ -w {wordlist} "
            f"-mc 200,201,204,301,302,403 "
            f"-t {threads} {rate_flag}"
            f"-o {output_file} -of json 2>&1"
        )

        output = await self._stream_to_redis(cmd, scan_id, "ffuf", org_id)
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "ffuf_fuzzing", "target_url": url},
            created_by_id=created_by_id,
        )


# Singleton — import this everywhere that needs scanner execution
scanner_service = ScannerService()