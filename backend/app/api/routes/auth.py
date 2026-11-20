"""
Authentication API Endpoints (Phase 7).
Supports user registration, login, and profile retrieval for 10-15 users on Render.
"""

from fastapi import APIRouter, Depends, status
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse
)
from app.services.auth_service import auth_service
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest):
    """
    Registers a new user and issues a signed JWT access token.
    """
    return auth_service.register_user(req)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(req: UserLoginRequest):
    """
    Authenticates user credentials and issues a signed JWT access token.
    """
    return auth_service.login_user(req)


@router.get("/me", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def get_me(user_id: str = Depends(get_current_user_id)):
    """
    Returns the authenticated user's profile and active session status.
    """
    return auth_service.get_user_profile(user_id)
