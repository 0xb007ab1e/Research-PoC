"""
FastAPI main application for the MCP Text Summarization Service.

Provides REST API endpoints with JWT authentication, rate limiting,
CORS support, and Prometheus metrics.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from jose import JWTError, jwt
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog
from opentelemetry import trace

# Import our new security modules
from auth import validate_jwt_token, get_jwt_validator
from tls_config import get_tls_config, is_tls_available, is_mutual_tls_available
from middleware import (
    HeaderValidationMiddleware, 
    SecurityHeadersMiddleware, 
    RequestLoggingMiddleware,
    JWTValidationMiddleware
)

# Import our models and pipeline
from models import (
    SummarizationRequest, 
    SummarizationResponse, 
    HealthCheckResponse,
    ErrorResponse
)
from pipeline import generate_summary, get_pipeline, SemanticThresholdError, ModelError
from config import settings
from telemetry import setup_telemetry, get_telemetry_manager, shutdown_telemetry

# Import and configure structured logging
from structured_logging import setup_structured_logging, get_logger

# Setup enhanced structured logging with OpenTelemetry integration
setup_structured_logging()
logger = get_logger(__name__)

# JWT Security
security = HTTPBearer()

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

SUMMARIZATION_COUNT = Counter(
    'summarizations_total',
    'Total number of summarization requests',
    ['model_used', 'status']
)

SUMMARIZATION_DURATION = Histogram(
    'summarization_duration_seconds',
    'Summarization processing time in seconds',
    ['model_used']
)

SEMANTIC_SCORE = Histogram(
    'semantic_similarity_score',
    'Semantic similarity scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

ACTIVE_REQUESTS = Gauge(
    'active_requests',
    'Number of active requests being processed'
)

# Application startup time for health checks
APP_START_TIME = time.time()

# Simple in-memory rate limiter (for production, use Redis)
class InMemoryRateLimiter:
    def __init__(self, calls: int = 100, period: int = 60):
        self.calls = calls
        self.period = period
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if now - req_time < self.period
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= self.calls:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True

# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(
    calls=settings.security.rate_limit_calls,
    period=settings.security.rate_limit_period
)


def get_settings():
    """Dependency injection for settings"""
    return settings


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> Dict[str, Any]:
    """
    Enhanced JWT authentication dependency using JWKS validation.
    
    Args:
        credentials: Bearer token from Authorization header
        request: FastAPI request object for context
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Get tenant ID from request state (set by middleware)
        tenant_id = getattr(request.state, 'tenant_id', None) if request else None
        
        # Validate JWT token using our enhanced validator
        payload = await validate_jwt_token(
            credentials.credentials,
            tenant_id=tenant_id
        )
        
        # Extract user information
        user_info = {
            "username": payload.get("sub"),
            "user_id": payload.get("user_id") or payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "exp": payload.get("exp"),
            "scopes": payload.get("scopes", []),
            "iat": payload.get("iat"),
            "iss": payload.get("iss")
        }
        
        logger.debug(
            "User authenticated successfully",
            user_id=user_info["user_id"],
            tenant_id=user_info["tenant_id"],
            scopes=user_info["scopes"]
        )
        
        return user_info
        
    except HTTPException:
        # Re-raise HTTP exceptions from validate_jwt_token
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "AUTH_ERROR", "error_message": "Authentication service error"}
        )


