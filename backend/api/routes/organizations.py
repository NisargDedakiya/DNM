"""
Organization API routes for team collaboration and RBAC operations.
Handles organization CRUD, member management, and workspace isolation.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.team_member import TeamMember, MemberRole
from backend.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationUpdate,
    TeamMemberResponse,
    TeamMemberDetailResponse,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    RemoveMemberRequest,
)
from backend.core.permissions import Permission, RBACService as BaseRBACService
from backend.services.organization_service import OrganizationService
from backend.services.rbac_service import RBACService

router = APIRouter(prefix="/organizations", tags=["organizations"])


async def get_org_service(db: AsyncSession = Depends(get_db)) -> OrganizationService:
    """Dependency for organization service."""
    return OrganizationService(db)


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    """Dependency for RBAC service."""
    return RBACService(db)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new organization",
    description="Create a new organization with the current user as owner",
)
async def create_organization(
    req: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
) -> Organization:
    """
    Create a new organization.

    The current user becomes the organization owner and is automatically added as a member.

    Args:
        req: Organization creation request
        current_user: Current authenticated user
        org_service: Organization service

    Returns:
        Organization: Created organization

    Raises:
        HTTPException: 400 if validation fails, 409 if slug exists
    """
    try:
        org = await org_service.create_organization(
            user_id=current_user.id,
            name=req.name,
            slug=req.slug,
            description=req.description,
        )
        return org
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List user's organizations",
    description="Get all organizations the current user is a member of",
)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
) -> list[Organization]:
    """
    List all organizations for current user.

    Returns all organizations the user is an active member of, ordered by creation date.

    Args:
        current_user: Current authenticated user
        org_service: Organization service

    Returns:
        list[Organization]: Organizations the user belongs to
    """
    orgs = await org_service.get_user_organizations(current_user.id)
    return orgs


@router.get(
    "/{organization_id}",
    response_model=OrganizationDetailResponse,
    summary="Get organization details",
    description="Get detailed information about an organization",
)
async def get_organization(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> dict:
    """
    Get organization details.

    User must be a member of the organization to view it.

    Args:
        organization_id: ID of the organization
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service

    Returns:
        dict: Organization details with member count

    Raises:
        HTTPException: 403 if not a member, 404 if org not found
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    org = await org_service.get_organization(organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    members = await org_service.get_organization_members(organization_id)
    return {
        **{
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "owner_id": org.owner_id,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
        },
        "member_count": len(members),
    }


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization details (owner only)",
)
async def update_organization(
    organization_id: UUID,
    req: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> Organization:
    """
    Update organization details.

    Only the organization owner can update organization settings.

    Args:
        organization_id: ID of the organization
        req: Update request
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service

    Returns:
        Organization: Updated organization

    Raises:
        HTTPException: 403 if not owner, 404 if org not found
    """
    await rbac.enforce_permission(
        current_user.id,
        organization_id,
        Permission.MANAGE_ORG,
        "Updating organization settings",
    )

    org = await org_service.update_organization(
        organization_id,
        name=req.name,
        description=req.description,
    )
    return org


@router.get(
    "/{organization_id}/members",
    response_model=list[TeamMemberDetailResponse],
    summary="List organization members",
    description="Get all active members of an organization",
)
async def list_members(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List organization members.

    User must be a member of the organization to view the member list.

    Args:
        organization_id: ID of the organization
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service
        db: Database session

    Returns:
        list[dict]: Team members with user details

    Raises:
        HTTPException: 403 if not a member
    """
    await rbac.validate_workspace_access(current_user.id, organization_id)

    members = await org_service.get_organization_members(organization_id)
    
    # Fetch user details for each member
    result_members = []
    for member in members:
        result_members.append({
            "id": member.id,
            "user_id": member.user_id,
            "organization_id": member.organization_id,
            "role": member.role,
            "is_active": member.is_active,
            "joined_at": member.joined_at,
            "invitation_accepted_at": member.invitation_accepted_at,
            "username": member.user.username,
            "email": member.user.email,
        })
    
    return result_members


@router.post(
    "/{organization_id}/members/invite",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite team member",
    description="Send invitation to join organization",
)
async def invite_member(
    organization_id: UUID,
    req: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
) -> TeamMember:
    """
    Invite a user to the organization.

    Only admin+ can invite members. Validates role hierarchy to prevent privilege escalation.

    Args:
        organization_id: ID of the organization
        req: Invitation request with email and role
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service
        db: Database session

    Returns:
        TeamMember: Created team member record

    Raises:
        HTTPException: 403 if no permission, 404 if user/org not found
    """
    await rbac.enforce_permission(
        current_user.id,
        organization_id,
        Permission.INVITE_MEMBERS,
        "Inviting members",
    )

    # Validate that user can assign this role
    await rbac.validate_role_hierarchy(current_user.id, organization_id, req.role)

    # Find user by email
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.email == req.email)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )

    # Invite the user
    member = await org_service.invite_member(
        organization_id=organization_id,
        user_id=user.id,
        role=req.role,
        invited_by_id=current_user.id,
    )
    return member


@router.put(
    "/{organization_id}/members/{member_id}/role",
    response_model=TeamMemberResponse,
    summary="Update member role",
    description="Change a team member's role",
)
async def update_member_role(
    organization_id: UUID,
    member_id: UUID,
    req: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> TeamMember:
    """
    Update team member role.

    Only admin+ can change roles. Prevents privilege escalation and role hierarchy violations.

    Args:
        organization_id: ID of the organization
        member_id: ID of the team member
        req: New role request
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service

    Returns:
        TeamMember: Updated team member

    Raises:
        HTTPException: 403 if no permission, 404 if member not found
    """
    await rbac.enforce_permission(
        current_user.id,
        organization_id,
        Permission.MANAGE_MEMBERS,
        "Updating member roles",
    )

    # Validate role hierarchy
    await rbac.validate_role_hierarchy(current_user.id, organization_id, req.role)

    member = await org_service.update_member_role(
        organization_id,
        member_id,
        req.role,
    )
    return member


@router.delete(
    "/{organization_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team member",
    description="Remove a member from organization",
)
async def remove_member(
    organization_id: UUID,
    member_id: UUID,
    req: RemoveMemberRequest | None = None,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service),
    rbac: RBACService = Depends(get_rbac_service),
) -> None:
    """
    Remove a team member from the organization.

    Only admin+ can remove members. Cannot remove the last owner.

    Args:
        organization_id: ID of the organization
        member_id: ID of the member to remove
        req: Removal request with optional reason
        current_user: Current authenticated user
        org_service: Organization service
        rbac: RBAC service

    Raises:
        HTTPException: 403 if no permission, 404 if member not found
    """
    await rbac.enforce_permission(
        current_user.id,
        organization_id,
        Permission.REMOVE_MEMBERS,
        "Removing members",
    )

    await org_service.remove_member(organization_id, member_id)
