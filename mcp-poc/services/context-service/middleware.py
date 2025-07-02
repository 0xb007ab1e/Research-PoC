"""
Middleware for header validation and propagation.
Ensures X-Tenant-ID and X-Request-ID headers are properly handled.
"""

import uuid
import time
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

# Import our auth module
from auth import validate_jwt_token, JWTValidationError

logger = structlog.get_logger(__name__)

class HeaderValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate and propagate required headers:
    - X-Tenant-ID: Validates tenant context
    - X-Request-ID: Ensures request traceability
    """
    
    def __init__(
        self,
        app,
        require_tenant_id: bool = True,
        require_request_id: bool = True,
        auto_generate_request_id: bool = True
    ):
        """
        Initialize header validation middleware.
        
        Args:
            app: FastAPI application
            require_tenant_id: Whether X-Tenant-ID header is required
            require_request_id: Whether X-Request-ID header is required
            auto_generate_request_id: Whether to auto-generate X-Request-ID if missing
        """
        super().__init__(app)
        self.require_tenant_id = require_tenant_id
        self.require_request_id = require_request_id
        self.auto_generate_request_id = auto_generate_request_id
        
        # Paths that don't require header validation
        self.exempt_paths = {
            "/healthz",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate/propagate headers.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response with proper headers
        """
        start_time = time.time()
        
        # Skip validation for exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return response
        
        # Validate and process headers
        try:
            tenant_id = await self._validate_tenant_id(request)
            request_id = await self._validate_request_id(request)
            
            # Store headers in request state for use by endpoints
            request.state.tenant_id = tenant_id
            request.state.request_id = request_id
            
            # Add structured logging context
            logger.bind(
                tenant_id=tenant_id,
                request_id=request_id,
                path=request.url.path,
                method=request.method
            )
            
            logger.info(
                "Request processed",
                tenant_id=tenant_id,
                request_id=request_id,
                user_agent=request.headers.get("user-agent"),
                client_ip=request.client.host if request.client else None
            )
            
        except HTTPException as e:
            # Log validation failure
            logger.warning(
                "Header validation failed",
                path=request.url.path,
                method=request.method,
                error=e.detail
            )
            raise e
        
        # Process request
        response = await call_next(request)
        
        # Add response headers for traceability
        response.headers["X-Request-ID"] = request_id
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        
        # Add processing time header
        processing_time = time.time() - start_time
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
        
        return response
    
    async def _validate_tenant_id(self, request: Request) -> Optional[str]:
        """
        Validate X-Tenant-ID header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tenant ID string or None
            
        Raises:
            HTTPException: If validation fails
        """
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if self.require_tenant_id and not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "MISSING_TENANT_ID",
                    "error_message": "X-Tenant-ID header is required"
                }
            )
        
        if tenant_id:
            # Validate tenant ID format
            if not self._is_valid_tenant_id(tenant_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "INVALID_TENANT_ID",
                        "error_message": "X-Tenant-ID header has invalid format"
                    }
                )
        
        return tenant_id
    
    async def _validate_request_id(self, request: Request) -> str:
        """
        Validate or generate X-Request-ID header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Request ID string
            
        Raises:
            HTTPException: If validation fails
        """
        request_id = request.headers.get("X-Request-ID")
        
        if not request_id:
            if self.auto_generate_request_id:
                request_id = str(uuid.uuid4())
                logger.debug(f"Generated request ID: {request_id}")
            elif self.require_request_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "MISSING_REQUEST_ID",
                        "error_message": "X-Request-ID header is required"
                    }
                )
        
        if request_id and not self._is_valid_request_id(request_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_REQUEST_ID",
                    "error_message": "X-Request-ID header has invalid format"
                }
            )
        
        return request_id
    
    def _is_valid_tenant_id(self, tenant_id: str) -> bool:
        """
        Validate tenant ID format.
        
        Args:
            tenant_id: Tenant ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules for tenant ID
        if not tenant_id or len(tenant_id) < 3 or len(tenant_id) > 64:
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in '-_' for c in tenant_id):
            return False
        
        # Don't allow tenant IDs that look like system paths
        invalid_patterns = ['..', '//', '\\\\', 'admin', 'system', 'root']
        tenant_lower = tenant_id.lower()
        if any(pattern in tenant_lower for pattern in invalid_patterns):
            return False
        
        return True
    
    def _is_valid_request_id(self, request_id: str) -> bool:
        """
        Validate request ID format.
        
        Args:
            request_id: Request ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation for request ID
        if not request_id or len(request_id) < 8 or len(request_id) > 128:
            return False
        
        # Check if it's a valid UUID (preferred format)
        try:
            uuid.UUID(request_id)
            return True
        except ValueError:
            pass
        
        # Allow alphanumeric with hyphens (for other ID formats)
        if all(c.isalnum() or c == '-' for c in request_id):
            return True
        
        return False

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Default security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';",
            "X-Permitted-Cross-Domain-Policies": "none"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging middleware with security context.
    """
    
    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
        
        # Sensitive headers to mask in logs
        self.sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "x-auth-token"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request details with security context.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response
        """
        start_time = time.time()
        
        # Prepare request log data
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "headers": self._mask_sensitive_headers(dict(request.headers))
        }
        
        # Add tenant and request ID if available
        if hasattr(request.state, "tenant_id"):
            request_data["tenant_id"] = request.state.tenant_id
        if hasattr(request.state, "request_id"):
            request_data["request_id"] = request.state.request_id
        
        logger.info("Request started", **request_data)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            processing_time = time.time() - start_time
            logger.info(
                "Request completed",
                request_id=getattr(request.state, "request_id", None),
                status_code=response.status_code,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=getattr(request.state, "request_id", None),
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2),
                exc_info=True
            )
            raise
    
    def _mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Mask sensitive header values for logging.
        
        Args:
            headers: Dictionary of headers
            
        Returns:
            Headers with sensitive values masked
        """
        masked_headers = {}
        
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                masked_headers[key] = "***MASKED***"
            else:
                masked_headers[key] = value
        
        return masked_headers

class JWTValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens and enforce tenant ID consistency.
    
    This middleware:
    1. Validates JWT tokens using JWKS from auth service
    2. Enforces that X-Tenant-ID header matches tenant_id claim in JWT
    3. Caches JWKS for performance (10 minute default TTL)
    """
    
    def __init__(self, app, enable_validation: bool = True):
        super().__init__(app)
        self.enable_validation = enable_validation
        
        # Paths that don't require JWT validation
        self.exempt_paths = {
            "/healthz",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate JWT token and enforce tenant consistency.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response
            
        Raises:
            HTTPException: If JWT validation fails or tenant mismatch
        """
        # Skip validation for exempt paths or if disabled
        if not self.enable_validation or request.url.path in self.exempt_paths:
            return await call_next(request)
        
        try:
            # Extract JWT token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": "MISSING_AUTHORIZATION",
                        "error_message": "Authorization header is required"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() != "bearer" or not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": "INVALID_AUTHORIZATION",
                        "error_message": "Invalid Authorization header format. Expected 'Bearer <token>'"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Get tenant ID from request state (set by HeaderValidationMiddleware)
            tenant_id = getattr(request.state, 'tenant_id', None)
            
            # Validate JWT token with tenant enforcement
            try:
                payload = await validate_jwt_token(token, tenant_id=tenant_id)
                
                # Store JWT payload in request state for use by endpoints
                request.state.jwt_payload = payload
                request.state.user_id = payload.get("sub")
                
                logger.info(
                    "JWT validation successful",
                    request_id=getattr(request.state, "request_id", None),
                    user_id=payload.get("sub"),
                    tenant_id=payload.get("tenant_id"),
                    scopes=payload.get("scopes", [])
                )
                
            except JWTValidationError as e:
                logger.warning(
                    "JWT validation failed",
                    request_id=getattr(request.state, "request_id", None),
                    error=str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": "INVALID_TOKEN",
                        "error_message": str(e)
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Additional tenant ID consistency check
            if tenant_id:
                jwt_tenant_id = payload.get("tenant_id")
                if jwt_tenant_id and jwt_tenant_id != tenant_id:
                    logger.warning(
                        "Tenant ID mismatch",
                        request_id=getattr(request.state, "request_id", None),
                        header_tenant_id=tenant_id,
                        jwt_tenant_id=jwt_tenant_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error_code": "TENANT_MISMATCH",
                            "error_message": "X-Tenant-ID header does not match JWT tenant_id claim"
                        }
                    )
        
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(
                "Unexpected JWT validation error",
                request_id=getattr(request.state, "request_id", None),
                error=str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "AUTH_SERVICE_ERROR",
                    "error_message": "Authentication service error"
                }
            )
        
        return await call_next(request)
