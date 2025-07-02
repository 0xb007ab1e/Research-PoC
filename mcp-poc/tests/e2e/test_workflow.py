#!/usr/bin/env python3
"""
End-to-end workflow validation test.

This test validates the complete MCP workflow by:
1. Starting the stack with docker-compose.dev.yml
2. Obtaining auth code and token from auth-service (bypassing browser)
3. Creating context data via context-service (with JWT + tenant header)
4. Summarizing text via text-summarization service
5. Exiting with non-zero on any failure

Usage:
    python test_workflow.py
    pytest tests/e2e/test_workflow.py
"""

import os
import sys
import time
import json
import uuid
import subprocess
import requests
import base64
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Dict, Any, Optional
from pathlib import Path
import ssl

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
COMPOSE_FILE = "docker-compose.dev.yml"
STARTUP_TIMEOUT = 180  # 3 minutes for all services to be healthy
HEALTH_CHECK_INTERVAL = 5
TEST_TENANT_ID = "test-tenant-e2e"
TEST_USER_ID = "test-user-e2e"
TEST_CLIENT_ID = "demo-client"
TEST_REDIRECT_URI = "http://localhost:3000/callback"

# Service URLs (from docker-compose.dev.yml)
SERVICES = {
    "auth-service": "https://localhost:8443",
    "context-service": "https://localhost:8001", 
    "text-summarization": "https://localhost:8000"
}

# Certificate paths for mTLS
CERT_BASE_PATH = project_root / "certs" / "docker"
CA_CERT_PATH = CERT_BASE_PATH / "auth-service" / "ca-cert.pem"
CLIENT_CERT_PATH = CERT_BASE_PATH / "auth-service" / "server-cert.pem"
CLIENT_KEY_PATH = CERT_BASE_PATH / "auth-service" / "server-key.pem"


class E2ETestError(Exception):
    """Custom exception for E2E test failures."""
    pass


