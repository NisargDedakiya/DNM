"""
Organization service for CRUD operations and business logic.
Handles async database interactions with workspace isolation and RBAC support.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional
import re

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.models.organization import Organization
from backend.models.team_member import TeamMember, MemberRole
from backend.models.user import User


class OrganizationService:
    """Service for organization management operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize OrganizationService with database session.

        Args:
            db: AsyncSession for database operations
        """
        self.db = db

    async def create_organization(
        self,
        user_id: UUID,
        name: str,
        slug: str,
        description: Optional[str] = None,
    ) -> Organization:
        """
        Create a new organization owned by the current user.

        Args:
            user_id: ID of the organization owner
            name: Organization name
            slug: URL-friendly identifier
            description: Optional organization description

        Returns:
            Organization: Created organization instance

        Raises:
            ValueError: If validation fails
            HTTPException: If slug already exists
        """
        # Validate slug format
        if not re.match(r"^[a-z0-9_-]+$", slug):
            raise ValueError("Slug must contain only lowercase alphanumeric characters, hyphens, and underscores")

        # Check if slug already exists
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization slug already exists",
            )

        org = Organization(
            name=name,
            slug=slug,
            description=description,
            owner_id=user_id,
        )
        self.db.add(org)
        await self.db.flush()

        # Add owner as team member with owner role
        owner_member = TeamMember(
            organization_id=org.id,
            user_id=user_id,
            role=MemberRole.OWNER,
            invited_by=user_id,
        )
        self.db.add(owner_member)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        """
        Get organization by ID.

        Args:
            organization_id: ID of the organization

        Returns:
            Organization or None if not found
        """
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalars().first()

    async def get_user_organizations(self, user_id: UUID) -> list[Organization]:
        """
        Get all organizations a user is a member of.

        Args:
            user_id: ID of the user

        Returns:
            list[Organization]: Organizations the user belongs to
        """
        result = await self.db.execute(
            select(Organization).join(TeamMember).where(
                and_(
                    TeamMember.user_id == user_id,
                    TeamMember.is_active == True,
                )
            ).order_by(Organization.created_at.desc())
        )
        return result.scalars().all()

    async def get_organization_members(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> list[TeamMember]:
        """
        Get team members of an organization.

        Args:
            organization_id: ID of the organization
            active_only: Only return active members if True

        Returns:
            list[TeamMember]: Team members in the organization
        """
        query = select(TeamMember).where(TeamMember.organization_id == organization_id)
        if active_only:
            query = query.where(TeamMember.is_active == True)
        query = query.order_by(TeamMember.joined_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def invite_member(
        self,
        organization_id: UUID,
        user_id: UUID,
        role: str = MemberRole.ANALYST,
        invited_by_id: UUID | None = None,
    ) -> TeamMember:
        """
        Invite a user to organization.

        Args:
            organization_id: ID of the organization
            user_id: ID of the user to invite
            role: Role to assign to the member
            invited_by_id: ID of the user sending the invitation

        Returns:
            TeamMember: Created team member

        Raises:
            HTTPException: If user already a member or validation fails
        """
        # Check if user is already a member
        result = await self.db.execute(
            select(TeamMember).where(
                and_(
                    TeamMember.organization_id == organization_id,
                    TeamMember.user_id == user_id,
                )
            )
        )
        existing = result.scalars().first()
        if existing:
            if existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a member of this organization",
                )
            # Reactivate inactive member
            existing.is_active = True
            existing.role = role
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Validate role
        if role not in [r.value for r in MemberRole]:
            raise ValueError(f"Invalid role: {role}")

        member = TeamMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by_id,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(
        self,
        organization_id: UUID,
        member_id: UUID,
        new_role: str,
    ) -> TeamMember:
        """
        Update team member role.

        Args:
            organization_id: ID of the organization
            member_id: ID of the team member
            new_role: New role to assign

        Returns:
            TeamMember: Updated team member

        Raises:
            HTTPException: If member not found or validation fails
        """
        result = await self.db.execute(
            select(TeamMember).where(
                and_(
                    TeamMember.id == member_id,
                    TeamMember.organization_id == organization_id,
                )
            )
        )
        member = result.scalars().first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found",
            )

        # Validate role
        if new_role not in [r.value for r in MemberRole]:
            raise ValueError(f"Invalid role: {new_role}")

        member.role = new_role
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self,
        organization_id: UUID,
        member_id: UUID,
    ) -> None:
        """
        Remove a team member from organization.

        Args:
            organization_id: ID of the organization
            member_id: ID of the team member to remove

        Raises:
            HTTPException: If member not found or is the only owner
        """
        result = await self.db.execute(
            select(TeamMember).where(
                and_(
                    TeamMember.id == member_id,
                    TeamMember.organization_id == organization_id,
                )
            )
        )
        member = result.scalars().first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found",
            )

        # Prevent removing the last owner
        if member.role == MemberRole.OWNER:
            owner_count = await self.db.execute(
                select(TeamMember).where(
                    and_(
                        TeamMember.organization_id == organization_id,
                        TeamMember.role == MemberRole.OWNER,
                        TeamMember.is_active == True,
                    )
                )
            )
            if len(owner_count.scalars().all()) == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the only owner of the organization",
                )

        member.is_active = False
        await self.db.commit()

    async def update_organization(
        self,
        organization_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Organization:
        """
        Update organization details.

        Args:
            organization_id: ID of the organization
            name: New organization name
            description: New organization description

        Returns:
            Organization: Updated organization

        Raises:
            HTTPException: If organization not found
        """
        org = await self.get_organization(organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        if name is not None:
            org.name = name
        if description is not None:
            org.description = description

        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_member_by_user_and_org(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Optional[TeamMember]:
        """
        Get team member record for specific user and organization.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization

        Returns:
            TeamMember or None if not found
        """
        result = await self.db.execute(
            select(TeamMember).where(
                and_(
                    TeamMember.user_id == user_id,
                    TeamMember.organization_id == organization_id,
                    TeamMember.is_active == True,
                )
            )
        )
        return result.scalars().first()
