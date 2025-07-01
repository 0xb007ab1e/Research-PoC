"""
MCP Text Summarization Service

A secure, high-performance text summarization service with multiple AI model support,
semantic validation, and fallback mechanisms.
"""

from .pipeline import generate_summary, get_pipeline
from .models import SummarizationRequest, SummarizationResponse, ErrorResponse

__version__ = "1.0.0"
__all__ = [
    "generate_summary",
    "get_pipeline", 
    "SummarizationRequest",
    "SummarizationResponse",
    "ErrorResponse"
]
