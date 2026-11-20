"""
Legacy alias service module.
Routes processing requests to app.services.pdf.processing_service.universal_processing_service.
"""
from app.services.pdf.processing_service import (
    UniversalProcessingService,
    universal_processing_service,
    universal_processing_service as processing_service
)

__all__ = [
    "UniversalProcessingService",
    "universal_processing_service",
    "processing_service"
]
