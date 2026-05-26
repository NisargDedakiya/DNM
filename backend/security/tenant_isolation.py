import logging
from typing import Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class TenantIsolationGuard:
    """Enforces absolute organization boundaries for database and operations."""

    def validate_org_access(self, request_org_id: str, jwt_org_ids: list[str]):
        """Ensure the user is requesting an org they actually belong to."""
        if request_org_id not in jwt_org_ids:
            logger.critical(f"Cross-tenant access attempt blocked! Requested: {request_org_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant isolation violation."
            )

    def isolate_query(self, query: Any, org_id: str, model_class: Any) -> Any:
        """Automatically append an org_id filter to a SQLAlchemy query."""
        if not hasattr(model_class, 'organization_id'):
            raise ValueError(f"Model {model_class} lacks organization_id for isolation.")
        return query.filter(model_class.organization_id == org_id)

    def enforce_org_boundary(self, entity: Any, expected_org_id: str):
        """Verify an individual record belongs to the expected org."""
        if getattr(entity, 'organization_id', None) != expected_org_id:
            logger.critical(f"Data leak prevented! Entity org mismatch.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Boundary violation.")

tenant_guard = TenantIsolationGuard()
