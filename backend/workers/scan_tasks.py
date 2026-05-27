"""
ARQ background task definitions for scanner pipeline execution.
Matches the ARQ task format established in backend/workers/scheduler.py.
Tasks are registered in WorkerSettings in arq_worker.py.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

from arq import Retry

from backend.database.session import AsyncSessionLocal
from backend.models.scan import ScanStatus
from backend.services.ai_triage_service import ai_triage
from backend.services.scan_service import ScanService
from backend.services.scanner_service import scanner_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _publish_event(ctx: Any, channel: str, payload: dict) -> None:
    """Publish a JSON payload to a Redis pub/sub channel."""
    redis = None
    if isinstance(ctx, dict):
        redis = ctx.get("redis")
    if redis is None:
        from backend.core.redis import get_redis
        redis = await get_redis()
    await redis.publish(channel, json.dumps(payload))


def _extract_urls(findings: list[Any]) -> list[str]:
    """Extract unique endpoint URLs from a list of Finding objects or dicts."""
    urls: list[str] = []
    for finding in findings:
        endpoint = getattr(finding, "endpoint", None)
        if endpoint:
            urls.append(endpoint)
            continue
        if isinstance(finding, dict):
            endpoint = finding.get("endpoint") or finding.get("affected_url")
            if endpoint:
                urls.append(endpoint)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        cleaned = re.sub(r"\s+", "", str(url)).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique_urls.append(cleaned)
    return unique_urls


async def _mark_scan_status(db, scan_id: UUID, status: ScanStatus) -> None:
    """Update scan status in the database and commit."""
    scan = await ScanService.update_scan_status(db, scan_id, status)
    if scan is None:
        raise RuntimeError(f"Scan {scan_id} not found during status update")
    await db.commit()


# ---------------------------------------------------------------------------
# ARQ task: full scan pipeline (nuclei → dalfox → chain detection)
# ---------------------------------------------------------------------------

async def run_full_scan(
    ctx,
    scan_id: str,
    program_id: str,
    org_id: str,
    targets: list[str],
    tech_stack: str,
    scope_json: dict,
    stealth: bool = False,
    created_by_id: str | None = None,
):
    """
    Full scanner pipeline ARQ task.

    Steps
    -----
    1. Mark scan status → running
    2. Publish scan_started event
    3. Run nuclei (scope validated, approval gated)
    4. Run dalfox on URLs discovered from nuclei findings
    5. Detect vulnerability chains via AI triage
    6. Mark scan status → completed
    7. Publish scan_complete event with summary counts

    The task raises ``arq.Retry`` on unexpected failure so the ARQ worker
    will retry according to its policy.

    Args:
        ctx: ARQ worker context dict (may contain ``redis`` client).
        scan_id: UUID string of the Scan record.
        program_id: UUID string of the Program.
        org_id: UUID string of the Organisation.
        targets: Initial target list (domains / IPs / URLs).
        tech_stack: Technology stack hint for nuclei template selection.
        scope_json: Program's scope JSON from the database.
        stealth: If True, use low-rate / low-concurrency scanner settings.
        created_by_id: Optional UUID string of the user who triggered the scan.
    """
    async with AsyncSessionLocal() as db:
        scan_uuid = UUID(scan_id)
        program_uuid = UUID(program_id)
        org_uuid = UUID(org_id)
        created_by_uuid = UUID(created_by_id) if created_by_id else None

        try:
            # Step 1 — mark running
            await _mark_scan_status(db, scan_uuid, ScanStatus.running)

            # Step 2 — announce scan start
            await _publish_event(
                ctx,
                f"alerts:{org_uuid}",
                {
                    "event": "scan_started",
                    "scan_id": scan_id,
                    "program_id": program_id,
                    "org_id": org_id,
                    "tech_stack": tech_stack,
                    "target_count": len(targets),
                },
            )

            # Step 3 — nuclei
            nuclei_findings = await scanner_service.run_nuclei(
                db=db,
                targets=targets,
                tech_stack=tech_stack,
                scan_id=scan_uuid,
                program_id=program_uuid,
                org_id=org_uuid,
                scope_json=scope_json,
                stealth=stealth,
                created_by_id=created_by_uuid,
            )

            # Step 4 — dalfox on discovered URLs
            discovered_urls = _extract_urls(nuclei_findings)
            dalfox_findings: list = []
            if discovered_urls:
                dalfox_findings = await scanner_service.run_dalfox(
                    db=db,
                    urls=discovered_urls,
                    scan_id=scan_uuid,
                    program_id=program_uuid,
                    org_id=org_uuid,
                    scope_json=scope_json,
                    created_by_id=created_by_uuid,
                )

            # Step 5 — AI chain detection
            chains = await ai_triage.detect_chains(db, program_uuid)

            # Step 6 — mark completed
            await _mark_scan_status(db, scan_uuid, ScanStatus.completed)

            # Step 7 — publish scan_complete
            await _publish_event(
                ctx,
                f"alerts:{org_uuid}",
                {
                    "event": "scan_complete",
                    "scan_id": scan_id,
                    "program_id": program_id,
                    "nuclei_findings": len(nuclei_findings),
                    "dalfox_findings": len(dalfox_findings),
                    "chains": len(chains),
                },
            )
            await db.commit()

            logger.info(
                "Full scan %s completed: nuclei=%d dalfox=%d chains=%d",
                scan_id,
                len(nuclei_findings),
                len(dalfox_findings),
                len(chains),
            )
            return {
                "status": "completed",
                "scan_id": scan_id,
                "nuclei_findings": len(nuclei_findings),
                "dalfox_findings": len(dalfox_findings),
                "chains": chains,
            }

        except Exception as exc:
            logger.exception("Full scan failed for scan %s: %s", scan_id, exc)
            try:
                await _mark_scan_status(db, scan_uuid, ScanStatus.failed)
                await db.commit()
            except Exception:
                logger.exception("Failed to mark scan %s as failed", scan_id)
            raise Retry(str(exc))


# Spec alias — full_scan_pipeline maps to the same ARQ task
full_scan_pipeline = run_full_scan


# ---------------------------------------------------------------------------
# ARQ task: standalone dalfox scan
# ---------------------------------------------------------------------------

async def run_dalfox_scan(
    ctx,
    scan_id: str,
    program_id: str,
    org_id: str,
    urls: list[str],
    scope_json: dict,
    created_by_id: str | None = None,
):
    """
    Standalone dalfox XSS scan ARQ task.

    Args:
        ctx: ARQ worker context dict.
        scan_id: UUID string of the Scan record.
        program_id: UUID string of the Program.
        org_id: UUID string of the Organisation.
        urls: List of target URLs to probe for XSS.
        scope_json: Program's scope JSON.
        created_by_id: Optional UUID string of the triggering user.
    """
    async with AsyncSessionLocal() as db:
        scan_uuid = UUID(scan_id)
        program_uuid = UUID(program_id)
        org_uuid = UUID(org_id)
        created_by_uuid = UUID(created_by_id) if created_by_id else None

        try:
            await _mark_scan_status(db, scan_uuid, ScanStatus.running)

            findings = await scanner_service.run_dalfox(
                db=db,
                urls=urls,
                scan_id=scan_uuid,
                program_id=program_uuid,
                org_id=org_uuid,
                scope_json=scope_json,
                created_by_id=created_by_uuid,
            )

            await _mark_scan_status(db, scan_uuid, ScanStatus.completed)
            await _publish_event(
                ctx,
                f"alerts:{org_uuid}",
                {
                    "event": "scan_complete",
                    "scan_id": scan_id,
                    "program_id": program_id,
                    "dalfox_findings": len(findings),
                },
            )
            await db.commit()

            logger.info("Dalfox scan %s completed: findings=%d", scan_id, len(findings))
            return {
                "status": "completed",
                "scan_id": scan_id,
                "dalfox_findings": len(findings),
            }

        except Exception as exc:
            logger.exception("Dalfox scan failed for scan %s: %s", scan_id, exc)
            try:
                await _mark_scan_status(db, scan_uuid, ScanStatus.failed)
                await db.commit()
            except Exception:
                logger.exception("Failed to mark scan %s as failed", scan_id)
            raise Retry(str(exc))