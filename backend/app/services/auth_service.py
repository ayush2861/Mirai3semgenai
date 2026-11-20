"""
User Authentication and Token Management Service (Phase 7).
Handles password hashing (bcrypt), JWT generation, validation, and user persistence.
"""

import os
import json
import uuid
import time
import bcrypt
import jwt
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.exceptions import UnauthorizedAccessError, BadRequestError
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Manages user registration, secure credential verification, JWT minting,
    and persistent storage on persistent disk.
    """

    def __init__(self):
        self.storage_file: Path = settings.USERS_DIR / "users.json"
        self._init_storage()

    def _init_storage(self):
        settings.USERS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            # Seed default admin user for initial 10-15 user deployment
            default_salt = bcrypt.gensalt()
            default_hash = bcrypt.hashpw(b"InfraMind2026!", default_salt).decode("utf-8")
            initial_data = {
                "user-admin-01": {
                    "user_id": "user-admin-01",
                    "email": "admin@inframind.ai",
                    "username": "admin",
                    "password_hash": default_hash,
                    "full_name": "SRE Lead Administrator",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                }
            }
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)
            logger.info("Initialized user database with default administrative credentials.")

    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users storage: {e}")
            return {}

    def _save_users(self, data: Dict[str, Dict[str, Any]]):
        temp_file = self.storage_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, self.storage_file)

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def create_access_token(self, user_id: str, email: str, username: str) -> tuple[str, int]:
        expire_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_at = datetime.now(timezone.utc) + expire_delta

        payload = {
            "sub": user_id,
            "email": email,
            "username": username,
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, int(expire_delta.total_seconds())

    def register_user(self, req: UserRegisterRequest) -> TokenResponse:
        users = self._load_users()

        # Check uniqueness of email and username
        for u in users.values():
            if u["email"].lower() == req.email.lower():
                raise BadRequestError(f"User with email '{req.email}' already exists.")
            if u["username"].lower() == req.username.lower():
                raise BadRequestError(f"Username '{req.username}' is already taken.")

        user_id = f"user-{uuid.uuid4().hex[:12]}"
        password_hash = self.hash_password(req.password)
        now_str = datetime.now(timezone.utc).isoformat()

        user_data = {
            "user_id": user_id,
            "email": req.email.lower(),
            "username": req.username,
            "password_hash": password_hash,
            "full_name": req.full_name or req.username,
            "created_at": now_str,
            "is_active": True
        }
        users[user_id] = user_data
        self._save_users(users)
        logger.info(f"Registered new user: {req.username} ({req.email}) -> ID: {user_id}")

        token, expires_in = self.create_access_token(user_id, req.email, req.username)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user_id,
            email=req.email,
            username=req.username,
            full_name=user_data["full_name"],
            expires_in=expires_in
        )

    def login_user(self, req: UserLoginRequest) -> TokenResponse:
        users = self._load_users()
        matching_user = None

        for u in users.values():
            if u["email"].lower() == req.email.lower():
                matching_user = u
                break

        if not matching_user or not self.verify_password(req.password, matching_user["password_hash"]):
            raise UnauthorizedAccessError("Invalid email or password.")

        if not matching_user.get("is_active", True):
            raise UnauthorizedAccessError("User account is deactivated.")

        token, expires_in = self.create_access_token(
            matching_user["user_id"],
            matching_user["email"],
            matching_user["username"]
        )
        logger.info(f"User logged in successfully: {matching_user['username']} ({matching_user['email']})")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=matching_user["user_id"],
            email=matching_user["email"],
            username=matching_user["username"],
            full_name=matching_user.get("full_name"),
            expires_in=expires_in
        )

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedAccessError("Authentication token has expired.")
        except jwt.InvalidTokenError:
            raise UnauthorizedAccessError("Invalid authentication token.")

    def get_user_profile(self, user_id: str) -> UserProfileResponse:
        users = self._load_users()
        if user_id not in users:
            raise UnauthorizedAccessError("User not found.")
        u = users[user_id]
        return UserProfileResponse(
            user_id=u["user_id"],
            username=u["username"],
            email=u["email"],
            full_name=u.get("full_name"),
            created_at=u["created_at"],
            is_active=u.get("is_active", True)
        )


Tuple_Token = tuple[str, int]
auth_service = AuthService()
