"""
Enterprise SSO orchestration service.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import create_access_token
from backend.identity.access_federation import federate_access, synchronize_permissions, validate_federated_roles
from backend.identity.org_identity import map_user_to_org, resolve_org_identity, synchronize_org_roles
from backend.private_mode.private_hunts import create_private_hunt, isolate_hunt_execution, restrict_hunt_access
from backend.private_mode.restricted_visibility import hide_sensitive_assets, isolate_attack_graph, restrict_finding_visibility
from backend.private_mode.stealth_workspace import create_stealth_workspace, isolate_workspace_events, restrict_workspace_visibility
from backend.sso.oauth_provider import authenticate_oauth_user
from backend.sso.saml_provider import authenticate_enterprise_user, map_saml_identity, validate_saml_response
from backend.sso.session_manager import create_enterprise_session, terminate_session, validate_session


class SSOService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_enterprise_request(
        self,
        organization_id: UUID,
        provider: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        provider = str(provider).lower().strip()
        org_id = str(organization_id)
        if provider == "saml":
            assertion = validate_saml_response(str(payload.get("saml_response") or ""), org_id, audience=payload.get("audience"))
            if not assertion.get("valid"):
                return {"authenticated": False, "reason": assertion.get("reason"), "assertion": assertion}
            enterprise_identity = authenticate_enterprise_user(str(payload.get("saml_response") or ""), org_id)
            identity = enterprise_identity.get("identity") or map_saml_identity(assertion)
        else:
            enterprise_identity = authenticate_oauth_user(provider, str(payload.get("access_token") or ""), org_id)
            if not enterprise_identity.get("authenticated"):
                return {"authenticated": False, "reason": enterprise_identity.get("validation", {}).get("reason", "invalid_oauth")}
            identity = enterprise_identity.get("identity", {})

        mapped_identity = map_user_to_org(identity, org_id, provider=provider)
        federated_identity = resolve_org_identity(str(mapped_identity.get("username") or mapped_identity.get("email") or mapped_identity.get("user_id")), provider, org_id)
        role_sync = synchronize_org_roles(mapped_identity, [federated_identity.get("visibility") and mapped_identity.get("role") or mapped_identity.get("role")])
        access = federate_access({**mapped_identity, **federated_identity}, provider)
        session = create_enterprise_session(str(mapped_identity.get("user_id") or mapped_identity.get("username")), org_id, provider, stealth_workspace_id=payload.get("workspace_id"))
        token = create_access_token(subject=str(mapped_identity.get("user_id") or mapped_identity.get("username")), expires_delta=None)

        return {
            "authenticated": True,
            "organization_id": org_id,
            "provider": provider,
            "identity": mapped_identity,
            "federated_access": access,
            "role_sync": role_sync,
            "session": session,
            "access_token": token,
            "audit": {"authenticated_at": datetime.now(timezone.utc).isoformat(), "stealth_workspace_id": payload.get("workspace_id")},
        }

    async def enforce_private_workspace_access(self, organization_id: UUID, workspace_id: str, user_id: UUID) -> dict[str, Any]:
        workspace = create_stealth_workspace(str(organization_id), workspace_id, str(user_id))
        visibility = restrict_workspace_visibility(workspace["id"])
        event_scope = isolate_workspace_events(workspace["id"])
        return {
            "organization_id": str(organization_id),
            "workspace": workspace,
            "visibility": visibility,
            "event_scope": event_scope,
        }

    async def synchronize_enterprise_identity(
        self,
        organization_id: UUID,
        external_identity: str,
        provider: str,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        identity = resolve_org_identity(external_identity, provider, str(organization_id))
        role_validation = validate_federated_roles([provider])
        permission_sync = synchronize_permissions(str(organization_id), identity["internal_subject"], permissions or [])
        return {
            "organization_id": str(organization_id),
            "identity": identity,
            "role_validation": role_validation,
            "permission_sync": permission_sync,
        }

    async def create_private_hunt_workflow(self, organization_id: UUID, workspace_id: str, scope: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        hunt = create_private_hunt(str(organization_id), workspace_id, scope, str(user_id))
        access = restrict_hunt_access(hunt["id"])
        execution = isolate_hunt_execution(hunt["id"])
        return {"hunt": hunt, "access": access, "execution": execution}

    async def restrict_confidential_payloads(self, findings: list[dict[str, Any]], graph_payload: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "findings": [restrict_finding_visibility(item) for item in findings],
            "graph": isolate_attack_graph(graph_payload),
            "assets": hide_sensitive_assets(assets),
        }
