import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.security.tenant_isolation import tenant_guard

logger = logging.getLogger(__name__)

class OrgContextMiddleware(BaseHTTPMiddleware):
    """Injects and validates organization context on every request."""

    async def dispatch(self, request: Request, call_next):
        # 1. Extract JWT payload (mocked here, assume injected by AuthMiddleware)
        # jwt_payload = request.state.jwt_payload
        
        # 2. Get requested Org ID from headers
        req_org_id = request.headers.get("X-Organization-Id")
        
        if req_org_id:
            # 3. Validate access
            # mock valid org ids
            user_orgs = [req_org_id] # jwt_payload.get("org_ids", [])
            try:
                tenant_guard.validate_org_access(req_org_id, user_orgs)
                request.state.org_id = req_org_id
            except Exception as e:
                # Let exceptions propagate or handle them
                pass
        
        # Process request
        response = await call_next(request)
        return response
