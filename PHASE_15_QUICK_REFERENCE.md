# Phase 15 Quick Reference Guide

## Quick Start: Protecting Routes with RBAC

### Basic Permission Check in Route

```python
from fastapi import Depends, HTTPException
from backend.auth.dependencies import get_current_user
from backend.services.rbac_service import RBACService
from backend.core.permissions import Permission
from uuid import UUID

@app.post("/scans")
async def create_scan(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service),
):
    """Create scan (analysts+ can do this)"""
    await rbac.enforce_permission(
        current_user.id,
        organization_id,
        Permission.RUN_SCANS,
        "Creating scans"
    )
    # Your logic here
```

### Validate Workspace Access

```python
@app.get("/organizations/{org_id}/dashboard")
async def get_dashboard(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service),
):
    """Get dashboard (any member can view)"""
    await rbac.validate_workspace_access(current_user.id, org_id)
    # Query data from this organization only
```

### Check Multiple Permissions

```python
@app.post("/organizations/{org_id}/members/bulk-action")
async def bulk_member_action(
    org_id: UUID,
    action: str,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service),
):
    """Complex action needing multiple permissions"""
    if action == "invite":
        await rbac.enforce_permission(
            current_user.id, org_id, Permission.INVITE_MEMBERS
        )
    elif action == "remove":
        await rbac.enforce_permission(
            current_user.id, org_id, Permission.REMOVE_MEMBERS
        )
```

### Query with Organization Isolation

```python
@app.get("/organizations/{org_id}/findings")
async def list_findings(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service),
    db: AsyncSession = Depends(get_db),
):
    """List findings (must validate membership + filter by org)"""
    await rbac.validate_workspace_access(current_user.id, org_id)
    
    # Query MUST filter by organization
    result = await db.execute(
        select(Finding).where(Finding.organization_id == org_id)
    )
    findings = result.scalars().all()
    return findings
```

## Common Permission Checks

### Owner-Only Operations

```python
# Update organization settings
await rbac.enforce_permission(
    user_id, org_id, Permission.MANAGE_ORG
)
```

### Admin+ Operations

```python
# Manage team members
await rbac.enforce_permission(
    user_id, org_id, Permission.MANAGE_MEMBERS
)

# Manage findings
await rbac.enforce_permission(
    user_id, org_id, Permission.MANAGE_FINDINGS
)
```

### Analyst+ Operations

```python
# Run scans
await rbac.enforce_permission(
    user_id, org_id, Permission.RUN_SCANS
)
```

### Everyone (Viewer+) Operations

```python
# View findings (all roles)
await rbac.enforce_permission(
    user_id, org_id, Permission.VIEW_FINDINGS
)
```

## Organization Service Usage

### Create Organization

```python
from backend.services.organization_service import OrganizationService

org_service = OrganizationService(db)
org = await org_service.create_organization(
    user_id=current_user.id,
    name="Team Name",
    slug="team-slug",
    description="Description"
)
```

### Invite Member

```python
member = await org_service.invite_member(
    organization_id=org_id,
    user_id=new_user_id,
    role="analyst",
    invited_by_id=current_user.id
)
```

### Get Organization Members

```python
members = await org_service.get_organization_members(org_id)
for member in members:
    print(f"{member.user.username}: {member.role}")
```

### Update Member Role

```python
member = await org_service.update_member_role(
    organization_id=org_id,
    member_id=member_id,
    new_role="admin"
)
```

### Remove Member

```python
await org_service.remove_member(org_id, member_id)
```

## RBAC Service Methods

### Check Permission

```python
# Returns True/False
has_perm = await rbac.has_permission(
    user_id, org_id, Permission.RUN_SCANS
)
```

### Enforce Permission

```python
# Raises HTTPException if denied
await rbac.enforce_permission(
    user_id, org_id, Permission.RUN_SCANS, "Running scans"
)
```

### Get User Role

```python
role = await rbac.get_user_role(user_id, org_id)
# Returns MemberRole enum or None
```

### Get Permissions for Role

```python
perms = await rbac.get_permissions_for_role(MemberRole.ANALYST)
# Returns set of Permission enums
```

### Validate Workspace Access

```python
# Raises HTTPException if not a member
await rbac.validate_workspace_access(user_id, org_id)
```

### Check Is Organization Owner

```python
is_owner = await rbac.is_organization_owner(user_id, org_id)
```

## Database Queries with Organization Isolation

### Query Programs in Organization

```python
from sqlalchemy import select
from backend.models.program import Program

result = await db.execute(
    select(Program).where(Program.organization_id == org_id)
)
programs = result.scalars().all()
```

### Query Scans in Organization

```python
from backend.models.scan import Scan

result = await db.execute(
    select(Scan).where(Scan.organization_id == org_id)
)
scans = result.scalars().all()
```

