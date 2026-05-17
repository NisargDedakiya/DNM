"""
Health check endpoints.
Provides service status and diagnostic information.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service status and version

    Example:
        GET /health
        Response: {"status": "ok", "version": "1.0.0"}
    """
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )
