"""
Platform Sync Service: orchestrates bug bounty platform synchronization.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.hackerone_client import HackerOneClient, HackerOneClientError
from backend.models.platform_program import PlatformProgram, PlatformName
from backend.services.scope_sync_service import ScopeSyncService

logger = logging.getLogger(__name__)

class PlatformSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scope_svc = ScopeSyncService()

    async def sync_hackerone_programs(self, organization_id: UUID) -> Dict[str, Any]:
        """Sync programs from HackerOne."""
        client = HackerOneClient()
        stats = {"added": 0, "updated": 0, "failed": 0}
        
        try:
            programs = await client.fetch_programs()
        except HackerOneClientError as e:
            logger.error(f"Failed to fetch HackerOne programs: {e}")
            return {"status": "error", "message": str(e), "stats": stats}
            
        for prog in programs:
            try:
                prog_data = self.normalize_platform_program("hackerone", prog)
                handle = prog_data["program_handle"]
                
                # Fetch scope
                raw_scopes = await client.fetch_program_scopes(handle)
                normalized_scope = self.scope_svc.normalize_scope_targets("hackerone", raw_scopes)
                
                # Check validation
                if not self.scope_svc.validate_imported_scope(normalized_scope):
                    logger.warning(f"Invalid scope imported for {handle}")
                    
                normalized_scope["raw_platform_data"] = {"programs": prog, "scopes_count": len(raw_scopes)}
                prog_data["scope_data"] = normalized_scope
                
                # Upsert
                await self._upsert_program(organization_id, "hackerone", prog_data)
                stats["updated"] += 1
            except Exception as e:
                logger.error(f"Failed to sync program: {e}")
                stats["failed"] += 1
                
        return {"status": "success", "stats": stats}

    async def sync_bugcrowd_programs(self, organization_id: UUID) -> Dict[str, Any]:
        """Sync programs from Bugcrowd (Placeholder)."""
        logger.info("Syncing Bugcrowd programs... (Not fully implemented)")
        return {"status": "success", "stats": {"added": 0, "updated": 0, "failed": 0}}

    def normalize_platform_program(self, platform: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize program metadata."""
        if platform == "hackerone":
            attrs = raw_data.get("attributes", {})
            return {
                "external_program_id": raw_data.get("id", ""),
                "program_name": attrs.get("name", ""),
                "program_handle": attrs.get("handle", ""),
                "program_url": f"https://hackerone.com/{attrs.get('handle', '')}",
                "is_private": attrs.get("state") == "soft_launched", # simple heuristic
                "offers_bounty": attrs.get("offers_bounties", True)
            }
        return {}
        
    async def _upsert_program(self, organization_id: UUID, platform_name: str, prog_data: Dict[str, Any]) -> PlatformProgram:
        """Upsert a platform program."""
        stmt = select(PlatformProgram).where(
            PlatformProgram.organization_id == organization_id,
            PlatformProgram.platform_name == platform_name,
            PlatformProgram.external_program_id == prog_data["external_program_id"]
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            existing.program_name = prog_data.get("program_name", existing.program_name)
            existing.program_handle = prog_data.get("program_handle", existing.program_handle)
            existing.program_url = prog_data.get("program_url", existing.program_url)
            existing.is_private = prog_data.get("is_private", existing.is_private)
            existing.offers_bounty = prog_data.get("offers_bounty", existing.offers_bounty)
            
            # Merge scope changes safely
            if "scope_data" in prog_data:
                existing.scope_data = self.scope_svc.merge_scope_changes(existing.scope_data or {}, prog_data["scope_data"])
                
            existing.sync_status = "ok"
            existing.synced_at = datetime.utcnow()
            await self.db.commit()
            return existing
        else:
            new_prog = PlatformProgram(
                organization_id=organization_id,
                platform_name=PlatformName(platform_name),
                external_program_id=prog_data["external_program_id"],
                program_name=prog_data.get("program_name", "Unknown"),
                program_handle=prog_data.get("program_handle"),
                program_url=prog_data.get("program_url"),
                is_private=prog_data.get("is_private", False),
                offers_bounty=prog_data.get("offers_bounty", True),
                scope_data=prog_data.get("scope_data"),
                sync_status="ok",
                synced_at=datetime.utcnow()
            )
            self.db.add(new_prog)
            await self.db.commit()
            return new_prog
