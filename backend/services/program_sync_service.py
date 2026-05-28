from uuid import UUID
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.hackerone import h1_client, _clean_asset_identifier
from backend.models.program import Program

logger = logging.getLogger(__name__)

# Asset types accepted as scannable targets by the scope pipeline.
# Must stay in sync with auth/hackerone.py _SCANNABLE_ASSET_TYPES.
_SCANNABLE_ASSET_TYPES: frozenset[str] = frozenset({"URL", "WILDCARD", "CIDR"})


def _build_clean_scope_json(scope_data) -> dict:
    """Return a serialisable scope dict with only clean, scannable entries.

    This is the last defensive layer before data touches the database:
    • Drops entries with non-scannable asset_type.
    • Drops entries with null/empty asset_identifier after normalisation.
    • Ensures the persisted dict can always be safely deserialised by
      ScopeValidator without triggering KeyError or empty-pattern matches.
    """
    def _clean_list(items: list) -> list[dict]:
        clean = []
        for entry in items:
            asset_type = (entry.get("asset_type") or "").upper().strip()
            if asset_type not in _SCANNABLE_ASSET_TYPES:
                continue
            identifier = _clean_asset_identifier(entry.get("asset_identifier") or "")
            if identifier is None:
                continue
            clean.append({
                "asset_identifier": identifier,
                "asset_type": asset_type,
                "eligible_for_bounty": bool(entry.get("eligible_for_bounty", False)),
                "eligible_for_submission": bool(entry.get("eligible_for_submission", entry.get("eligible_for_bounty", False))),
                "max_severity": entry.get("max_severity") or "critical",
                "instruction": (entry.get("instruction") or "").lower(),
            })
        return clean

    return {
        "in_scope": _clean_list(scope_data.get("in_scope", []) if hasattr(scope_data, "get") else []),
        "out_of_scope": _clean_list(scope_data.get("out_of_scope", []) if hasattr(scope_data, "get") else []),
        "no_auto_scan": bool(scope_data.get("no_auto_scan", False) if hasattr(scope_data, "get") else False),
    }


class ProgramSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_all(self, organization_id: UUID, user_id: UUID) -> dict:
        """
        Synchronizes HackerOne programs into local Program model.
        Only clean, scannable scope entries (URL/WILDCARD/CIDR) with valid
        asset_identifiers are written to the database.
        """
        programs = await h1_client.get_programs()
        
        added = 0
        updated = 0
        
        for p in programs:
            handle = p.get('handle')
            if not handle:
                continue
            
            # Fetch structured scope — already filtered by h1_client to
            # URL/WILDCARD/CIDR types and clean identifiers.
            try:
                scope_data = await h1_client.get_structured_scope(handle)
            except Exception as e:
                logger.error(f"Failed to fetch structured scope for {handle}: {e}")
                scope_data = {'in_scope': [], 'out_of_scope': [], 'no_auto_scan': False}

            # Build the clean, serialisable dict that goes into the DB.
            clean_scope_json = _build_clean_scope_json(scope_data)

            # Derive the human-readable scope string from clean identifiers.
            in_scope_targets = [
                entry["asset_identifier"]
                for entry in clean_scope_json["in_scope"]
            ]
            scope_str = ", ".join(in_scope_targets) if in_scope_targets else "No in-scope targets"
            
            # Check if program exists by handle and organization_id
            stmt = select(Program).where(
                and_(
                    Program.organization_id == organization_id,
                    Program.handle == handle
                )
            )
            res = await self.db.execute(stmt)
            existing_program = res.scalars().first()
            
            if existing_program:
                existing_program.name = p.get('name', '')
                existing_program.scope = scope_str
                existing_program.description = p.get('policy', '')
                existing_program.is_private = p.get('is_private', False)
                existing_program.scope_json = clean_scope_json
                updated += 1
            else:
                new_program = Program(
                    name=p.get('name', ''),
                    platform='hackerone',
                    scope=scope_str,
                    description=p.get('policy', ''),
                    created_by=user_id,
                    organization_id=organization_id,
                    handle=handle,
                    is_private=p.get('is_private', False),
                    scope_json=clean_scope_json
                )
                self.db.add(new_program)
                added += 1
                
        await self.db.commit()
        return {"added": added, "updated": updated, "total": len(programs)}

    async def refresh_scope(self, program_id: UUID, organization_id: UUID) -> dict:
        """
        Re-fetches and updates the scope for a specific program handle.
        Only clean, scannable scope entries are written to the database.
        """
        stmt = select(Program).where(
            and_(
                Program.id == program_id,
                Program.organization_id == organization_id
            )
        )
        res = await self.db.execute(stmt)
        program = res.scalars().first()
        if not program:
            raise ValueError("Program not found or access denied")
            
        if not program.handle or program.platform != 'hackerone':
            raise ValueError("Only HackerOne programs with a valid handle can be refreshed")
            
        scope_data = await h1_client.get_structured_scope(program.handle)
        
        # Apply the same cleaning / filtering as sync_all.
        clean_scope_json = _build_clean_scope_json(scope_data)

        in_scope_targets = [
            entry["asset_identifier"]
            for entry in clean_scope_json["in_scope"]
        ]
        scope_str = ", ".join(in_scope_targets) if in_scope_targets else "No in-scope targets"
        
        program.scope = scope_str
        program.scope_json = clean_scope_json
        
        await self.db.commit()
        
        return {
            "program_id": str(program.id),
            "handle": program.handle,
            "in_scope_count": len(clean_scope_json["in_scope"]),
            "out_of_scope_count": len(clean_scope_json["out_of_scope"]),
            "no_auto_scan": clean_scope_json["no_auto_scan"],
        }
