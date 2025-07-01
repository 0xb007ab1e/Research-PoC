"""
MCP Context Service

A FastAPI-based context management service designed for multi-tenant environments
with comprehensive security and observability features.
"""

__version__ = "1.0.0"
__author__ = "MCP Team"
__description__ = "Multi-tenant context management service"

# Import main application components for easier access
from .main import app
from .config import settings
from .models import (
    ContextCreateRequest,
    ContextUpdateRequest,
    ContextResponse,
    HealthCheckResponse,
    ErrorResponse,
)
from .repository import ContextRepository, DatabaseError

__all__ = [
    "app",
    "settings",
    "ContextCreateRequest",
    "ContextUpdateRequest",
    "ContextResponse",
    "HealthCheckResponse",
    "ErrorResponse",
    "ContextRepository",
    "DatabaseError",
]
