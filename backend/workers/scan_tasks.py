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


async def _publish_event(ctx: Any, channel: str, payload: dict) -> None:
    redis = None
    if isinstance(ctx, dict):
        redis = ctx.get("redis")
    if redis is None:
        from backend.core.redis import get_redis

        redis = await get_redis()
    await redis.publish(channel, json.dumps(payload))


def _extract_urls(findings: list[Any]) -> list[str]:
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
    scan = await ScanService.update_scan_status(db, scan_id, status)
    if scan is None:
        raise RuntimeError(f"Scan {scan_id} not found")
    await db.commit()


async def run_full_scan(ctx, scan_id: str, program_id: str, org_id: str, targets: list[str], tech_stack: str, scope_json: dict, stealth: bool = False):
    async with AsyncSessionLocal() as db:
        scan_uuid = UUID(scan_id)
        program_uuid = UUID(program_id)
        org_uuid = UUID(org_id)

        try:
            await _mark_scan_status(db, scan_uuid, ScanStatus.running)
            await _publish_event(ctx, f"alerts:{org_uuid}", {"event": "scan_started", "scan_id": scan_id, "program_id": program_id})

            nuclei_findings = await scanner_service.run_nuclei(
                db=db,
                targets=targets,
                tech_stack=tech_stack,
                scan_id=scan_uuid,
                program_id=program_uuid,
                org_id=org_uuid,
                scope_json=scope_json,
                stealth=stealth,
            )

            discovered_urls = _extract_urls(nuclei_findings)
            dalfox_findings = []
            if discovered_urls:
                dalfox_findings = await scanner_service.run_dalfox(
                    db=db,
                    urls=discovered_urls,
                    scan_id=scan_uuid,
                    program_id=program_uuid,
                    org_id=org_uuid,
                    scope_json=scope_json,
                )

            chains = await ai_triage.detect_chains(db, program_uuid)

            await _mark_scan_status(db, scan_uuid, ScanStatus.completed)
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


async def run_dalfox_scan(ctx, scan_id: str, program_id: str, org_id: str, urls: list[str], scope_json: dict):
    async with AsyncSessionLocal() as db:
        scan_uuid = UUID(scan_id)
        program_uuid = UUID(program_id)
        org_uuid = UUID(org_id)

        try:
            await _mark_scan_status(db, scan_uuid, ScanStatus.running)

            findings = await scanner_service.run_dalfox(
                db=db,
                urls=urls,
                scan_id=scan_uuid,
                program_id=program_uuid,
                org_id=org_uuid,
                scope_json=scope_json,
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
            return {"status": "completed", "scan_id": scan_id, "dalfox_findings": len(findings)}
        except Exception as exc:
            logger.exception("Dalfox scan failed for scan %s: %s", scan_id, exc)
            try:
                await _mark_scan_status(db, scan_uuid, ScanStatus.failed)
                await db.commit()
            except Exception:
                logger.exception("Failed to mark scan %s as failed", scan_id)
            raise Retry(str(exc))