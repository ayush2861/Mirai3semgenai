import os
from pathlib import Path
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "InfraMind API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 25

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # Directories & Persistent Disk
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    # Render persistent disk mount point is typically /var/data
    PERSISTENT_DISK_PATH: Optional[str] = None
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    CHROMA_DIR: Path = DATA_DIR / "chroma"
    USERS_DIR: Path = DATA_DIR / "users"

    # Authentication & Security
    JWT_SECRET_KEY: str = "inframind_jwt_secret_production_key_safe_hash_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    DEFAULT_USER_ID: str = "default_user"

    # Vector & Embedding Settings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_COLLECTION_NAME: str = "inframind_knowledge"

    # Gemini AI Provider Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.8-flash,gemini-3.1-flash-lite"
    LLM_PROVIDER: str = "gemini"
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048
    GEMINI_TEMPERATURE: float = 0.2
    
    # RAG Context & Token Management
    MAX_CONTEXT_CHUNKS: int = 6
    MAX_CONTEXT_CHARS: int = 8000

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

# Check for Render persistent disk environment configuration
if os.getenv("RENDER") or os.getenv("CHROMA_PERSIST_DIRECTORY"):
    if os.getenv("CHROMA_PERSIST_DIRECTORY"):
        settings.CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIRECTORY"))
    if os.getenv("UPLOAD_DIRECTORY"):
        settings.UPLOADS_DIR = Path(os.getenv("UPLOAD_DIRECTORY"))
    if os.getenv("DATA_DIRECTORY"):
        settings.DATA_DIR = Path(os.getenv("DATA_DIRECTORY"))
        settings.PROCESSED_DIR = settings.DATA_DIR / "processed"
        settings.USERS_DIR = settings.DATA_DIR / "users"

# Ensure required runtime directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
settings.USERS_DIR.mkdir(parents=True, exist_ok=True)
