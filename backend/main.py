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
from backend.api.routes import grid as grid_routes
from backend.api.routes import performance as performance_routes
from backend.api.routes import sensei as sensei_routes
from backend.api.routes import ai as ai_routes
from backend.api.routes import scheduler as scheduler_routes

from backend.api.routes import sso as sso_routes
from backend.api.routes import exposure as exposure_routes
from backend.api.routes import recon_ai as recon_ai_routes
from backend.api.routes import dashboard as dashboard_routes
from backend.api.routes import assets as assets_routes
from backend.api.routes import websocket as websocket_routes
from backend.api.routes import timeline as timeline_routes
from backend.api.routes import history as history_routes
from backend.api.routes import graph as graph_routes
from backend.api.routes import executive as executive_routes
from backend.api.routes import copilot as copilot_routes
from backend.api.routes import integrations as integrations_routes
from backend.api.routes import notifications as notifications_routes
from backend.api.routes import hackerone as hackerone_routes
from backend.api.routes import reports as reports_routes
from backend.api.routes import cluster as cluster_routes
from backend.api.routes import collaboration as collaboration_routes
from backend.api.routes import threat as threat_routes
from backend.api.routes import attack as attack_routes
from backend.api.routes import security as security_routes
from backend.api.routes import developer as developer_routes
from backend.api.routes import strategy as strategy_routes
from backend.api.routes import marketplace as marketplace_routes
from backend.api.public import rest_api as public_rest_api
from backend.api.public import graphql_api as public_graphql_api

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

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from backend.workers.scheduler import execute_monitoring_scheduler
    from backend.recovery.disaster_recovery import cleanup_orphan_jobs
    import asyncio

    async def execute_orphan_cleanup():
        from backend.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                count = await cleanup_orphan_jobs(db)
                if count > 0:
                    logger.info(f"Orphan job cleanup daemon recovered {count} stuck tasks.")
            except Exception as e:
                logger.error(f"Error in periodic orphan job cleanup: {e}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(execute_monitoring_scheduler, 'interval', minutes=5, id='monitoring')
    scheduler.add_job(execute_orphan_cleanup, 'interval', minutes=1, id='orphan_cleanup')
    scheduler.start()
    
    # Run immediate cleanup once in background on startup
    asyncio.create_task(execute_orphan_cleanup())

    yield

    # Shutdown
    try:
        scheduler.shutdown()
    except Exception as exc:
        logger.warning("Scheduler shutdown skipped: %s", exc)

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
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Secure CSP middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> Response:
            response = await call_next(request)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self' ws: wss:;"
            )
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # app.mount("/static", StaticFiles(directory="frontend"), name="static")

    api_router = APIRouter(prefix="/api")
    
    # Register routers under /api
    api_router.include_router(health.router)
    api_router.include_router(auth_routes.router)
    api_router.include_router(organizations_routes.router)
    api_router.include_router(programs_routes.router)
    api_router.include_router(monitoring_routes.router)
    api_router.include_router(grid_routes.router)
    api_router.include_router(performance_routes.router)
    api_router.include_router(sensei_routes.router)
    api_router.include_router(ai_routes.router)
    api_router.include_router(scheduler_routes.router)

    api_router.include_router(sso_routes.router)
    api_router.include_router(exposure_routes.router)
    api_router.include_router(exposure_routes.timeline_router)
    api_router.include_router(scans_routes.router)
    api_router.include_router(findings_routes.router)
    api_router.include_router(assets_routes.router)
    api_router.include_router(dashboard_routes.router)
    api_router.include_router(recon_ai_routes.router)
    api_router.include_router(websocket_routes.router)
    api_router.include_router(timeline_routes.router)
    api_router.include_router(history_routes.router)
    api_router.include_router(graph_routes.router)
    api_router.include_router(executive_routes.router)
    api_router.include_router(copilot_routes.router)
    api_router.include_router(integrations_routes.router)
    api_router.include_router(notifications_routes.router)
    api_router.include_router(hackerone_routes.router)
    api_router.include_router(reports_routes.router)
    api_router.include_router(cluster_routes.router)
    api_router.include_router(collaboration_routes.router)
    api_router.include_router(threat_routes.router)
    api_router.include_router(attack_routes.router)
    api_router.include_router(security_routes.router)
    api_router.include_router(developer_routes.router)
    api_router.include_router(strategy_routes.router)
    api_router.include_router(marketplace_routes.router)
    api_router.include_router(public_rest_api.router)
    api_router.include_router(public_graphql_api.router)
    from backend.api.routes import observability_dashboard as observability_routes
    api_router.include_router(observability_routes.router)
    app.include_router(health.router)
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
