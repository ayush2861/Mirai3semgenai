"""
FastAPI Dependencies Module.
Provides dependency injection for user authentication, security, and tenant context.
"""

import logging
from typing import Optional
from fastapi import Header, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import UnauthorizedAccessError
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Extracts authenticated user ID:
    1. If JWT Bearer token is provided in Authorization header, decode and verify.
    2. Else if X-User-ID header is provided (e.g. testing or server-to-server), use it.
    3. Otherwise, fallback to settings.DEFAULT_USER_ID.
    """
    # 1. Bearer Token Verification
    if auth_credentials and auth_credentials.credentials:
        try:
            payload = auth_service.verify_token(auth_credentials.credentials)
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except Exception as e:
            logger.warning(f"Bearer token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )

    # 2. X-User-ID Header fallback (for automated integration test suites)
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    # 3. Default User
    return settings.DEFAULT_USER_ID
