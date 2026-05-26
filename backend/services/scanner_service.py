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
TMP = Path("/tmp/dnm")
TMP.mkdir(parents=True, exist_ok=True)


# Tech stack -> best nuclei template directories
TECH_TEMPLATES = {
    "wordpress": ["vulnerabilities/wordpress", "default-logins/cms", "exposures/"],
    "laravel": ["technologies/laravel", "vulnerabilities/generic", "exposures/"],
    "django": ["technologies/django", "vulnerabilities/python"],
    "rails": ["technologies/ruby-on-rails"],
    "spring": ["technologies/spring", "cves/"],
    "nodejs": ["technologies/nodejs", "vulnerabilities/javascript"],
    "fastapi": ["technologies/", "misconfiguration/", "exposures/"],
    "default": ["exposures/", "misconfiguration/", "default-logins/", "cves/"],
}


class ScannerService:
    async def _run(self, cmd: str, scan_id: UUID, label: str) -> str:
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
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + " ")

        await proc.wait()
        return " ".join(output_lines)

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
    ) -> list:
        scope_json = scope_json or {}

        valid, invalid = ScopeValidator.filter_valid(targets, scope_json)
        if invalid:
            logger.warning("%s targets out of scope - skipped", len(invalid))
        if not valid:
            return []

        approved = await ApprovalGate.request(
            scan_id,
            f"Run nuclei on {len(valid)} targets ({tech_stack})?",
            valid[:5],
            "nuclei",
            org_id,
        )
        if not approved:
            return []

        tmpl_dirs = TECH_TEMPLATES.get(tech_stack.lower(), TECH_TEMPLATES["default"])
        tmpls = " ".join(f"-t {t}" for t in tmpl_dirs)
        tfile = str(TMP / f"{scan_id}_targets.txt")
        Path(tfile).write_text(" ".join(valid), encoding="utf-8")
        rl = "2" if stealth else "20"
        cc = "1" if stealth else "10"
        cmd = (
            f"nuclei -l {tfile} {tmpls} -severity medium,high,critical -json "
            f"-rl {rl} -c {cc} 2>&1"
        )
        output = await self._run(cmd, scan_id, "nuclei")
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "nuclei", "tech_stack": tech_stack},
        )

    async def run_dalfox(
        self,
        db: AsyncSession,
        urls: list[str],
        scan_id: UUID,
        program_id: UUID,
        org_id: UUID,
        scope_json: dict,
    ) -> list:
        scope_json = scope_json or {}

        valid, _ = ScopeValidator.filter_valid(urls, scope_json)
        if not valid:
            return []

        approved = await ApprovalGate.request(
            scan_id,
            f"Run XSS scan on {len(valid)} URLs?",
            valid[:5],
            "dalfox",
            org_id,
        )
        if not approved:
            return []

        ufile = str(TMP / f"{scan_id}_urls.txt")
        Path(ufile).write_text(" ".join(valid), encoding="utf-8")
        cmd = f"dalfox file {ufile} --silence 2>&1"
        output = await self._run(cmd, scan_id, "dalfox")
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "dalfox_xss"},
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
    ) -> list:
        scope_json = scope_json or {}

        ScopeValidator.validate_or_raise(url, scope_json)
        approved = await ApprovalGate.request(
            scan_id,
            f"Run directory fuzzing on {url}?",
            [url],
            "ffuf",
            org_id,
        )
        if not approved:
            return []

        t = "3" if stealth else "40"
        r = "5" if stealth else "100"
        cmd = f"ffuf -u {url}/FUZZ -w {wordlist} -mc 200,201,301,302,403 -t {t} -rate {r} 2>&1"
        output = await self._run(cmd, scan_id, "ffuf")
        return await ai_triage.triage(
            db,
            output,
            scan_id,
            program_id,
            org_id,
            {"scan_type": "ffuf", "target_url": url},
        )


scanner_service = ScannerService()