class WorkflowTester:
    """End-to-end workflow tester."""
    
    def __init__(self):
        self.compose_process = None
        self.access_token = None
        self.context_id = None
        self.session = requests.Session()
        
        # Setup SSL context for mTLS
        self._setup_ssl_session()
    
    def _setup_ssl_session(self):
        """Configure the requests session for mTLS communication."""
        try:
            # Verify certificate files exist
            cert_files = [CA_CERT_PATH, CLIENT_CERT_PATH, CLIENT_KEY_PATH]
            for cert_file in cert_files:
                if not cert_file.exists():
                    raise E2ETestError(f"Certificate file not found: {cert_file}")
            
            # Configure session with client certificates
            self.session.cert = (str(CLIENT_CERT_PATH), str(CLIENT_KEY_PATH))
            self.session.verify = str(CA_CERT_PATH)
            
            print(f"✓ SSL/mTLS session configured successfully")
            
        except Exception as e:
            raise E2ETestError(f"Failed to setup SSL session: {e}")
    
    def start_stack(self):
        """Start the development stack using docker-compose."""
        print("🚀 Starting development stack...")
        
        try:
            # Check if docker-compose file exists
            compose_path = project_root / COMPOSE_FILE
            if not compose_path.exists():
                raise E2ETestError(f"Docker compose file not found: {compose_path}")
            
            # Start the stack
            cmd = ["docker-compose", "-f", str(compose_path), "up", "-d"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if result.returncode != 0:
                raise E2ETestError(f"Failed to start stack: {result.stderr}")
            
            print(f"✓ Stack started successfully")
            print("⏳ Waiting for services to be healthy...")
            
            # Wait for services to be healthy
            self._wait_for_services_healthy()
            
        except subprocess.CalledProcessError as e:
            raise E2ETestError(f"Docker compose failed: {e}")
        except Exception as e:
            raise E2ETestError(f"Failed to start stack: {e}")
    
    def _wait_for_services_healthy(self):
        """Wait for all services to pass health checks."""
        start_time = time.time()
        
        while time.time() - start_time < STARTUP_TIMEOUT:
            all_healthy = True
            
            for service_name, base_url in SERVICES.items():
                if not self._check_service_health(service_name, base_url):
                    all_healthy = False
                    break
            
            if all_healthy:
                print("✓ All services are healthy")
                return
            
            time.sleep(HEALTH_CHECK_INTERVAL)
        
        raise E2ETestError(f"Services failed to become healthy within {STARTUP_TIMEOUT} seconds")
    
    def _check_service_health(self, service_name: str, base_url: str) -> bool:
        """Check if a service is healthy."""
        try:
            # Different health endpoints for different services
            health_endpoints = {
                "auth-service": "/health",
                "context-service": "/healthz",
                "text-summarization": "/healthz"
            }
            
            endpoint = health_endpoints.get(service_name, "/health")
            health_url = f"{base_url}{endpoint}"
            
            response = self.session.get(health_url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "").lower()
                if status in ["healthy", "ok"]:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def obtain_auth_token(self):
        """Obtain auth code and token from auth-service (bypassing browser)."""
        print("🔐 Obtaining authentication token...")
        
        try:
            # Step 1: Get authorization code
            auth_code = self._get_authorization_code()
            
            # Step 2: Exchange code for access token
            self.access_token = self._exchange_code_for_token(auth_code)
            
            print("✓ Authentication token obtained successfully")
            
        except Exception as e:
            raise E2ETestError(f"Failed to obtain auth token: {e}")
    
    def _get_authorization_code(self) -> str:
        """Get authorization code by calling the auth service directly."""
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            code_verifier.encode('utf-8')
        ).decode('utf-8').rstrip('=')
        
        # Store code_verifier for token exchange
        self.code_verifier = code_verifier
        
        # Prepare authorization request
        auth_params = {
            "response_type": "code",
            "client_id": TEST_CLIENT_ID,
            "redirect_uri": TEST_REDIRECT_URI,
            "scope": "read write",
            "state": str(uuid.uuid4()),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "nonce": str(uuid.uuid4())
        }
        
        auth_url = f"{SERVICES['auth-service']}/authorize?{urlencode(auth_params)}"
        
        # Make authorization request
        response = self.session.get(auth_url, allow_redirects=False, timeout=30)
        
        if response.status_code != 302:
            raise E2ETestError(f"Expected redirect (302), got {response.status_code}: {response.text}")
        
        # Extract authorization code from redirect location
        location = response.headers.get('Location')
        if not location:
            raise E2ETestError("No redirect location in authorization response")
        
        parsed_url = urlparse(location)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' not in query_params:
            error = query_params.get('error', ['unknown'])[0]
            error_desc = query_params.get('error_description', [''])[0]
            raise E2ETestError(f"Authorization failed: {error} - {error_desc}")
        
        auth_code = query_params['code'][0]
        print(f"✓ Authorization code obtained: {auth_code[:10]}...")
        
        return auth_code
    
    def _exchange_code_for_token(self, auth_code: str) -> str:
        """Exchange authorization code for access token."""
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": TEST_REDIRECT_URI,
            "client_id": TEST_CLIENT_ID,
            "code_verifier": self.code_verifier
        }
        
        token_url = f"{SERVICES['auth-service']}/token"
        
        response = self.session.post(
            token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        
        if response.status_code != 200:
            raise E2ETestError(f"Token exchange failed: {response.status_code} - {response.text}")
        
        token_response = response.json()
        
        if 'access_token' not in token_response:
            raise E2ETestError(f"No access token in response: {token_response}")
        
        access_token = token_response['access_token']
        print(f"✓ Access token obtained: {access_token[:20]}...")
        
        return access_token
    
    def create_context(self):
        """Create context data using the context-service."""
        print("📄 Creating context data...")
        
        try:
            context_data = {
                "context_data": {
                    "user_preferences": {
                        "theme": "dark",
                        "language": "en",
                        "notifications": True
                    },
                    "session_info": {
                        "login_time": "2024-01-15T10:00:00Z",
                        "last_activity": "2024-01-15T10:30:00Z"
                    },
                    "workflow_test": True,
                    "test_id": str(uuid.uuid4())
                },
                "context_type": "e2e_test_preferences",
                "title": "E2E Test User Preferences",
                "description": "Test context data for end-to-end workflow validation",
                "tags": ["e2e", "test", "workflow", "preferences"],
                "tenant_id": TEST_TENANT_ID,
                "user_id": TEST_USER_ID
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Tenant-ID": TEST_TENANT_ID,
                "X-Request-ID": str(uuid.uuid4())
            }
            
            context_url = f"{SERVICES['context-service']}/context"
            
            response = self.session.post(
                context_url,
                json=context_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise E2ETestError(f"Context creation failed: {response.status_code} - {response.text}")
            
            context_response = response.json()
            self.context_id = context_response.get("id")
            
            if not self.context_id:
                raise E2ETestError(f"No context ID in response: {context_response}")
            
            print(f"✓ Context created successfully: {self.context_id}")
            
        except Exception as e:
            raise E2ETestError(f"Failed to create context: {e}")
    
    def summarize_text(self):
        """Summarize text using the text-summarization service."""
        print("📝 Summarizing text...")
        
        try:
            # Sample text that includes context information for summarization
            sample_text = f"""
            End-to-end testing is a crucial methodology for validating complete application workflows
            in distributed microservices architectures. This comprehensive testing approach ensures
            that all components of the system work together seamlessly, from authentication and
            authorization through data processing and service communication.
            
            In our MCP (Microservices Control Platform) architecture, the workflow involves multiple
            services: an OAuth2.1 compliant authentication service that provides secure JWT tokens,
            a context service that manages tenant-specific data and user preferences, and a text
            summarization service that processes content using AI models.
            
            The authentication flow uses PKCE (Proof Key for Code Exchange) for enhanced security,
            mutual TLS for service-to-service communication, and comprehensive observability through
            structured logging and Prometheus metrics. Context data is stored in tenant-isolated
            schemas within PostgreSQL, ensuring data isolation and compliance with multi-tenant
            security requirements.
            
            Text summarization leverages advanced natural language processing models to extract
            key insights from large documents while maintaining semantic coherence and relevance.
            The service provides configurable semantic thresholds, supports multiple AI model
            providers, and includes comprehensive error handling and rate limiting.
            
            Testing ID: {uuid.uuid4()}
            Context ID: {self.context_id}
            Tenant ID: {TEST_TENANT_ID}
            """
            
            summarization_request = {
                "text_blob": sample_text.strip(),
                "semantic_threshold": 0.75,
                "ai_model": "openai",
                "tenant_id": TEST_TENANT_ID,
                "user_id": TEST_USER_ID,
                "context_id": self.context_id,
                "metadata": {
                    "test_type": "e2e_workflow",
                    "timestamp": time.time()
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Tenant-ID": TEST_TENANT_ID,
                "X-Request-ID": str(uuid.uuid4())
            }
            
            summarization_url = f"{SERVICES['text-summarization']}/v1/summarize"
            
            response = self.session.post(
                summarization_url,
                json=summarization_request,
                headers=headers,
                timeout=60  # Longer timeout for AI processing
            )
            
            if response.status_code != 200:
                raise E2ETestError(f"Text summarization failed: {response.status_code} - {response.text}")
            
            summarization_response = response.json()
            
            # Validate response structure
            required_fields = ["refined_text", "semantic_score", "model_used"]
            for field in required_fields:
                if field not in summarization_response:
                    raise E2ETestError(f"Missing required field in response: {field}")
            
            semantic_score = summarization_response.get("semantic_score", 0)
            model_used = summarization_response.get("model_used", "unknown")
            refined_text = summarization_response.get("refined_text", "")
            
            print(f"✓ Text summarization completed successfully")
            print(f"  Model used: {model_used}")
            print(f"  Semantic score: {semantic_score:.3f}")
            print(f"  Summary length: {len(refined_text)} characters")
            
            # Validate semantic score meets threshold
            if semantic_score < 0.75:
                raise E2ETestError(f"Semantic score {semantic_score} below threshold 0.75")
            
        except Exception as e:
            raise E2ETestError(f"Failed to summarize text: {e}")
    
    def cleanup(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up test environment...")
        
        try:
            # Stop and remove containers
            cmd = ["docker-compose", "-f", COMPOSE_FILE, "down", "-v"]
            subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            print("✓ Development stack stopped")
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def run_workflow(self):
        """Run the complete end-to-end workflow."""
        try:
            print("=" * 60)
            print("🧪 Starting End-to-End Workflow Test")
            print("=" * 60)
            
            # Step 1: Start the stack
            self.start_stack()
            
            # Step 2: Obtain authentication token
            self.obtain_auth_token()
            
            # Step 3: Create context data
            self.create_context()
            
            # Step 4: Summarize text
            self.summarize_text()
            
            print("=" * 60)
            print("✅ End-to-End Workflow Test PASSED")
            print("=" * 60)
            return True
            
        except E2ETestError as e:
            print("=" * 60)
            print(f"❌ End-to-End Workflow Test FAILED: {e}")
            print("=" * 60)
            return False
            
        except Exception as e:
            print("=" * 60)
            print(f"💥 End-to-End Workflow Test ERROR: {e}")
            print("=" * 60)
            return False
            
        finally:
            self.cleanup()


def main():
    """Main entry point for standalone execution."""
    tester = WorkflowTester()
    success = tester.run_workflow()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


def test_e2e_workflow():
    """Pytest entry point for integration with test suite."""
    tester = WorkflowTester()
    success = tester.run_workflow()
    
    if not success:
        raise AssertionError("End-to-end workflow test failed")


if __name__ == "__main__":
    main()
