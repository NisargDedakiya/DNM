import logging
from typing import List
from fastapi import HTTPException, status
from backend.rbac.permissions import Permission
from backend.rbac.roles import ROLE_PERMISSIONS

logger = logging.getLogger(__name__)

class AccessControl:
    """Core RBAC validation logic."""

    def has_permission(self, user_role: str, required_permission: Permission) -> bool:
        if user_role not in ROLE_PERMISSIONS:
            return False
        return required_permission in ROLE_PERMISSIONS[user_role]

    def require_permission(self, user_role: str, required_permission: Permission):
        """Used in route dependencies to enforce access."""
        if not self.has_permission(user_role, required_permission):
            logger.warning(f"Access denied: {user_role} missing {required_permission}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {required_permission}"
            )

    def validate_role_access(self, user_role: str, allowed_roles: List[str]):
        """Check if user role is within a permitted list of roles."""
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not authorized for this action."
            )

access_control = AccessControl()
