from uuid import UUID
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.auth.hackerone import h1_client
from backend.models.program import Program

logger = logging.getLogger(__name__)

class ProgramSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_all(self, organization_id: UUID, user_id: UUID) -> dict:
        """
        Synchronizes HackerOne programs into local Program model.
        """
        programs = await h1_client.get_programs()
        
        added = 0
        updated = 0
        
        for p in programs:
            handle = p.get('handle')
            if not handle:
                continue
            
            # Fetch structured scope
            try:
                scope_data = await h1_client.get_structured_scope(handle)
            except Exception as e:
                logger.error(f"Failed to fetch structured scope for {handle}: {e}")
                scope_data = {'in_scope': [], 'out_of_scope': [], 'no_auto_scan': False}
                
            in_scope_targets = [t.get('asset_identifier', '') for t in scope_data.get('in_scope', [])]
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
                existing_program.scope_json = scope_data
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
                    scope_json=scope_data
                )
                self.db.add(new_program)
                added += 1
                
        await self.db.commit()
        return {"added": added, "updated": updated, "total": len(programs)}

    async def refresh_scope(self, program_id: UUID, organization_id: UUID) -> dict:
        """
        Re-fetches and updates the scope for a specific program handle.
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
        
        in_scope_targets = [t.get('asset_identifier', '') for t in scope_data.get('in_scope', [])]
        scope_str = ", ".join(in_scope_targets) if in_scope_targets else "No in-scope targets"
        
        program.scope = scope_str
        program.scope_json = scope_data
        
        await self.db.commit()
        
        return {
            "program_id": str(program.id),
            "handle": program.handle,
            "in_scope_count": len(scope_data.get("in_scope", [])),
            "out_of_scope_count": len(scope_data.get("out_of_scope", [])),
            "no_auto_scan": scope_data.get("no_auto_scan", False)
        }
