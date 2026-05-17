"""
Permission engine for Role-Based Access Control (RBAC).
Centralized permission validation and authorization decorators.
"""
from enum import Enum
from typing import Callable, Optional
from functools import wraps
from uuid import UUID

from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.models.team_member import TeamMember, MemberRole
from backend.models.organization import Organization
from backend.database.session import get_db


class Permission(str, Enum):
    """Application permissions."""

    # Organization management
    MANAGE_ORG = "manage_org"
    MANAGE_MEMBERS = "manage_members"
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    
    # Scan operations
    RUN_SCANS = "run_scans"
    MANAGE_SCANS = "manage_scans"
    
    # Finding operations
    VIEW_FINDINGS = "view_findings"
    MANAGE_FINDINGS = "manage_findings"
    TRIAGE_FINDINGS = "triage_findings"
    
    # Asset management
    MANAGE_ASSETS = "manage_assets"
    VIEW_ASSETS = "view_assets"


# Role-to-Permission Mapping
ROLE_PERMISSIONS = {
    MemberRole.OWNER: {
        Permission.MANAGE_ORG,
        Permission.MANAGE_MEMBERS,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.RUN_SCANS,
        Permission.MANAGE_SCANS,
        Permission.VIEW_FINDINGS,
        Permission.MANAGE_FINDINGS,
        Permission.TRIAGE_FINDINGS,
        Permission.MANAGE_ASSETS,
        Permission.VIEW_ASSETS,
    },
    MemberRole.ADMIN: {
        Permission.MANAGE_MEMBERS,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.RUN_SCANS,
        Permission.MANAGE_SCANS,
        Permission.VIEW_FINDINGS,
        Permission.MANAGE_FINDINGS,
        Permission.TRIAGE_FINDINGS,
        Permission.MANAGE_ASSETS,
        Permission.VIEW_ASSETS,
    },
    MemberRole.ANALYST: {
        Permission.RUN_SCANS,
        Permission.MANAGE_SCANS,
        Permission.VIEW_FINDINGS,
        Permission.MANAGE_FINDINGS,
        Permission.TRIAGE_FINDINGS,
        Permission.VIEW_ASSETS,
    },
    MemberRole.VIEWER: {
        Permission.VIEW_FINDINGS,
        Permission.VIEW_ASSETS,
    },
}


class RBACService:
    """
    Centralized RBAC service for permission checking and validation.
    Provides reusable authorization logic for routes and services.
    """

    def __init__(self, db: AsyncSession):
        """Initialize RBAC service with database session."""
        self.db = db

    async def get_user_role(self, user_id: UUID, organization_id: UUID) -> Optional[MemberRole]:
        """
        Get user's role in organization.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization

        Returns:
            MemberRole or None if user is not a member
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
        member = result.scalars().first()
        return MemberRole(member.role) if member else None

    async def has_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission: Permission | str,
    ) -> bool:
        """
        Check if user has specific permission in organization.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization
            permission: Required permission

        Returns:
            bool: True if user has permission, False otherwise
        """
        role = await self.get_user_role(user_id, organization_id)
        if not role:
            return False

        permission_obj = Permission(permission) if isinstance(permission, str) else permission
        return permission_obj in ROLE_PERMISSIONS.get(role, set())

    async def check_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission: Permission | str,
    ) -> None:
        """
        Check permission and raise HTTPException if not authorized.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization
            permission: Required permission

        Raises:
            HTTPException: 403 Forbidden if user lacks permission
        """
        has_perm = await self.has_permission(user_id, organization_id, permission)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )

    async def validate_workspace_access(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Validate that user has access to organization workspace.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization

        Raises:
            HTTPException: 403 Forbidden if user is not an organization member
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
        member = result.scalars().first()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization",
            )

    async def is_organization_owner(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Check if user is the organization owner.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization

        Returns:
            bool: True if user is the owner, False otherwise
        """
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalars().first()
        if not org:
            return False
        return org.owner_id == user_id


# Dependency injection helpers
async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    """Get RBAC service with database session."""
    return RBACService(db)


def require_permission(permission: Permission | str) -> Callable:
    """
    Decorator to require specific permission for endpoint.

    Args:
        permission: Required permission

    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            user = kwargs.get("current_user")
            organization_id = kwargs.get("organization_id")
            rbac = kwargs.get("rbac_service")

            if not user or not organization_id or not rbac:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies",
                )

            await rbac.check_permission(user.id, organization_id, permission)
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(*roles: MemberRole | str) -> Callable:
    """
    Decorator to require specific roles for endpoint.

    Args:
        roles: Required roles (at least one)

    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            user = kwargs.get("current_user")
            organization_id = kwargs.get("organization_id")
            rbac = kwargs.get("rbac_service")

            if not user or not organization_id or not rbac:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies",
                )

            user_role = await rbac.get_user_role(user.id, organization_id)
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this organization",
                )

            # Convert string roles to MemberRole enum
            role_list = [MemberRole(r) if isinstance(r, str) else r for r in roles]
            if user_role not in role_list:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This operation requires one of these roles: {', '.join(r.value for r in role_list)}",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
