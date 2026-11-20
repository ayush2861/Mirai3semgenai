from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
@router.head("/health")
async def health_check():
    """
    Verifies that the InfraMind backend API is active and healthy.
    """
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.VERSION
    }
