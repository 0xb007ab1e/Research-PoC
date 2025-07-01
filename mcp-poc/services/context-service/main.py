"""
FastAPI main application for the MCP Context Service.

Provides REST API endpoints with security and observability patterns.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog
from opentelemetry import trace

# Import our security modules
from auth import validate_jwt_token, get_jwt_validator
from tls_config import get_tls_config, is_tls_available, is_mutual_tls_available
from middleware import (
    HeaderValidationMiddleware, 
    SecurityHeadersMiddleware, 
    RequestLoggingMiddleware,
    JWTValidationMiddleware
)

# Import the repository and models
from models import ContextCreateRequest, ContextUpdateRequest, ContextResponse, HealthCheckResponse, ErrorResponse
from repository import ContextRepository, DatabaseError
from config import settings
from telemetry import setup_telemetry, get_telemetry_manager, shutdown_telemetry

# Setup structured logging
from structured_logging import setup_structured_logging, get_logger

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

CONTEXT_COUNT = Counter(
    'contexts_total',
    'Total number of context operations',
    ['operation', 'status']
)

CONTEXT_DURATION = Histogram(
    'context_operation_duration_seconds',
    'Context operation processing time in seconds',
    ['operation']
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


def get_tenant_id_from_request(request: Request) -> str:
    """
    Extract tenant ID from request state (set by middleware)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tenant ID string
        
    Raises:
        HTTPException: If tenant ID is not available
    """
    tenant_id = getattr(request.state, 'tenant_id', None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "MISSING_TENANT_ID", "error_message": "Tenant ID is required"}
        )
    return tenant_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting MCP Context Service")
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
    
    # Test database connection
    try:
        test_repo = ContextRepository()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        # Don't fail startup, let endpoints handle the error
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Context Service")
    
    # Shutdown telemetry
    shutdown_telemetry()


# Create repository instance
context_repo = ContextRepository()

# Create FastAPI application
app = FastAPI(
    title="MCP Context Service",
    description="Service for managing context data with tenant awareness",
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
    """Middleware to collect Prometheus metrics"""
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response


@app.post(
    "/context",
    response_model=ContextResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Create context data",
    description="Create context data with tenant-scoped data storage"
)
async def create_context(
    request: ContextCreateRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rate_limit: None = Depends(rate_limit_check)
) -> ContextResponse:
    """Create a new context entry"""
    start_time = time.time()
    
    # Extract tenant ID from request state (set by middleware)
    tenant_id = get_tenant_id_from_request(http_request)
    
    # Add user context to request if not provided
    if not request.user_id and current_user.get("user_id"):
        request.user_id = current_user["user_id"]
    if not request.tenant_id and current_user.get("tenant_id"):
        request.tenant_id = current_user["tenant_id"]
    
    logger.info(
        "Context creation request received",
        request_id=request.request_id,
        user_id=request.user_id,
        tenant_id=tenant_id,
        context_type=request.context_type
    )
    
    try:
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Create context
        context_id = await context_repo.create_context(tenant_id, request.dict())
        context_data = await context_repo.get_context(tenant_id, context_id)
        
        if not context_data:
            CONTEXT_COUNT.labels(operation="create", status="failed").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "CONTEXT_CREATION_FAILED",
                    "error_message": "Context creation failed",
                    "request_id": request.request_id
                }
            )
        
        # Record success metrics
        duration = time.time() - start_time
        CONTEXT_DURATION.labels(operation="create").observe(duration)
        CONTEXT_COUNT.labels(operation="create", status="success").inc()
        
        logger.info(
            "Context created successfully",
            request_id=request.request_id,
            context_id=context_id,
            processing_time_ms=round(duration * 1000, 2)
        )
        
        return ContextResponse(**context_data)
        
    except DatabaseError as e:
        CONTEXT_COUNT.labels(operation="create", status="db_error").inc()
        logger.error(f"Database error creating context: {e}", request_id=request.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "DATABASE_ERROR",
                "error_message": "Database operation failed",
                "request_id": request.request_id
            }
        )
    except Exception as e:
        CONTEXT_COUNT.labels(operation="create", status="error").inc()
        logger.error(f"Unexpected error creating context: {e}", request_id=request.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Internal server error occurred",
                "request_id": request.request_id
            }
        )
    finally:
        ACTIVE_REQUESTS.dec()


@app.get(
    "/context/{id}",
    response_model=ContextResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Get context data",
    description="Retrieve context data by ID"
)
async def get_context(
    id: str,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rate_limit: None = Depends(rate_limit_check)
) -> ContextResponse:
    """Retrieve the context by ID"""
    start_time = time.time()
    
    # Extract tenant ID from request state (set by middleware)
    tenant_id = get_tenant_id_from_request(http_request)
    
    logger.info(
        "Context retrieval request received",
        context_id=id,
        user_id=current_user.get("user_id"),
        tenant_id=tenant_id
    )
    
    try:
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        context_data = await context_repo.get_context(tenant_id, id)
        
        if not context_data:
            CONTEXT_COUNT.labels(operation="get", status="not_found").inc()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "CONTEXT_NOT_FOUND",
                    "error_message": "Context not found or expired",
                    "context_id": id
                }
            )
        
        # Record success metrics
        duration = time.time() - start_time
        CONTEXT_DURATION.labels(operation="get").observe(duration)
        CONTEXT_COUNT.labels(operation="get", status="success").inc()
        
        logger.info(
            "Context retrieved successfully",
            context_id=id,
            processing_time_ms=round(duration * 1000, 2)
        )
        
        return ContextResponse(**context_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except DatabaseError as e:
        CONTEXT_COUNT.labels(operation="get", status="db_error").inc()
        logger.error(f"Database error retrieving context {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "DATABASE_ERROR",
                "error_message": "Database operation failed",
                "context_id": id
            }
        )
    except Exception as e:
        CONTEXT_COUNT.labels(operation="get", status="error").inc()
        logger.error(f"Unexpected error retrieving context {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Internal server error occurred",
                "context_id": id
            }
        )
    finally:
        ACTIVE_REQUESTS.dec()


@app.put(
    "/context/{id}",
    response_model=ContextResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Update context data",
    description="Update context data by ID"
)
async def update_context(
    id: str,
    request: ContextUpdateRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rate_limit: None = Depends(rate_limit_check)
) -> ContextResponse:
    """Update the context by ID"""
    start_time = time.time()
    
    # Extract tenant ID from request state (set by middleware)
    tenant_id = get_tenant_id_from_request(http_request)
    
    logger.info(
        "Context update request received",
        request_id=request.request_id,
        context_id=id,
        user_id=current_user.get("user_id"),
        tenant_id=tenant_id
    )
    
    try:
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        update_success = await context_repo.update_context(tenant_id, id, request.dict(exclude_unset=True))
        
        if not update_success:
            CONTEXT_COUNT.labels(operation="update", status="not_found").inc()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "CONTEXT_NOT_FOUND",
                    "error_message": "Context not found or expired",
                    "context_id": id,
                    "request_id": request.request_id
                }
            )
        
        # Get updated context
        context_data = await context_repo.get_context(tenant_id, id)
        if not context_data:
            CONTEXT_COUNT.labels(operation="update", status="retrieval_failed").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "CONTEXT_RETRIEVAL_FAILED",
                    "error_message": "Failed to retrieve updated context",
                    "context_id": id,
                    "request_id": request.request_id
                }
            )
        
        # Record success metrics
        duration = time.time() - start_time
        CONTEXT_DURATION.labels(operation="update").observe(duration)
        CONTEXT_COUNT.labels(operation="update", status="success").inc()
        
        logger.info(
            "Context updated successfully",
            request_id=request.request_id,
            context_id=id,
            processing_time_ms=round(duration * 1000, 2)
        )
        
        return ContextResponse(**context_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except DatabaseError as e:
        CONTEXT_COUNT.labels(operation="update", status="db_error").inc()
        logger.error(f"Database error updating context {id}: {e}", request_id=request.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "DATABASE_ERROR",
                "error_message": "Database operation failed",
                "context_id": id,
                "request_id": request.request_id
            }
        )
    except Exception as e:
        CONTEXT_COUNT.labels(operation="update", status="error").inc()
        logger.error(f"Unexpected error updating context {id}: {e}", request_id=request.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "Internal server error occurred",
                "context_id": id,
                "request_id": request.request_id
            }
        )
    finally:
        ACTIVE_REQUESTS.dec()


@app.get(
    "/healthz",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check the health status of the service and its dependencies"
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint with comprehensive dependency checks."""
    uptime_seconds = int(time.time() - APP_START_TIME)
    
    # Check dependencies
    dependencies = {}
    
    try:
        # Check database connection
        test_repo = ContextRepository()
        # Try to connect to a test tenant (this will test the connection)
        async with test_repo.db.get_connection("health_check") as conn:
            await conn.fetchval("SELECT 1")
        dependencies["database"] = "healthy"
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        dependencies["database"] = f"error: {str(e)}"
    
    # Check OpenTelemetry status
    telemetry_manager = get_telemetry_manager()
    if telemetry_manager:
        dependencies["telemetry"] = "enabled"
    else:
        dependencies["telemetry"] = "disabled"
    
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
    """Prometheus metrics endpoint."""
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

