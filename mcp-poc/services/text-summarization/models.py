"""
Pydantic models for the MCP Text Summarization Service
Defines request/response schemas with validation and security considerations
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

class SummarizationRequest(BaseModel):
    """Request model for text summarization with semantic validation"""
    
    # Required fields
    text_blob: str = Field(
        ...,
        min_length=100,
        max_length=50000,
        description="The text to be summarized"
    )
    
    semantic_threshold: float = Field(
        default=0.8,
        ge=0.6,
        le=0.95,
        description="Minimum semantic similarity score between original and summarized text"
    )
    
    # Optional fields with defaults
    ai_model: str = Field(
        default="openai",
        description="AI model to use for summarization (openai, huggingface, local)"
    )
    
    api_token: Optional[str] = Field(
        default=None,
        description="API token for the specified AI model (if required)"
    )
    
    # Advanced parameters
    max_summary_length: Optional[int] = Field(
        default=500,
        ge=50,
        le=1000,
        description="Maximum length of the summary in characters"
    )
    
    summary_ratio: Optional[float] = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Target ratio of summary length to original text length"
    )
    
    retry_attempts: Optional[int] = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of retry attempts if semantic threshold is not met"
    )
    
    # Tenant and user context
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant environments"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier for audit and tracking"
    )
    
    # Request metadata
    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request"
    )
    
    @validator('text_blob')
    def validate_text_content(cls, v):
        """Validate text content for security and quality"""
        
        # Remove excessive whitespace
        v = ' '.join(v.split())
        
        # Check for minimum word count
        word_count = len(v.split())
        if word_count < 20:
            raise ValueError('Text must contain at least 20 words')
        
        # Basic security check for potentially malicious content
        suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
        v_lower = v.lower()
        for pattern in suspicious_patterns:
            if pattern in v_lower:
                raise ValueError('Text contains potentially malicious content')
        
        return v
    
    @validator('ai_model')
    def validate_ai_model(cls, v):
        """Validate AI model selection"""
        allowed_models = ['openai', 'huggingface', 'local']
        if v not in allowed_models:
            raise ValueError(f'AI model must be one of: {allowed_models}')
        return v
    
    @validator('api_token')
    def validate_api_token(cls, v, values):
        """Validate API token based on selected model"""
        if v is not None:
            # Basic token format validation
            if len(v) < 10:
                raise ValueError('API token appears to be too short')
            
            # Check for suspicious tokens
            if v.startswith('sk-') and len(v) < 20:
                raise ValueError('OpenAI API token format appears invalid')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "text_blob": "Artificial intelligence has revolutionized many industries. It enables machines to learn from data and make intelligent decisions. Machine learning algorithms can process vast amounts of information quickly and accurately. This technology is being used in healthcare, finance, transportation, and many other fields to improve efficiency and outcomes.",
                "semantic_threshold": 0.8,
                "ai_model": "openai",
                "max_summary_length": 300,
                "summary_ratio": 0.4,
                "tenant_id": "tenant-123",
                "user_id": "user-456"
            }
        }

class SummarizationResponse(BaseModel):
    """Response model for text summarization results"""
    
    # Core response data
    refined_text: str = Field(
        ...,
        description="The summarized and refined text"
    )
    
    semantic_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score between original and summarized text"
    )
    
    # Request context
    request_id: str = Field(
        ...,
        description="Unique identifier for the original request"
    )
    
    # Processing metadata
    original_length: int = Field(
        ...,
        description="Length of original text in characters"
    )
    
    summary_length: int = Field(
        ...,
        description="Length of summarized text in characters"
    )
    
    compression_ratio: float = Field(
        ...,
        description="Ratio of summary length to original length"
    )
    
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds"
    )
    
    # Model and processing details
    model_used: str = Field(
        ...,
        description="AI model that was actually used for summarization"
    )
    
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts made"
    )
    
    # Quality metrics
    quality_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Additional quality metrics (coherence, fluency, etc.)"
    )
    
    # Status and warnings
    status: str = Field(
        default="success",
        description="Processing status (success, partial_success, failed)"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings generated during processing"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response creation timestamp"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "refined_text": "AI has revolutionized industries by enabling machines to learn from data and make intelligent decisions. Machine learning processes vast information quickly, improving efficiency in healthcare, finance, and transportation.",
                "semantic_score": 0.87,
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "original_length": 342,
                "summary_length": 187,
                "compression_ratio": 0.55,
                "processing_time_ms": 1250,
                "model_used": "openai",
                "retry_count": 0,
                "quality_metrics": {
                    "coherence": 0.89,
                    "fluency": 0.92,
                    "coverage": 0.85
                },
                "status": "success",
                "warnings": []
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response model"""
    
    error_code: str = Field(
        ...,
        description="Specific error code for programmatic handling"
    )
    
    error_message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID if available"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "SEMANTIC_THRESHOLD_NOT_MET",
                "error_message": "Could not achieve required semantic similarity after maximum retry attempts",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "details": {
                    "attempts_made": 3,
                    "best_score_achieved": 0.75,
                    "required_threshold": 0.8
                }
            }
        }

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    
    status: str = Field(
        ...,
        description="Service health status"
    )
    
    version: str = Field(
        ...,
        description="Service version"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of external dependencies"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        description="Service uptime in seconds"
    )

class MetricsResponse(BaseModel):
    """Service metrics response model"""
    
    total_requests: int = Field(
        default=0,
        description="Total number of summarization requests processed"
    )
    
    successful_requests: int = Field(
        default=0,
        description="Number of successful requests"
    )
    
    failed_requests: int = Field(
        default=0,
        description="Number of failed requests"
    )
    
    average_processing_time_ms: float = Field(
        default=0.0,
        description="Average processing time in milliseconds"
    )
    
    average_semantic_score: float = Field(
        default=0.0,
        description="Average semantic similarity score"
    )
    
    average_compression_ratio: float = Field(
        default=0.0,
        description="Average compression ratio"
    )
    
    models_used: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of requests by model type"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp"
    )
