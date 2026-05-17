"""
Finding service layer for vulnerability management.
Handles CRUD operations, deduplication, and ownership validation.
"""
import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.enums import FindingSeverity, FindingStatus
from backend.models.finding import Finding
from backend.models.user import User

logger = logging.getLogger(__name__)


class FindingService:
    """
    Business logic for finding management.
    Handles creation, updates, filtering, and deduplication.
    """

    @staticmethod
    async def create_finding(
        db: AsyncSession,
        title: str,
        description: str,
        severity: FindingSeverity,
        program_id: UUID,
        user_id: UUID,
        endpoint: str | None = None,
        evidence: str | None = None,
        scan_id: UUID | None = None,
    ) -> Finding:
        """
        Create new finding.

        Args:
            db: Database session
            title: Finding title
            description: Detailed description
            severity: Severity level
            program_id: Associated program
            user_id: User creating finding
            endpoint: Optional affected endpoint
            evidence: Optional evidence/proof
            scan_id: Optional scan that discovered it

        Returns:
            Created Finding record
        """
        finding = Finding(
            title=title,
            description=description,
            severity=severity,
            program_id=program_id,
            created_by_id=user_id,
            endpoint=endpoint,
            evidence=evidence,
            scan_id=scan_id,
            status=FindingStatus.open,
        )

        db.add(finding)
        await db.flush()
        logger.info(
            f"Created finding {finding.id} (severity: {severity}) "
            f"for program {program_id} by user {user_id}"
        )

        return finding

    @staticmethod
    async def get_finding_by_id(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID | None = None,
    ) -> Finding | None:
        """
        Retrieve finding with optional ownership check.

        Args:
            db: Database session
            finding_id: Finding ID
            user_id: Optional user for ownership validation

        Returns:
            Finding record or None
        """
        query = select(Finding).where(Finding.id == finding_id)

        if user_id:
            # Verify user owns the finding (through program)
            query = query.join(Finding.program).where(
                Finding.program.has(created_by_id=user_id)
            )

        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_program_findings(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
        severity: FindingSeverity | None = None,
        status: FindingStatus | None = None,
        scan_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        """
        Get findings for program with filtering.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership validation
            severity: Optional severity filter
            status: Optional status filter
            scan_id: Optional scan filter
            limit: Maximum results
            offset: Result offset

        Returns:
            Tuple of (findings list, total count)
        """
        # Build base query with ownership check
        query = (
            select(Finding)
            .where(
                and_(
                    Finding.program_id == program_id,
                    Finding.program.has(created_by_id=user_id),
                )
            )
        )

        # Apply optional filters
        if severity:
            query = query.where(Finding.severity == severity)

        if status:
            query = query.where(Finding.status == status)

        if scan_id:
            query = query.where(Finding.scan_id == scan_id)

        # Get total count
        count_query = query.with_only_columns(Finding.id)
        count_result = await db.execute(
            select(count_query).with_only_columns(__import__('sqlalchemy').func.count())
        )
        total = count_result.scalar() or 0

        # Apply pagination and execute
        results_query = (
            query.order_by(Finding.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(results_query)
        findings = result.scalars().all()

        return findings, total

    @staticmethod
    async def update_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
        title: str | None = None,
        description: str | None = None,
        severity: FindingSeverity | None = None,
        endpoint: str | None = None,
        evidence: str | None = None,
        status: FindingStatus | None = None,
    ) -> Finding | None:
        """
        Update finding with partial updates.

        Args:
            db: Database session
            finding_id: Finding ID
            user_id: User for ownership validation
            title: Optional new title
            description: Optional new description
            severity: Optional new severity
            endpoint: Optional new endpoint
            evidence: Optional new evidence
            status: Optional new status

        Returns:
            Updated Finding or None
        """
        finding = await FindingService.get_finding_by_id(db, finding_id, user_id)

        if not finding:
            logger.warning(
                f"Finding not found: {finding_id} for user {user_id}"
            )
            return None

        # Update fields if provided
        if title is not None:
            finding.title = title

        if description is not None:
            finding.description = description

        if severity is not None:
            finding.severity = severity

        if endpoint is not None:
            finding.endpoint = endpoint

        if evidence is not None:
            finding.evidence = evidence

        if status is not None:
            finding.status = status

        logger.info(f"Updated finding {finding_id}")
        return finding

    @staticmethod
    async def delete_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """
        Delete finding.

        Args:
            db: Database session
            finding_id: Finding ID
            user_id: Optional ownership check

        Returns:
            True if deleted, False otherwise
        """
        finding = await FindingService.get_finding_by_id(db, finding_id, user_id)

        if not finding:
            logger.warning(f"Finding not found: {finding_id}")
            return False

        await db.delete(finding)
        logger.info(f"Deleted finding {finding_id}")
        return True

    @staticmethod
    async def find_duplicates(
        db: AsyncSession,
        program_id: UUID,
        title: str,
        severity: FindingSeverity,
        endpoint: str | None = None,
        exclude_finding_id: UUID | None = None,
    ) -> list[Finding]:
        """
        Find potential duplicate findings in program.

        Uses title, severity, and endpoint for matching.

        Args:
            db: Database session
            program_id: Program to search
            title: Finding title
            severity: Severity level
            endpoint: Optional endpoint
            exclude_finding_id: Exclude specific finding

        Returns:
            List of potential duplicates
        """
        query = select(Finding).where(
            and_(
                Finding.program_id == program_id,
                Finding.title == title,
                Finding.severity == severity,
            )
        )

        if endpoint:
            query = query.where(Finding.endpoint == endpoint)

        if exclude_finding_id:
            query = query.where(Finding.id != exclude_finding_id)

        result = await db.execute(query)
        duplicates = result.scalars().all()

        logger.debug(
            f"Found {len(duplicates)} potential duplicates "
            f"for '{title}' in program {program_id}"
        )

        return duplicates

    @staticmethod
    async def mark_as_duplicate(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Mark finding as duplicate.

        Args:
            db: Database session
            finding_id: Finding ID
            user_id: User for ownership validation

        Returns:
            True if marked, False otherwise
        """
        finding = await FindingService.update_finding(
            db,
            finding_id,
            user_id,
            status=FindingStatus.duplicate,
        )

        if finding:
            logger.info(f"Marked finding {finding_id} as duplicate")
            return True

        return False

    @staticmethod
    async def get_severity_summary(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
    ) -> dict[str, int]:
        """
        Get summary of findings by severity.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership validation

        Returns:
            Dictionary mapping severity to count
        """
        query = select(Finding.severity, __import__('sqlalchemy').func.count()).where(
            and_(
                Finding.program_id == program_id,
                Finding.program.has(created_by_id=user_id),
            )
        ).group_by(Finding.severity)

        result = await db.execute(query)
        rows = result.all()

        summary = {severity.value: count for severity, count in rows}

        # Ensure all severity levels are present
        for severity in FindingSeverity:
            if severity.value not in summary:
                summary[severity.value] = 0

        return summary

    @staticmethod
    async def get_status_summary(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
    ) -> dict[str, int]:
        """
        Get summary of findings by status.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership validation

        Returns:
            Dictionary mapping status to count
        """
        query = select(Finding.status, __import__('sqlalchemy').func.count()).where(
            and_(
                Finding.program_id == program_id,
                Finding.program.has(created_by_id=user_id),
            )
        ).group_by(Finding.status)

        result = await db.execute(query)
        rows = result.all()

        summary = {status.value: count for status, count in rows}

        # Ensure all status values are present
        for status in FindingStatus:
            if status.value not in summary:
                summary[status.value] = 0

        return summary

    @staticmethod
    async def count_critical_findings(
        db: AsyncSession,
        program_id: UUID,
        user_id: UUID,
    ) -> int:
        """
        Count critical severity findings.

        Args:
            db: Database session
            program_id: Program ID
            user_id: User for ownership validation

        Returns:
            Count of critical findings
        """
        query = select(Finding).where(
            and_(
                Finding.program_id == program_id,
                Finding.severity == FindingSeverity.critical,
                Finding.program.has(created_by_id=user_id),
            )
        )

        result = await db.execute(query)
        return len(result.scalars().all())
