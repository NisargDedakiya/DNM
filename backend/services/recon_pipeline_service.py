"""
Recon pipeline orchestration: subfinder -> httpx probe -> katana -> nuclei -> findings

This module orchestrates the async pipeline, publishes websocket events,
creates findings via FindingService, and triggers AI triage.
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from backend.scanners.katana_scanner import KatanaScanner
from backend.scanners.nuclei_scanner import NucleiScanner
from backend.scanners.parsers import normalize_findings
from backend.websocket.pubsub import publish_event
from backend.services.finding_service import FindingService
from backend.ai.triage_service import triage_finding

logger = logging.getLogger(__name__)


async def run_katana_stage(targets: List[str], timeout: int = 180, user_id: str | UUID | None = None, program_id: UUID | None = None) -> List[str]:
    scanner = KatanaScanner(timeout=timeout)
    endpoints: List[str] = []
    await publish_event(user_id, {"event": "katana_started", "payload": {"targets": targets}})

    async def run_target(t: str):
        try:
            res = await scanner.run(t)
            eps = res.get("endpoints", [])
            endpoints.extend(eps)
        except Exception as exc:
            logger.exception("Katana stage failed for %s: %s", t, exc)

    tasks = [asyncio.create_task(run_target(t)) for t in targets]
    await asyncio.gather(*tasks)

    # dedupe
    endpoints = list(dict.fromkeys(endpoints))
    await publish_event(user_id, {"event": "katana_completed", "payload": {"count": len(endpoints)}})
    return endpoints


async def run_nuclei_stage(endpoints: List[str], timeout: int = 120, user_id: str | UUID | None = None, program_id: UUID | None = None) -> List[dict]:
    scanner = NucleiScanner(timeout=timeout)
    findings = []
    await publish_event(user_id, {"event": "nuclei_started", "payload": {"endpoints_count": len(endpoints)}})

    async def run_ep(ep: str):
        try:
            res = await scanner.run(ep)
            fs = res.get("findings", [])
            findings.extend(fs)
        except Exception:
            logger.exception("Nuclei error on %s", ep)

    tasks = [asyncio.create_task(run_ep(ep)) for ep in endpoints]
    await asyncio.gather(*tasks)

    await publish_event(user_id, {"event": "nuclei_completed", "payload": {"findings": len(findings)}})
    return findings


async def httpx_probe(hosts: List[str], concurrency: int = 20, timeout: int = 10) -> List[str]:
    """Probe hosts with httpx to determine live endpoints (http/https)."""
    live: List[str] = []
    sem = asyncio.Semaphore(concurrency)

    async def probe(u: str):
        async with sem:
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    r = await client.get(u if u.startswith("http") else f"http://{u}")
                    if r.status_code < 400:
                        live.append(r.url.human_repr())
            except Exception:
                # try https
                try:
                    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                        r = await client.get(f"https://{u}")
                        if r.status_code < 400:
                            live.append(r.url.human_repr())
                except Exception:
                    pass

    tasks = [asyncio.create_task(probe(h)) for h in hosts]
    await asyncio.gather(*tasks)
    return list(dict.fromkeys(live))


async def process_findings(raw_findings: List[dict], db: AsyncSession, user_id: str | UUID, program_id: UUID, scan_id: UUID | None = None) -> List[UUID]:
    """Normalize findings, deduplicate, create Finding records, and trigger triage."""
    created_ids: List[UUID] = []
    # normalize nuclei findings
    normalized = normalize_findings("nuclei", raw_findings, program_id=str(program_id))

    for nf in normalized:
        # dedup check
        duplicates = await FindingService.find_duplicates(db, nf["program_id"], nf["title"], nf["severity"], nf.get("endpoint"))
        if duplicates:
            logger.info("Duplicate finding skipped: %s", nf["title"])
            continue

        # create finding
        finding = await FindingService.create_finding(
            db,
            title=nf["title"],
            description=nf["description"],
            severity=nf["severity"],
            program_id=UUID(nf["program_id"]),
            user_id=UUID(str(user_id)),
            endpoint=nf.get("endpoint"),
            evidence=nf.get("evidence"),
            scan_id=scan_id,
        )
        await db.flush()
        created_ids.append(finding.id)
        # trigger AI triage (fire-and-forget)
        asyncio.create_task(_async_triage(finding))

    if created_ids:
        await publish_event(user_id, {"event": "findings_created", "payload": {"count": len(created_ids)}})

    return created_ids


async def _async_triage(finding):
    try:
        await triage_finding(
            title=finding.title,
            severity=(finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)),
            description=finding.description,
            endpoint=finding.endpoint,
            evidence=finding.evidence,
        )
    except Exception:
        logger.exception("AI triage failed for finding %s", getattr(finding, "id", "unknown"))


async def run_full_pipeline(
    initial_targets: List[str],
    db: AsyncSession,
    user_id: str | UUID,
    program_id: UUID,
    scan_id: UUID | None = None,
) -> dict:
    """Run the full recon pipeline and return summary.

    Steps: httpx probe -> katana -> nuclei -> process findings
    """
    # Stage 0: probe hosts
    await publish_event(user_id, {"event": "pipeline_started", "payload": {"targets": initial_targets}})
    live = await httpx_probe(initial_targets)
    await publish_event(user_id, {"event": "httpx_completed", "payload": {"live_count": len(live)}})

    # Stage 1: katana discovery
    endpoints = await run_katana_stage(live, user_id=user_id, program_id=program_id)

    # Stage 2: nuclei scanning
    nuclei_raw = await run_nuclei_stage(endpoints, user_id=user_id, program_id=program_id)

    # Stage 3: create findings
    created = await process_findings(nuclei_raw, db, user_id, program_id, scan_id=scan_id)
    # commit DB once at end
    await db.commit()

    await publish_event(user_id, {"event": "pipeline_completed", "payload": {"created_findings": len(created)}})

    return {"live_hosts": len(live), "endpoints": len(endpoints), "raw_findings": len(nuclei_raw), "created_findings": len(created)}


class ReconPipelineService:
    """
    Class wrapper around the module-level recon pipeline functions.
    Provides a dependency-injection-compatible interface for FastAPI routes
    and Celery workers.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_pipeline(
        self,
        initial_targets: List[str],
        user_id: str | UUID,
        program_id: UUID,
        scan_id: UUID | None = None,
    ) -> dict:
        return await run_full_pipeline(
            initial_targets=initial_targets,
            db=self.db,
            user_id=user_id,
            program_id=program_id,
            scan_id=scan_id,
        )

    async def probe_hosts(self, hosts: List[str], concurrency: int = 20, timeout: int = 10) -> List[str]:
        return await httpx_probe(hosts, concurrency=concurrency, timeout=timeout)

    async def run_katana(
        self,
        targets: List[str],
        user_id: str | UUID | None = None,
        program_id: UUID | None = None,
        timeout: int = 180,
    ) -> List[str]:
        return await run_katana_stage(targets, timeout=timeout, user_id=user_id, program_id=program_id)

    async def run_nuclei(
        self,
        endpoints: List[str],
        user_id: str | UUID | None = None,
        program_id: UUID | None = None,
        timeout: int = 120,
    ) -> List[dict]:
        return await run_nuclei_stage(endpoints, timeout=timeout, user_id=user_id, program_id=program_id)

    async def save_findings(
        self,
        raw_findings: List[dict],
        user_id: str | UUID,
        program_id: UUID,
        scan_id: UUID | None = None,
    ) -> List[UUID]:
        return await process_findings(raw_findings, self.db, user_id, program_id, scan_id=scan_id)