async def rate_limit_check(request: Request):
    """
    Rate limiting middleware function.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Use client IP as rate limit key
    client_ip = request.client.host
    
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting MCP Text Summarization Service")
    logger.info(f"Environment: {settings.service.environment}")
    logger.info(f"Debug mode: {settings.service.debug}")
    
    # Initialize OpenTelemetry
    telemetry_manager = setup_telemetry()
    if telemetry_manager:
        # Instrument the FastAPI app
        telemetry_manager.instrument_fastapi_app(app)
        logger.info("OpenTelemetry instrumentation enabled")
    else:
        logger.warning("OpenTelemetry setup failed, continuing without telemetry")
    
    # Initialize the pipeline to preload models
    try:
        pipeline = get_pipeline()
        logger.info("Pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        # Don't fail startup, let endpoints handle the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Text Summarization Service")
    
    # Shutdown telemetry
    shutdown_telemetry()


# Create FastAPI application
app = FastAPI(
    title="MCP Text Summarization Service",
    description="AI-powered text summarization with semantic validation",
    version=settings.service.service_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.service.debug else None,
    redoc_url="/redoc" if settings.service.debug else None
)

# Add security middleware (order matters - add from outermost to innermost)
app.add_middleware(
    SecurityHeadersMiddleware
)

app.add_middleware(
    RequestLoggingMiddleware
)

app.add_middleware(
    JWTValidationMiddleware,
    enable_validation=True
)

app.add_middleware(
    HeaderValidationMiddleware,
    require_tenant_id=settings.security.require_tenant_id,
    require_request_id=settings.security.require_request_id,
    auto_generate_request_id=settings.security.auto_generate_request_id
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.security.allowed_methods,
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect Prometheus and OpenTelemetry metrics"""
    start_time = time.time()
    
    # Track active requests
    ACTIVE_REQUESTS.inc()
    
    # Get telemetry manager for OTel metrics
    telemetry_manager = get_telemetry_manager()
    if telemetry_manager:
        telemetry_manager.record_active_requests(increment=True)
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        # Prometheus metrics
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        # OpenTelemetry metrics
        if telemetry_manager:
            telemetry_manager.record_request_metrics(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
        
        return response
        
    finally:
        ACTIVE_REQUESTS.dec()
        if telemetry_manager:
            telemetry_manager.record_active_requests(increment=False)


@app.post(
    "/v1/summarize",
    response_model=SummarizationResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Generate text summary",
    description="Generate an AI-powered summary of the provided text with semantic validation"
)
async def summarize_text(
    request: SummarizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rate_limit: None = Depends(rate_limit_check),
    http_request: Request = None
) -> SummarizationResponse:
    """
    Generate a summary of the provided text.
    
    The endpoint uses AI models to generate summaries and validates them
    against semantic similarity thresholds to ensure quality.
    """
    start_time = time.time()
    
    # Add user context to request if not provided
    if not request.user_id and current_user.get("user_id"):
        request.user_id = current_user["user_id"]
    if not request.tenant_id and current_user.get("tenant_id"):
        request.tenant_id = current_user["tenant_id"]
    
    logger.info(
        f"Summarization request received",
        request_id=request.request_id,
        user_id=request.user_id,
        model=request.ai_model,
        text_length=len(request.text_blob)
    )
    
    try:
        # Generate summary using pipeline
        response = await generate_summary(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        # Prometheus metrics
        SUMMARIZATION_DURATION.labels(model_used=response.model_used).observe(duration)
        SUMMARIZATION_COUNT.labels(model_used=response.model_used, status="success").inc()
        SEMANTIC_SCORE.observe(response.semantic_score)
        
        # OpenTelemetry metrics
        telemetry_manager = get_telemetry_manager()
        if telemetry_manager:
            telemetry_manager.record_summarization_metrics(
                model=response.model_used,
                status="success",
                duration=duration,
                semantic_score=response.semantic_score
            )
        
        logger.info(
            f"Summarization completed successfully",
            request_id=request.request_id,
            semantic_score=response.semantic_score,
            model_used=response.model_used,
            processing_time_ms=response.processing_time_ms
        )
        
        return response
        
    except SemanticThresholdError as e:
        logger.warning(f"Semantic threshold not met: {e}", request_id=request.request_id)
        SUMMARIZATION_COUNT.labels(model_used=request.ai_model, status="threshold_failed").inc()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "SEMANTIC_THRESHOLD_NOT_MET",
                "error_message": str(e),
                "request_id": request.request_id
            }
        )
        
    except ModelError as e:
        logger.error(f"Model error: {e}", request_id=request.request_id)
        SUMMARIZATION_COUNT.labels(model_used=request.ai_model, status="model_failed").inc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "MODEL_ERROR",
                "error_message": "AI model processing failed",
                "request_id": request.request_id
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", request_id=request.request_id)
        SUMMARIZATION_COUNT.labels(model_used=request.ai_model, status="error").inc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Internal server error occurred",
                "request_id": request.request_id
            }
        )


@app.get(
    "/healthz",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check the health status of the service and its dependencies"
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Returns the current health status of the service including
    uptime and dependency status.
    """
    uptime_seconds = int(time.time() - APP_START_TIME)
    
    # Check dependencies
    dependencies = {}
    
    try:
        # Check if pipeline is initialized
        pipeline = get_pipeline()
        dependencies["pipeline"] = "healthy"
        
        # Check if sentence transformer is loaded
        if pipeline.sentence_transformer:
            dependencies["sentence_transformer"] = "healthy"
        else:
            dependencies["sentence_transformer"] = "not_loaded"
            
        # Check local model
        if pipeline.local_model:
            dependencies["local_model"] = "healthy"
        else:
            dependencies["local_model"] = "not_loaded"
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        dependencies["pipeline"] = f"error: {str(e)}"
    
    # Determine overall status
    has_errors = any("error" in status for status in dependencies.values())
    overall_status = "unhealthy" if has_errors else "healthy"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.service.service_version,
        dependencies=dependencies,
        uptime_seconds=uptime_seconds
    )


@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Export Prometheus metrics for monitoring and alerting"
)
async def get_metrics() -> str:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for scraping by monitoring systems.
    """
    return generate_latest()


@app.get(
    "/",
    summary="Service information",
    description="Get basic information about the service"
)
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.service.service_name,
        "version": settings.service.service_version,
        "environment": settings.service.environment,
        "status": "running",
        "docs_url": "/docs" if settings.service.debug else "disabled",
        "health_check": "/healthz",
        "metrics": "/metrics"
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        path=request.url.path,
        method=request.method
    )
    
    return {
        "error_code": f"HTTP_{exc.status_code}",
        "error_message": exc.detail,
        "timestamp": datetime.utcnow().isoformat(),
        "path": str(request.url.path)
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {exc}",
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    # Configure TLS if enabled
    ssl_keyfile = None
    ssl_certfile = None
    ssl_ca_certs = None
    
    if settings.security.enable_tls and is_tls_available():
        tls_config = get_tls_config()
        ssl_context = tls_config.create_ssl_context(
            client_auth=settings.security.enable_mutual_tls
        )
        
        if ssl_context:
            ssl_keyfile = str(tls_config.server_key_path)
            ssl_certfile = str(tls_config.server_cert_path)
            if settings.security.enable_mutual_tls and tls_config.ca_cert_path.exists():
                ssl_ca_certs = str(tls_config.ca_cert_path)
            
            logger.info(
                "TLS enabled",
                mutual_tls=settings.security.enable_mutual_tls,
                cert_file=ssl_certfile,
                key_file=ssl_keyfile,
                ca_file=ssl_ca_certs
            )
        else:
            logger.warning("TLS requested but certificates not available, running without TLS")
    else:
        logger.info("Running without TLS encryption")
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service.host,
        port=settings.service.port,
        reload=settings.service.debug,
        log_level=settings.service.log_level.lower(),
        access_log=True,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        ssl_ca_certs=ssl_ca_certs
    )
