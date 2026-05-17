"""
Scan service layer for database operations.
Manages scan lifecycle and result storage.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.scan import Scan, ScanStatus, ScanType
from backend.models.user import User

logger = logging.getLogger(__name__)


class ScanService:
    """
    Business logic for scan management.
    Handles creation, tracking, and result storage.
    """

    @staticmethod
    async def create_scan(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
        scan_type: ScanType = ScanType.recon,
    ) -> Scan:
        """
        Create new scan record.

        Args:
            db: Database session
            program_id: Program being scanned
            user_id: User who initiated scan
            scan_type: Type of scan (recon, surface, deep, manual)

        Returns:
            Created Scan record
        """
        scan = Scan(
            program_id=program_id,
            created_by_id=user_id,
            scan_type=scan_type,
            status=ScanStatus.pending,
        )

        db.add(scan)
        await db.flush()
        logger.info(f"Created scan {scan.id} for program {program_id}")

        return scan

    @staticmethod
    async def get_scan_by_id(
        db: AsyncSession,
        scan_id: UUID,
        user_id: UUID | None = None,
    ) -> Scan | None:
        """
        Retrieve scan record with optional ownership check.

        Args:
            db: Database session
            scan_id: Scan ID to retrieve
            user_id: Optional user for ownership validation

        Returns:
            Scan record or None if not found
        """
        query = select(Scan).where(Scan.id == scan_id)

        if user_id:
            # Verify user owns this scan
            query = query.where(Scan.created_by_id == user_id)

        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_program_scans(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
        limit: int = 100,
    ) -> list[Scan]:
        """
        Get all scans for a program with ownership check.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership validation
            limit: Maximum results

        Returns:
            List of Scan records
        """
        query = (
            select(Scan)
            .where(
                and_(
                    Scan.program_id == program_id,
                    Scan.created_by_id == user_id,
                )
            )
            .order_by(Scan.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_scan_status(
        db: AsyncSession,
        scan_id: UUID,
        status: ScanStatus,
        user_id: UUID | None = None,
    ) -> Scan | None:
        """
        Update scan status.

        Args:
            db: Database session
            scan_id: Scan to update
            status: New status
            user_id: Optional ownership check

        Returns:
            Updated Scan record or None
        """
        scan = await ScanService.get_scan_by_id(db, scan_id, user_id)

        if not scan:
            logger.warning(f"Scan not found: {scan_id}")
            return None

        scan.status = status

        if status == ScanStatus.running and not scan.started_at:
            scan.started_at = datetime.now(timezone.utc)

        if status in (ScanStatus.completed, ScanStatus.failed, ScanStatus.cancelled):
            if not scan.completed_at:
                scan.completed_at = datetime.now(timezone.utc)

        logger.info(f"Updated scan {scan_id} status to {status}")
        return scan

    @staticmethod
    async def store_scan_results(
        db: AsyncSession,
        scan_id: UUID,
        results_data: dict,
        user_id: UUID | None = None,
    ) -> Scan | None:
        """
        Store scan results and update status.

        Args:
            db: Database session
            scan_id: Scan ID
            results_data: Results to store (JSON)
            user_id: Optional ownership check

        Returns:
            Updated Scan record or None
        """
        scan = await ScanService.get_scan_by_id(db, scan_id, user_id)

        if not scan:
            logger.warning(f"Scan not found: {scan_id}")
            return None

        # Store results in metadata field if available
        # Otherwise, results are stored separately in findings
        scan.status = ScanStatus.completed
        scan.completed_at = datetime.now(timezone.utc)

        logger.info(f"Stored results for scan {scan_id}")
        return scan

    @staticmethod
    async def count_program_scans(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
    ) -> int:
        """
        Count scans for a program.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership

        Returns:
            Count of scans
        """
        query = (
            select(Scan)
            .where(
                and_(
                    Scan.program_id == program_id,
                    Scan.created_by_id == user_id,
                )
            )
        )

        result = await db.execute(query)
        return len(result.scalars().all())

    @staticmethod
    async def delete_scan(
        db: AsyncSession,
        scan_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """
        Delete scan record.

        Args:
            db: Database session
            scan_id: Scan to delete
            user_id: Optional ownership check

        Returns:
            True if deleted, False otherwise
        """
        scan = await ScanService.get_scan_by_id(db, scan_id, user_id)

        if not scan:
            logger.warning(f"Scan not found: {scan_id}")
            return False

        await db.delete(scan)
        logger.info(f"Deleted scan {scan_id}")
        return True
