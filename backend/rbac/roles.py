from typing import List, Dict
from backend.rbac.permissions import Permission

class Role:
    OWNER = "owner"
    ADMIN = "admin"
    HUNTER = "hunter"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    READ_ONLY = "read_only"

ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    Role.OWNER: list(Permission),
    
    Role.ADMIN: [
        Permission.FINDINGS_READ, Permission.FINDINGS_WRITE,
        Permission.REPORTS_SUBMIT, Permission.SCANS_EXECUTE,
        Permission.APPROVALS_GRANT, Permission.GRAPH_READ,
        Permission.SCHEDULER_MANAGE, Permission.ORG_MANAGE
    ],
    
    Role.HUNTER: [
        Permission.FINDINGS_READ, Permission.FINDINGS_WRITE,
        Permission.SCANS_EXECUTE, Permission.GRAPH_READ
    ],
    
    Role.ANALYST: [
        Permission.FINDINGS_READ, Permission.GRAPH_READ,
        Permission.REPORTS_SUBMIT
    ],
    
    Role.REVIEWER: [
        Permission.FINDINGS_READ, Permission.GRAPH_READ,
        Permission.APPROVALS_GRANT
    ],
    
    Role.READ_ONLY: [
        Permission.FINDINGS_READ, Permission.GRAPH_READ
    ]
}
