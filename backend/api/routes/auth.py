from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from backend.database.session import get_db
from backend.services.auth_service import AuthService
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    try:
        user = await svc.register_user(username=payload.username, email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return UserResponse.from_orm(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    token = await svc.authenticate_user(username=payload.username, password=payload.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = await svc.get_by_username(payload.username)
    return TokenResponse(access_token=token, expires_in=8 * 3600, user=UserResponse.from_orm(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return UserResponse.from_orm(current_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(current_user=Depends(get_current_user)):
    # For now, return a new token for the current user
    # In a full implementation, this should validate an HttpOnly refresh cookie
    from backend.auth.jwt_handler import create_access_token
    from datetime import timedelta
    token = create_access_token(subject=str(current_user.id), expires_delta=timedelta(hours=8))
    return TokenResponse(access_token=token, expires_in=8 * 3600, user=UserResponse.from_orm(current_user))


@router.post("/logout")
async def logout():
    # In a full implementation, this would clear the HttpOnly refresh cookie
    return {"message": "Logged out successfully"}
