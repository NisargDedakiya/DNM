from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["web"])

BASE_DIR = Path(__file__).resolve().parents[3]
LOGIN_PAGE = BASE_DIR / "frontend" / "login.html"


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/login")


@router.get("/login", include_in_schema=False)
async def login_page() -> FileResponse:
    return FileResponse(LOGIN_PAGE)
