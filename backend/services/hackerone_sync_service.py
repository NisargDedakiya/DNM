"""
HackerOne synchronization service.

Responsibilities:
- synchronize programs and scopes
- normalize and validate imported targets
- persist organization-scoped sync snapshots
- provide recon-ready target ingestion payloads
- emit realtime pipeline events via WebSocket publisher
"""
from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import ip_network
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.hackerone import HackerOneClient
from backend.models.hackerone_program import HackerOneProgram
from backend.models.hackerone_report import HackerOneReport
from backend.utils.scope_validator import normalize_target
import logging

logger = logging.getLogger(__name__)


async def _emit(org_id: str, event_type: str, payload: dict) -> None:
    """Best-effort websocket publish — never raises."""
    try:
        from backend.websocket.publisher import ws_publisher
        await ws_publisher.publish_pipeline_event(org_id, event_type, payload)
    except Exception as exc:
        logger.debug("[h1-pipeline-emit] %s → %s (suppressed): %s", org_id, event_type, exc)


class HackerOneSyncService:
    """Service for HackerOne program/report sync and scope ingestion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_programs(
        self,
        *,
        organization_id: UUID,
        username: str,
        api_token: str,
    ) -> dict[str, Any]:
        """Synchronize accessible HackerOne programs into local storage."""
        org_id_str = str(organization_id)

        await _emit(org_id_str, "h1_sync_started", {
            "platform": "hackerone",
            "stage": "h1_sync_started",
            "message": "HackerOne sync initiated. Fetching accessible programs...",
        })

        try:
            client = HackerOneClient(username=username, api_token=api_token)
            programs = await client.get_programs()
        except Exception as exc:
            await _emit(org_id_str, "h1_sync_error", {
                "platform": "hackerone",
                "stage": "h1_sync_error",
                "error": str(exc),
                "message": f"HackerOne API error: {exc}",
            })
            raise

        await _emit(org_id_str, "h1_programs_fetched", {
            "platform": "hackerone",
            "stage": "h1_programs_fetched",
            "total_programs": len(programs),
            "message": f"{len(programs)} programs found. Normalizing scopes...",
        })

        created = 0
        updated = 0
        imported: list[dict[str, Any]] = []
        recon_ingestion: list[dict[str, Any]] = []
        total_recon_targets = 0

        for program in programs:
            saved, status = await self.import_hackerone_program(
                organization_id=organization_id,
                raw_program=program,
            )
            if status == "created":
                created += 1
            else:
                updated += 1

            imported.append(
                {
                    "id": str(saved.id),
                    "hackerone_program_id": saved.hackerone_program_id,
                    "handle": saved.handle,
                    "name": saved.name,
                    "offers_bounties": saved.offers_bounties,
                }
            )

            scope_result = await self.sync_program_scope(
                organization_id=organization_id,
                program_handle=saved.handle,
                username=username,
                api_token=api_token,
            )
            recon_targets = [
                t["normalized_target"]
                for t in scope_result["targets"]
                if t.get("recon_ready")
            ]
            total_recon_targets += len(recon_targets)
            recon_ingestion.append(
                {
                    "program_handle": saved.handle,
                    "recon_ready_targets": recon_targets,
                    "monitoring_targets": [
                        t["normalized_target"]
                        for t in scope_result["targets"]
                        if t.get("target_type") in {"domain", "wildcard_domain", "url"}
                    ],
                }
            )

        await self.db.commit()

        # ► Emit scope normalized event
        await _emit(org_id_str, "h1_scope_normalized", {
            "platform": "hackerone",
            "stage": "h1_scope_normalized",
            "total_programs": len(programs),
            "total_recon_targets": total_recon_targets,
            "message": f"{total_recon_targets} recon-ready targets normalized across {len(programs)} programs.",
        })

        await _emit(org_id_str, "h1_sync_complete", {
            "platform": "hackerone",
            "stage": "h1_sync_complete",
            "created": created,
            "updated": updated,
            "total": len(programs),
            "total_recon_targets": total_recon_targets,
            "message": f"HackerOne sync complete: {created} new, {updated} updated programs.",
        })

        return {
            "status": "ok",
            "created": created,
            "updated": updated,
            "total": len(programs),
            "programs": imported,
            "recon_ingestion": recon_ingestion,
        }

    async def import_hackerone_program(
        self,
        *,
        organization_id: UUID,
        raw_program: dict[str, Any],
    ) -> tuple[HackerOneProgram, str]:
        """Create or update a HackerOneProgram row from raw API object."""
        attributes = raw_program.get("attributes", {}) or {}
        handle = (attributes.get("handle") or "").strip().lower()
        if not handle:
            handle = str(raw_program.get("id", "")).strip().lower()

        existing_result = await self.db.execute(
            select(HackerOneProgram).where(
                and_(
                    HackerOneProgram.organization_id == organization_id,
                    HackerOneProgram.hackerone_program_id == str(raw_program.get("id", "")),
                )
            )
        )
        existing = existing_result.scalars().first()

        offers_bounties = bool(attributes.get("offers_bounties", False))
        bounty_enabled = bool(attributes.get("submission_state") == "open")

        if existing:
            existing.handle = handle
            existing.name = (attributes.get("name") or handle or "Unknown Program")[:512]
            existing.offers_bounties = offers_bounties
            existing.bounty_enabled = bounty_enabled
            existing.synced_at = datetime.now(timezone.utc)
            return existing, "updated"

        model = HackerOneProgram(
            organization_id=organization_id,
            hackerone_program_id=str(raw_program.get("id", ""))[:255],
            handle=handle[:255],
            name=(attributes.get("name") or handle or "Unknown Program")[:512],
            offers_bounties=offers_bounties,
            bounty_enabled=bounty_enabled,
            synced_at=datetime.now(timezone.utc),
        )
        self.db.add(model)
        await self.db.flush()
        return model, "created"

    async def sync_program_scope(
        self,
        *,
        organization_id: UUID,
        program_handle: str,
        username: str,
        api_token: str,
    ) -> dict[str, Any]:
        """Fetch structured scope and return normalized recon-ready targets."""
        client = HackerOneClient(username=username, api_token=api_token)
        raw_scope = await client.get_structured_scope(program_handle)
        normalized = self.normalize_scope_targets(raw_scope)

        return {
            "organization_id": str(organization_id),
            "program_handle": program_handle,
            "targets": normalized,
            "total_targets": len(normalized),
        }

    def normalize_scope_targets(self, structured_scope: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize imported scope into deterministic, validated target list."""
        output: list[dict[str, Any]] = []

        for item in structured_scope:
            attrs = item.get("attributes", {}) or {}
            target = (attrs.get("asset_identifier") or "").strip()
            if not target:
                continue

            asset_type = (attrs.get("asset_type") or "other").strip().lower()
            instruction = (attrs.get("instruction") or "").strip()[:1000]
            eligible = bool(attrs.get("eligible_for_submission", False))

            normalized_target = None
            target_type = "other"

            if target.startswith("*."):
                try:
                    normalized_target = f"*.{normalize_target(target[2:])}"
                    target_type = "wildcard_domain"
                except Exception:
                    continue
            elif "/" in target and not target.startswith("http"):
                # Future-safe CIDR handling
                try:
                    normalized_target = str(ip_network(target, strict=False))
                    target_type = "cidr"
                except Exception:
                    continue
            elif target.startswith("http://") or target.startswith("https://"):
                try:
                    parsed = urlparse(target)
                    host = parsed.hostname or ""
                    normalized_host = normalize_target(host)
                    normalized_target = f"{parsed.scheme}://{normalized_host}{parsed.path or ''}"
                    target_type = "url"
                except Exception:
                    continue
            else:
                try:
                    normalized_target = normalize_target(target)
                    target_type = "domain"
                except Exception:
                    # keep future-safe non-domain targets, but mark as non-recon
                    normalized_target = target[:1024]
                    target_type = asset_type if asset_type else "other"

            output.append(
                {
                    "target": target[:1024],
                    "normalized_target": normalized_target,
                    "target_type": target_type,
                    "asset_type": asset_type,
                    "eligible_for_submission": eligible,
                    "instruction": instruction,
                    "recon_ready": target_type in {"domain", "wildcard_domain", "url", "cidr"},
                }
            )

        # deterministic de-duplication order by normalized target
        dedup = {}
        for row in output:
            dedup[row["normalized_target"]] = row

        return [dedup[key] for key in sorted(dedup.keys())]

    async def sync_reports(
        self,
        *,
        organization_id: UUID,
        username: str,
        api_token: str,
    ) -> dict[str, Any]:
        """Fetch my reports and cache metadata for organization tracking."""
        org_id_str = str(organization_id)
        client = HackerOneClient(username=username, api_token=api_token)
        reports = await client.get_my_reports()

        created = 0
        updated = 0

        for item in reports:
            report_id = str(item.get("id", ""))[:255]
            attrs = item.get("attributes", {}) or {}

            existing_result = await self.db.execute(
                select(HackerOneReport).where(
                    and_(
                        HackerOneReport.organization_id == organization_id,
                        HackerOneReport.hackerone_report_id == report_id,
                    )
                )
            )
            existing = existing_result.scalars().first()

            title = (attrs.get("title") or "Untitled")[:1024]
            severity = str(attrs.get("severity_rating") or "unknown")[:64]
            state = str(attrs.get("state") or "unknown")[:64]
            submitted_at = attrs.get("submitted_at")

            if existing:
                existing.title = title
                existing.severity = severity
                existing.state = state
                if submitted_at:
                    existing.submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                updated += 1
                continue

            model = HackerOneReport(
                organization_id=organization_id,
                hackerone_report_id=report_id,
                title=title,
                severity=severity,
                state=state,
                submitted_at=(
                    datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
                    if submitted_at
                    else None
                ),
            )
            self.db.add(model)
            created += 1

        await self.db.commit()

        # ► Emit reports synced event
        await _emit(org_id_str, "h1_reports_synced", {
            "platform": "hackerone",
            "stage": "h1_reports_synced",
            "created": created,
            "updated": updated,
            "total": len(reports),
            "message": f"{len(reports)} reports synced ({created} new, {updated} updated).",
        })

        return {
            "status": "ok",
            "created": created,
            "updated": updated,
            "total": len(reports),
        }
