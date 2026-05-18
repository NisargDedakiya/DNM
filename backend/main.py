"""
FastAPI application entry point.
Main application factory with lifespan management and middleware configuration.
"""
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings
from backend.core.redis import close_redis, connect_redis
from backend.database.session import close_db, init_db
from backend.api.routes import health
from backend.api.routes import auth as auth_routes
from backend.api.routes import web as web_routes
from backend.api.routes import programs as programs_routes
from backend.api.routes import scans as scans_routes
from backend.api.routes import findings as findings_routes
from backend.api.routes import organizations as organizations_routes
from backend.api.routes import monitoring as monitoring_routes
from backend.api.routes import exposure as exposure_routes
from backend.api.routes import recon_ai as recon_ai_routes
from backend.api.routes import dashboard as dashboard_routes
from backend.api.routes import assets as assets_routes
from backend.api.routes import websocket as websocket_routes
from backend.api.routes import timeline as timeline_routes
from backend.api.routes import graph as graph_routes
from backend.api.routes import executive as executive_routes
from backend.api.routes import copilot as copilot_routes
from backend.api.routes import integrations as integrations_routes
from backend.api.routes import notifications as notifications_routes
from backend.api.routes import hackerone as hackerone_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    try:
        await init_db()
    except Exception as exc:
        logger.warning("Database initialization skipped: %s", exc)

    try:
        await connect_redis()
    except Exception as exc:
        logger.warning("Redis initialization skipped: %s", exc)

    yield

    # Shutdown
    try:
        await close_redis()
    except Exception as exc:
        logger.warning("Redis shutdown skipped: %s", exc)

    try:
        await close_db()
    except Exception as exc:
        logger.warning("Database shutdown skipped: %s", exc)


def create_app() -> FastAPI:
    """
    Application factory.
    Creates and configures FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["localhost", "127.0.0.1"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # app.mount("/static", StaticFiles(directory="frontend"), name="static")

    api_router = APIRouter(prefix="/api")
    
    # Register routers under /api
    api_router.include_router(health.router)
    api_router.include_router(auth_routes.router)
    api_router.include_router(organizations_routes.router)
    api_router.include_router(programs_routes.router)
    api_router.include_router(monitoring_routes.router)
    api_router.include_router(exposure_routes.router)
    api_router.include_router(scans_routes.router)
    api_router.include_router(findings_routes.router)
    api_router.include_router(assets_routes.router)
    api_router.include_router(dashboard_routes.router)
    api_router.include_router(recon_ai_routes.router)
    api_router.include_router(websocket_routes.router)
    api_router.include_router(timeline_routes.router)
    api_router.include_router(graph_routes.router)
    api_router.include_router(executive_routes.router)
    api_router.include_router(copilot_routes.router)
    api_router.include_router(integrations_routes.router)
    api_router.include_router(notifications_routes.router)
    api_router.include_router(hackerone_routes.router)
    api_router.include_router(web_routes.router)
    
    app.include_router(api_router)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
