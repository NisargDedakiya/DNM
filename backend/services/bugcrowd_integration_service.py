"""
Bugcrowd Integration Service
Orchestrates scraping, extraction, and ingestion workflow
"""
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from backend.engines.bugcrowd_scraper import BugcrowdScraper, BugcrowdScraperConfig
from backend.services.scope_extraction_service import ScopeExtractor
from backend.services.program_metadata_service import ProgramMetadataAnalyzer, ProgramMetadata
from backend.models.bugcrowd_program import BugcrowdProgram, BugcrowdAsset, BugcrowdProgramStatus, BugcrowdSyncHistory
from backend.ai.claude_client import ClaudeClient
from backend.core.scope_validator import ScopeValidator
from backend.models.asset import Asset
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BugcrowdIngestionResult:
    """Result of a Bugcrowd ingestion"""
    
    def __init__(self):
        self.success = False
        self.program_name: Optional[str] = None
        self.assets_imported = 0
        self.assets_updated = 0
        self.errors: List[str] = []
        self.program_id: Optional[str] = None
        self.duration_seconds: Optional[float] = None


class BugcrowdIntegrationService:
    """
    Orchestrate Bugcrowd engagement ingestion
    Handles scraping, extraction, normalization, and storage
    """
    
    def __init__(
        self,
        claude_client: ClaudeClient,
        scope_validator: ScopeValidator,
        db: AsyncSession
    ):
        self.claude = claude_client
        self.validator = scope_validator
        self.db = db
        self.scraper_config = BugcrowdScraperConfig()
    
    async def ingest_bugcrowd_engagement(
        self,
        engagement_url: str,
        organization_id: str
    ) -> BugcrowdIngestionResult:
        """
        Ingest a Bugcrowd engagement page
        
        Full workflow:
        1. Fetch public engagement page
        2. Parse HTML
        3. Extract scope with AI
        4. Extract metadata with AI
        5. Normalize targets
        6. Validate targets
        7. Store in database
        8. Link to recon workflows
        
        Args:
            engagement_url: Bugcrowd engagement URL
            organization_id: Organization workspace ID
            
        Returns:
            BugcrowdIngestionResult with details
        """
        result = BugcrowdIngestionResult()
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting Bugcrowd ingestion for {engagement_url}")
            
            # Step 1: Fetch engagement page
            logger.debug("Step 1: Fetching engagement page...")
            async with BugcrowdScraper(self.scraper_config) as scraper:
                html = await scraper.fetch_engagement_page(engagement_url)
            
            if not html:
                result.errors.append("Failed to fetch engagement page")
                logger.error(f"Could not fetch {engagement_url}")
                return result
            
            # Step 2: Parse HTML
            logger.debug("Step 2: Parsing HTML...")
            async with BugcrowdScraper(self.scraper_config) as scraper:
                parsed_data = scraper.parse_engagement_html(html)
                scope_sections = scraper.extract_scope_sections(parsed_data)
                basic_metadata = scraper.extract_program_metadata(parsed_data)
            
            result.program_name = parsed_data.get("program_name", "Unknown Program")
            
            # Step 3: Extract scope with AI
            logger.debug("Step 3: Extracting scope with AI...")
            extractor = ScopeExtractor(self.claude, self.validator)
            scope_raw = "\n".join(scope_sections.get("in_scope", []))
            structured_scope = await extractor.extract_structured_scope(
                scope_raw,
                program_context=f"Program: {result.program_name}"
            )
            
            # Step 4: Extract metadata with AI
            logger.debug("Step 4: Extracting metadata with AI...")
            metadata_analyzer = ProgramMetadataAnalyzer(self.claude)
            program_metadata = await metadata_analyzer.analyze_program_metadata(
                result.program_name,
                parsed_data.get("program_description"),
                parsed_data.get("raw_text", "")
            )
            
            # Step 5: Store program
            logger.debug("Step 5: Storing program...")
            program_id = await self._store_program(
                engagement_url,
                organization_id,
                result.program_name,
                structured_scope,
                program_metadata,
                html
            )
            result.program_id = program_id
            
            # Step 6: Store assets and link to inventory
            logger.debug("Step 6: Storing assets...")
            result.assets_imported, result.assets_updated = await self._store_assets(
                program_id,
                structured_scope,
                organization_id
            )
            
            # Step 7: Record sync
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self._record_sync_history(program_id, result, duration)
            
            result.success = True
            result.duration_seconds = duration
            logger.info(
                f"Successfully ingested {result.program_name}: "
                f"{result.assets_imported} imported, {result.assets_updated} updated"
            )
        
        except Exception as e:
            logger.error(f"Error during Bugcrowd ingestion: {str(e)}", exc_info=True)
            result.errors.append(str(e))
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        return result
    
    async def _store_program(
        self,
        engagement_url: str,
        organization_id: str,
        program_name: str,
        structured_scope: Dict,
        metadata: ProgramMetadata,
        html_snapshot: str
    ) -> str:
        """Store Bugcrowd program in database"""
        
        # Check for duplicate
        existing_result = await self.db.execute(
            select(BugcrowdProgram).where(BugcrowdProgram.engagement_url == engagement_url)
        )
        existing = existing_result.scalars().first()
        
        if existing:
            existing.last_synced_at = datetime.utcnow()
            existing.html_snapshot = html_snapshot[:50000]  # Limit size
            existing.scope_data = {
                "in_scope": [t.to_dict() for t in structured_scope.get("in_scope", [])],
                "out_of_scope": [t.to_dict() for t in structured_scope.get("out_of_scope", [])]
            }
            existing.program_metadata = metadata.to_dict()
            existing.program_description = metadata.description
            existing.asset_categories = metadata.asset_categories
            existing.ai_extraction_used = True
            existing.extraction_confidence = 85
            await self.db.commit()
            logger.info(f"Updated existing program: {existing.id}")
            return existing.id
        
        # Create new program
        program = BugcrowdProgram(
            organization_id=organization_id,
            engagement_url=engagement_url,
            program_name=program_name,
            scope_data={
                "in_scope": [t.to_dict() for t in structured_scope.get("in_scope", [])],
                "out_of_scope": [t.to_dict() for t in structured_scope.get("out_of_scope", [])]
            },
            program_metadata=metadata.to_dict(),
            status=BugcrowdProgramStatus.ACTIVE,
            program_description=metadata.description,
            asset_categories=metadata.asset_categories,
            last_synced_at=datetime.utcnow(),
            html_snapshot=html_snapshot[:50000],  # Limit size
            ai_extraction_used=True,
            extraction_confidence=85  # Default confidence
        )
        
        self.db.add(program)
        await self.db.commit()
        logger.info(f"Created new program: {program.id} - {program_name}")
        return program.id
    
    async def _store_assets(
        self,
        program_id: str,
        structured_scope: Dict,
        organization_id: str
    ) -> tuple:
        """Store extracted assets in database"""
        
        imported_count = 0
        updated_count = 0
        
        program_result = await self.db.execute(select(BugcrowdProgram).where(BugcrowdProgram.id == program_id))
        program = program_result.scalars().first()
        if not program:
            logger.error(f"Program not found: {program_id}")
            return imported_count, updated_count
        
        # Process in-scope targets
        for target in structured_scope.get("in_scope", []):
            try:
                # Check for existing asset
                existing_result = await self.db.execute(
                    select(BugcrowdAsset).where(
                    and_(
                        BugcrowdAsset.program_id == program_id,
                        BugcrowdAsset.target == target.target
                    )
                    )
                )
                existing = existing_result.scalars().first()
                
                if existing:
                    existing.asset_type = target.asset_type
                    existing.priority_level = target.priority
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                    logger.debug(f"Updated asset: {target.target}")
                else:
                    asset = BugcrowdAsset(
                        program_id=program_id,
                        target=target.target,
                        asset_type=target.asset_type,
                        in_scope=True,
                        normalized_target=target.target,
                        wildcard_pattern=target.wildcard,
                        base_domain=target.base_domain,
                        notes=target.notes,
                        restrictions=target.restrictions,
                        validation_status="valid",
                        synced_to_asset_inventory=False
                    )
                    self.db.add(asset)
                    imported_count += 1
                    logger.debug(f"Created asset: {target.target}")
            
            except Exception as e:
                logger.error(f"Error storing asset {target.target}: {str(e)}")
        
        await self.db.commit()
        logger.info(f"Stored {imported_count} new assets, updated {updated_count} existing")
        return imported_count, updated_count
    
    async def _record_sync_history(
        self,
        program_id: str,
        result: BugcrowdIngestionResult,
        duration: float
    ):
        """Record sync history for audit trail"""
        
        history = BugcrowdSyncHistory(
            program_id=program_id,
            sync_status="success" if result.success else "failed",
            assets_imported=result.assets_imported,
            assets_updated=result.assets_updated,
            errors=result.errors if result.errors else None,
            duration_seconds=int(duration)
        )
        
        self.db.add(history)
        await self.db.commit()
        logger.info(f"Recorded sync history for program {program_id}")