### Query Findings in Organization

```python
from backend.models.finding import Finding

result = await db.execute(
    select(Finding).where(Finding.organization_id == org_id)
)
findings = result.scalars().all()
```

### Complex Query with Organization + Status Filter

```python
from sqlalchemy import select, and_
from backend.models.finding import Finding, FindingStatus

result = await db.execute(
    select(Finding).where(
        and_(
            Finding.organization_id == org_id,
            Finding.status == FindingStatus.open,
            Finding.severity == SeverityLevel.critical
        )
    )
)
critical_findings = result.scalars().all()
```

## Error Handling

### Handle Permission Denied

```python
try:
    await rbac.enforce_permission(user_id, org_id, Permission.MANAGE_ORG)
except HTTPException as e:
    # e.status_code == 403
    # e.detail contains permission error message
    print(f"Access denied: {e.detail}")
```

### Handle Organization Not Found

```python
org = await org_service.get_organization(org_id)
if not org:
    raise HTTPException(
        status_code=404,
        detail="Organization not found"
    )
```

### Handle User Not a Member

```python
member = await org_service.get_member_by_user_and_org(user_id, org_id)
if not member or not member.is_active:
    raise HTTPException(
        status_code=403,
        detail="You are not a member of this organization"
    )
```

## Testing RBAC

### Test Permission Granted

```python
# Setup
rbac = RBACService(db)
org = await org_service.create_organization(user1_id, "Test", "test")

# Test
can_run = await rbac.has_permission(user1_id, org.id, Permission.RUN_SCANS)
assert can_run == True  # Owner can run scans
```

### Test Permission Denied

```python
# Setup
viewer_member = await org_service.invite_member(
    org.id, user2_id, "viewer", user1_id
)

# Test
can_manage = await rbac.has_permission(user2_id, org.id, Permission.MANAGE_ORG)
assert can_manage == False  # Viewers cannot manage org
```

### Test Workspace Isolation

```python
# Create two organizations
org1 = await org_service.create_organization(user1_id, "Org1", "org1")
org2 = await org_service.create_organization(user1_id, "Org2", "org2")

# User should not access org2 data from org1 context
result = await db.execute(
    select(Program).where(Program.organization_id == org1.id)
)
org1_programs = result.scalars().all()
# Should only contain programs created in org1
```

## Migrating Existing Models

### Adding organization_id to existing models:

```python
# In migration:
op.add_column('programs', sa.Column('organization_id', sa.UUID(), nullable=True))
op.create_foreign_key(
    'fk_programs_organization_id',
    'programs', 'organizations',
    ['organization_id'], ['id'],
    ondelete='CASCADE'
)

# Then backfill:
op.execute("""
    UPDATE programs
    SET organization_id = (SELECT id FROM organizations LIMIT 1)
    WHERE organization_id IS NULL
""")

# Finally make NOT NULL:
op.alter_column('programs', 'organization_id', nullable=False)
```

## Common Patterns

### Protected Route Pattern

```python
@router.post("/{org_id}/action")
async def perform_action(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service),
    org_service: OrganizationService = Depends(get_org_service),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate workspace access
    await rbac.validate_workspace_access(current_user.id, org_id)
    
    # 2. Check specific permission
    await rbac.enforce_permission(
        current_user.id, org_id, Permission.PERFORM_ACTION
    )
    
    # 3. Verify resource exists in organization
    resource = await db.execute(
        select(Resource).where(
            and_(Resource.id == resource_id, Resource.organization_id == org_id)
        )
    )
    if not resource.scalars().first():
        raise HTTPException(404, "Resource not found")
    
    # 4. Perform action with organization context
    # ... your business logic ...
    
    return result
```

## Debugging

### Check if User is Member

```python
member = await org_service.get_member_by_user_and_org(user_id, org_id)
print(f"Member: {member}")
print(f"Role: {member.role if member else 'Not a member'}")
print(f"Active: {member.is_active if member else 'N/A'}")
```

### Check User's Permissions

```python
role = await rbac.get_user_role(user_id, org_id)
perms = await rbac.get_permissions_for_role(role)
print(f"Role: {role}")
print(f"Permissions: {[p.value for p in perms]}")
```

### Verify Organization Isolation

```python
# Count findings per org
for org in user_orgs:
    result = await db.execute(
        select(Finding).where(Finding.organization_id == org.id)
    )
    findings = result.scalars().all()
    print(f"Org {org.slug}: {len(findings)} findings")
```

---

**Note**: Always remember:
- ✓ Validate workspace access first
- ✓ Check permission for sensitive operations
- ✓ Filter by organization_id in all queries
- ✓ Never trust frontend authorization
- ✗ Don't skip permission checks
- ✗ Don't forget organization filtering in queries
