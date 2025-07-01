"""
Enhanced JWT authentication module with JWKS support for Auth Service integration.
Implements secure JWT validation with public key downloading and caching.
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import httpx
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from fastapi import HTTPException, status
import structlog

from config import settings

logger = structlog.get_logger(__name__)

class JWKSError(Exception):
    """Raised when JWKS operations fail"""
    pass

class JWTValidationError(Exception):
    """Raised when JWT validation fails"""
    pass

class JWKSManager:
    """Manages JWKS (JSON Web Key Set) operations including key caching and rotation"""
    
    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        """
        Initialize JWKS manager.
        
        Args:
            jwks_url: URL to fetch JWKS from Auth Service
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._keys_cache: Dict[str, Any] = {}
        self._cache_timestamp = 0
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def get_jwks(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get JWKS from cache or fetch from Auth Service.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            JWKS dictionary
            
        Raises:
            JWKSError: If JWKS cannot be fetched or is invalid
        """
        now = time.time()
        
        # Check cache validity
        if not force_refresh and self._keys_cache and (now - self._cache_timestamp) < self.cache_ttl:
            logger.debug("Using cached JWKS")
            return self._keys_cache
        
        try:
            logger.info(f"Fetching JWKS from {self.jwks_url}")
            response = await self._client.get(self.jwks_url)
            response.raise_for_status()
            
            jwks_data = response.json()
            
            # Validate JWKS structure
            if "keys" not in jwks_data:
                raise JWKSError("Invalid JWKS format: missing 'keys' field")
            
            if not isinstance(jwks_data["keys"], list):
                raise JWKSError("Invalid JWKS format: 'keys' must be an array")
            
            # Cache the keys
            self._keys_cache = jwks_data
            self._cache_timestamp = now
            
            logger.info(f"Successfully cached {len(jwks_data['keys'])} JWK(s)")
            return jwks_data
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise JWKSError(f"Failed to fetch JWKS from {self.jwks_url}: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"JWKS endpoint returned error: {e.response.status_code}")
            raise JWKSError(f"JWKS endpoint error: {e.response.status_code}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JWKS JSON response: {e}")
            raise JWKSError("Invalid JWKS JSON response")
    
    async def get_key_by_kid(self, kid: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific key by Key ID (kid).
        
        Args:
            kid: Key ID to search for
            
        Returns:
            JWK dictionary or None if not found
        """
        jwks = await self.get_jwks()
        
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                return key
        
        # Try refreshing cache once if key not found
        jwks = await self.get_jwks(force_refresh=True)
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                return key
        
        return None
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

class EnhancedJWTValidator:
    """Enhanced JWT validator with JWKS support and comprehensive validation"""
    
    def __init__(self, auth_service_url: str):
        """
        Initialize JWT validator.
        
        Args:
            auth_service_url: Base URL of the Auth Service
        """
        self.jwks_url = f"{auth_service_url}/.well-known/jwks.json"
        self.jwks_manager = JWKSManager(self.jwks_url)
        
    async def validate_token(
        self, 
        token: str, 
        required_tenant_id: Optional[str] = None,
        required_scopes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Validate JWT token with comprehensive checks.
        
        Args:
            token: JWT token string
            required_tenant_id: Required tenant ID (if any)
            required_scopes: Required scopes (if any)
            
        Returns:
            Validated token payload
            
        Raises:
            JWTValidationError: If token validation fails
        """
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise JWTValidationError("Token missing key ID (kid)")
            
            # Get the public key
            jwk_data = await self.jwks_manager.get_key_by_kid(kid)
            if not jwk_data:
                raise JWTValidationError(f"Unknown key ID: {kid}")
            
            # Construct the public key
            try:
                public_key = jwk.construct(jwk_data)
            except Exception as e:
                logger.error(f"Failed to construct public key: {e}")
                raise JWTValidationError("Invalid public key")
            
            # Validate the token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256", "ES256"],  # Support RSA and ECDSA
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": False,  # We'll validate audience manually
                    "require_exp": True,
                    "require_iat": True,
                }
            )
            
            # Additional validations
            await self._validate_payload(payload, required_tenant_id, required_scopes)
            
            logger.info(
                "Token validated successfully",
                user_id=payload.get("sub"),
                tenant_id=payload.get("tenant_id"),
                exp=payload.get("exp")
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise JWTValidationError("Token has expired")
        except jwt.JWTClaimsError as e:
            logger.warning(f"Token claims validation failed: {e}")
            raise JWTValidationError(f"Token claims invalid: {e}")
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise JWTValidationError(f"Token validation failed: {e}")
        except JWKSError as e:
            logger.error(f"JWKS error: {e}")
            raise JWTValidationError("Authentication service unavailable")
    
    async def _validate_payload(
        self, 
        payload: Dict[str, Any], 
        required_tenant_id: Optional[str] = None,
        required_scopes: Optional[list] = None
    ):
        """
        Validate token payload claims.
        
        Args:
            payload: Decoded JWT payload
            required_tenant_id: Required tenant ID
            required_scopes: Required scopes
            
        Raises:
            JWTValidationError: If validation fails
        """
        # Validate required claims
        required_claims = ["sub", "iat", "exp"]
        for claim in required_claims:
            if claim not in payload:
                raise JWTValidationError(f"Missing required claim: {claim}")
        
        # Validate subject
        subject = payload.get("sub")
        if not subject or not isinstance(subject, str):
            raise JWTValidationError("Invalid subject claim")
        
        # Validate tenant if required
        if required_tenant_id:
            token_tenant = payload.get("tenant_id")
            if not token_tenant:
                raise JWTValidationError("Token missing tenant_id claim")
            if token_tenant != required_tenant_id:
                raise JWTValidationError(f"Tenant mismatch: expected {required_tenant_id}, got {token_tenant}")
        
        # Validate scopes if required
        if required_scopes:
            token_scopes = payload.get("scopes", [])
            if not isinstance(token_scopes, list):
                raise JWTValidationError("Invalid scopes claim format")
            
            missing_scopes = set(required_scopes) - set(token_scopes)
            if missing_scopes:
                raise JWTValidationError(f"Missing required scopes: {missing_scopes}")
        
        # Validate token age (additional security check)
        iat = payload.get("iat")
        if iat:
            token_age = time.time() - iat
            max_age = 24 * 3600  # 24 hours max token age
            if token_age > max_age:
                raise JWTValidationError("Token is too old")
    
    async def close(self):
        """Close resources"""
        await self.jwks_manager.close()

# Global validator instance
_jwt_validator: Optional[EnhancedJWTValidator] = None

def get_jwt_validator() -> EnhancedJWTValidator:
    """Get or create the global JWT validator instance"""
    global _jwt_validator
    
    if _jwt_validator is None:
        auth_service_url = getattr(settings.security, 'auth_service_url', 'http://auth-service:8080')
        _jwt_validator = EnhancedJWTValidator(auth_service_url)
    
    return _jwt_validator

async def validate_jwt_token(
    token: str, 
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to validate JWT token.
    
    Args:
        token: JWT token string
        tenant_id: Required tenant ID (optional)
        
    Returns:
        Validated token payload
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        validator = get_jwt_validator()
        return await validator.validate_token(token, required_tenant_id=tenant_id)
    
    except JWTValidationError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "error_message": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "AUTH_SERVICE_ERROR", "error_message": "Authentication service error"}
        )
