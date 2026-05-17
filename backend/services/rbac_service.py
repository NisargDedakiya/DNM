"""
RBAC service for permission enforcement and validation.
Extended permission checking with organization context.
"""
from __future__ import annotations

from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.core.permissions import Permission, RBACService as BaseRBACService, ROLE_PERMISSIONS
from backend.models.team_member import MemberRole
from backend.services.organization_service import OrganizationService


class RBACService(BaseRBACService):
    """
    Extended RBAC service with organization context.
    Provides permission enforcement combined with organization service operations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize RBAC service with database session."""
        super().__init__(db)
        self.org_service = OrganizationService(db)

    async def enforce_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission: Permission | str,
        action_description: str = "This operation",
    ) -> None:
        """
        Enforce permission with detailed error messages.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization
            permission: Required permission
            action_description: Description of the action for error message

        Raises:
            HTTPException: 403 if permission denied, 404 if org not found
        """
        org = await self.org_service.get_organization(organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        has_perm = await self.has_permission(user_id, organization_id, permission)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{action_description} requires '{permission.value if isinstance(permission, Permission) else permission}' permission",
            )

    async def get_permissions_for_role(self, role: MemberRole | str) -> set[Permission]:
        """
        Get all permissions for a specific role.

        Args:
            role: The role to get permissions for

        Returns:
            set[Permission]: Set of permissions for the role
        """
        role_obj = MemberRole(role) if isinstance(role, str) else role
        return ROLE_PERMISSIONS.get(role_obj, set())

    async def can_manage_member(
        self,
        user_id: UUID,
        organization_id: UUID,
        target_member_id: UUID,
    ) -> bool:
        """
        Check if user can manage (remove/update role) of a specific member.

        Args:
            user_id: ID of the user performing the action
            organization_id: ID of the organization
            target_member_id: ID of the member being managed

        Returns:
            bool: True if allowed to manage, False otherwise
        """
        user_role = await self.get_user_role(user_id, organization_id)
        if not user_role:
            return False

        # Get target member's role
        target_member = await self.org_service.get_member_by_user_and_org(
            # We need to get member from org
            organization_id,
            target_member_id,
        )
        if not target_member:
            return False

        target_role = MemberRole(target_member.role)

        # Owner can manage anyone
        if user_role == MemberRole.OWNER:
            return True

        # Admin can manage analysts and viewers
        if user_role == MemberRole.ADMIN:
            return target_role in {MemberRole.ANALYST, MemberRole.VIEWER}

        # Others cannot manage anyone
        return False

    async def validate_role_hierarchy(
        self,
        user_id: UUID,
        organization_id: UUID,
        new_role: str,
    ) -> None:
        """
        Validate that user has sufficient privilege to assign a new role.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization
            new_role: Role to be assigned

        Raises:
            HTTPException: 403 if user cannot assign this role
        """
        user_role = await self.get_user_role(user_id, organization_id)
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )

        new_role_obj = MemberRole(new_role)

        # Owner can assign any role
        if user_role == MemberRole.OWNER:
            return

        # Admin can assign analyst and viewer roles only
        if user_role == MemberRole.ADMIN:
            if new_role_obj not in {MemberRole.ANALYST, MemberRole.VIEWER}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only assign analyst or viewer roles",
                )
            return

        # Analysts and viewers cannot assign any roles
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to assign roles",
        )

    async def get_user_organization_count(self, user_id: UUID) -> int:
        """
        Get count of organizations user is a member of.

        Args:
            user_id: ID of the user

        Returns:
            int: Number of organizations
        """
        orgs = await self.org_service.get_user_organizations(user_id)
        return len(orgs)

    async def can_delete_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Check if user can delete organization.
        Only the owner can delete.

        Args:
            user_id: ID of the user
            organization_id: ID of the organization

        Returns:
            bool: True if user can delete the organization
        """
        return await self.is_organization_owner(user_id, organization_id)
