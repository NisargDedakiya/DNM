"""
Developer ecosystem orchestration service.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.permissions import Permission
from backend.hardening.rate_limiter import enforce_rate_limit
from backend.models.api_key import ApiKey
from backend.models.developer_application import DeveloperApplication
from backend.models.webhook_subscription import WebhookSubscription


class DeveloperService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _hash_key(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    async def generate_api_key(
        self,
        organization_id: UUID,
        name: str,
        permissions: list[str] | None = None,
        rate_limit: dict | None = None,
        application_name: str | None = None,
    ) -> dict:
        secret = secrets.token_urlsafe(40)
        api_key = ApiKey(
            organization_id=organization_id,
            key_hash=self._hash_key(secret),
            permissions=permissions or [Permission.VIEW_FINDINGS.value, Permission.VIEW_ASSETS.value],
            rate_limit=rate_limit or {"requests_per_minute": 120, "requests_per_hour": 2000},
        )
        self.db.add(api_key)
        await self.db.flush()

        application = None
        if application_name:
            application = DeveloperApplication(
                organization_id=organization_id,
                name=application_name,
                api_key_id=api_key.id,
                usage_stats={"requests": 0, "last_used_at": None},
            )
            self.db.add(application)

        await self.db.commit()
        await self.db.refresh(api_key)
        if application is not None:
            await self.db.refresh(application)

        return {
            "id": api_key.id,
            "organization_id": api_key.organization_id,
            "name": name,
            "secret": secret,
            "permissions": api_key.permissions or [],
            "rate_limit": api_key.rate_limit or {},
            "application": None if application is None else {
                "id": application.id,
                "name": application.name,
                "usage_stats": application.usage_stats or {},
            },
            "created_at": api_key.created_at,
        }

    async def validate_developer_request(
        self,
        organization_id: UUID,
        api_key_secret: str,
        endpoint: str,
        required_permission: str | None = None,
    ) -> dict:
        key_hash = self._hash_key(api_key_secret)
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.organization_id == organization_id,
                ApiKey.key_hash == key_hash,
            ),
        )
        api_key = result.scalars().first()
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        permissions = [str(permission) for permission in (api_key.permissions or [])]
        if required_permission and required_permission not in permissions and "*" not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key lacks required permission")

        budget = api_key.rate_limit or {"requests_per_minute": 120}
        allowed = await enforce_rate_limit(
            organization_id=organization_id,
            bucket=f"api-key:{api_key.id}:{endpoint}",
            limit=int(budget.get("requests_per_minute", 120)),
            window_seconds=60,
        )
        if not allowed["allowed"]:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        app_result = await self.db.execute(
            select(DeveloperApplication).where(DeveloperApplication.api_key_id == api_key.id),
        )
        application = app_result.scalars().first()
        if application is not None:
            stats = dict(application.usage_stats or {})
            stats["requests"] = int(stats.get("requests", 0)) + 1
            stats["last_used_at"] = datetime.now(timezone.utc).isoformat()
            application.usage_stats = stats
            await self.db.commit()

        return {
            "api_key_id": api_key.id,
            "organization_id": api_key.organization_id,
            "permissions": permissions,
            "rate_limit": api_key.rate_limit or {},
            "allowance": allowed,
        }

    async def generate_usage_summary(self, organization_id: UUID) -> dict:
        api_key_count = await self.db.scalar(
            select(func.count(ApiKey.id)).where(ApiKey.organization_id == organization_id),
        )
        webhook_count = await self.db.scalar(
            select(func.count(WebhookSubscription.id)).where(WebhookSubscription.organization_id == organization_id),
        )
        app_count = await self.db.scalar(
            select(func.count(DeveloperApplication.id)).where(DeveloperApplication.organization_id == organization_id),
        )
        apps = await self.db.execute(
            select(DeveloperApplication).where(DeveloperApplication.organization_id == organization_id),
        )
        application_rows = apps.scalars().all()

        return {
            "organization_id": organization_id,
            "api_keys": int(api_key_count or 0),
            "webhooks": int(webhook_count or 0),
            "applications": int(app_count or 0),
            "recent_applications": [
                {
                    "id": app.id,
                    "name": app.name,
                    "usage_stats": app.usage_stats or {},
                    "created_at": app.created_at,
                }
                for app in application_rows[:10]
            ],
        }
