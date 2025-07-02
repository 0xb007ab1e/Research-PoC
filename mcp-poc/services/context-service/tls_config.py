"""
TLS configuration module for mutual TLS support.
Handles SSL certificate loading and validation from /etc/certs.
"""

import os
import ssl
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger(__name__)

class TLSConfig:
    """TLS configuration manager for mutual TLS"""
    
    def __init__(self, certs_dir: str = "/etc/certs"):
        """
        Initialize TLS configuration.
        
        Args:
            certs_dir: Directory containing TLS certificates
        """
        self.certs_dir = Path(certs_dir)
        self.server_cert_path = self.certs_dir / "server.crt"
        self.server_key_path = self.certs_dir / "server.key"
        self.ca_cert_path = self.certs_dir / "ca.crt"
        self.client_cert_path = self.certs_dir / "client.crt"
        self.client_key_path = self.certs_dir / "client.key"
        
        logger.info(f"TLS configuration initialized with certs directory: {certs_dir}")
    
    def validate_certificates(self) -> Dict[str, bool]:
        """
        Validate existence and readability of certificate files.
        
        Returns:
            Dictionary with validation status for each certificate
        """
        validation_results = {}
        
        cert_files = {
            "server_cert": self.server_cert_path,
            "server_key": self.server_key_path,
            "ca_cert": self.ca_cert_path,
            "client_cert": self.client_cert_path,
            "client_key": self.client_key_path
        }
        
        for cert_name, cert_path in cert_files.items():
            try:
                if cert_path.exists() and cert_path.is_file():
                    # Check if file is readable
                    with open(cert_path, 'r') as f:
                        content = f.read(10)  # Read first 10 chars to verify readability
                    validation_results[cert_name] = True
                    logger.debug(f"Certificate {cert_name} validated: {cert_path}")
                else:
                    validation_results[cert_name] = False
                    logger.warning(f"Certificate {cert_name} not found: {cert_path}")
            except Exception as e:
                validation_results[cert_name] = False
                logger.error(f"Error validating certificate {cert_name}: {e}")
        
        return validation_results
    
    def create_ssl_context(self, client_auth: bool = True) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for the server with mutual TLS support.
        
        Args:
            client_auth: Whether to require client authentication
            
        Returns:
            SSL context or None if certificates are not available
        """
        try:
            # Validate certificates first
            validation_results = self.validate_certificates()
            
            # Check minimum required certificates for server
            if not validation_results.get("server_cert") or not validation_results.get("server_key"):
                logger.error("Server certificate or key not available")
                return None
            
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # Configure server certificate and key
            context.load_cert_chain(
                certfile=str(self.server_cert_path),
                keyfile=str(self.server_key_path)
            )
            
            # Configure mutual TLS if client authentication is required
            if client_auth:
                if validation_results.get("ca_cert"):
                    context.load_verify_locations(cafile=str(self.ca_cert_path))
                    context.verify_mode = ssl.CERT_REQUIRED
                    logger.info("Mutual TLS enabled with client certificate verification")
                else:
                    logger.warning("CA certificate not available, disabling client auth")
                    context.verify_mode = ssl.CERT_NONE
            else:
                context.verify_mode = ssl.CERT_NONE
            
            # Security settings
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_SINGLE_DH_USE
            context.options |= ssl.OP_SINGLE_ECDH_USE
            
            logger.info("SSL context created successfully")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            return None
    
    def create_client_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for outbound connections with client certificates.
        
        Returns:
            SSL context for client connections or None if certificates are not available
        """
        try:
            validation_results = self.validate_certificates()
            
            # Create client SSL context
            context = ssl.create_default_context()
            
            # Load CA certificate for server verification
            if validation_results.get("ca_cert"):
                context.load_verify_locations(cafile=str(self.ca_cert_path))
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = True
            else:
                logger.warning("CA certificate not available for client context")
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            # Load client certificate if available
            if validation_results.get("client_cert") and validation_results.get("client_key"):
                context.load_cert_chain(
                    certfile=str(self.client_cert_path),
                    keyfile=str(self.client_key_path)
                )
                logger.info("Client SSL context created with client certificate")
            else:
                logger.info("Client SSL context created without client certificate")
            
            # Security settings
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create client SSL context: {e}")
            return None
    
    def get_tls_status(self) -> Dict[str, Any]:
        """
        Get current TLS configuration status.
        
        Returns:
            Dictionary with TLS status information
        """
        validation_results = self.validate_certificates()
        
        status = {
            "certificates_directory": str(self.certs_dir),
            "certificates": validation_results,
            "server_tls_available": validation_results.get("server_cert", False) and validation_results.get("server_key", False),
            "mutual_tls_available": validation_results.get("ca_cert", False),
            "client_tls_available": validation_results.get("client_cert", False) and validation_results.get("client_key", False)
        }
        
        return status

# Global TLS configuration instance
_tls_config: Optional[TLSConfig] = None

def get_tls_config() -> TLSConfig:
    """Get or create the global TLS configuration instance"""
    global _tls_config
    
    if _tls_config is None:
        _tls_config = TLSConfig()
    
    return _tls_config

def is_tls_available() -> bool:
    """Check if TLS is properly configured"""
    tls_config = get_tls_config()
    status = tls_config.get_tls_status()
    return status["server_tls_available"]

def is_mutual_tls_available() -> bool:
    """Check if mutual TLS is properly configured"""
    tls_config = get_tls_config()
    status = tls_config.get_tls_status()
    return status["mutual_tls_available"]
