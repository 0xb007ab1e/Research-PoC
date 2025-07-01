"""
Pytest configuration and fixtures for integration tests.
Provides shared test infrastructure using testcontainers.
"""

import os
import asyncio
import pytest
import httpx
from typing import Dict, Any, AsyncGenerator, Generator
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose
from testcontainers.core.waiting_utils import wait_for_logs
import time
import uuid
from jose import jwt
import json

# Test configuration
TEST_DATABASE_NAME = "test_mcp_db"
TEST_AUTH_SERVICE_PORT = 8443
TEST_CONTEXT_SERVICE_PORT = 8001
TEST_SUMMARIZATION_SERVICE_PORT = 8000

class TestConfig:
    """Test configuration constants"""
    
    # Test user credentials
    TEST_USER_ID = "test-user-123"
    TEST_TENANT_ID = "test-tenant-123"
    TEST_USERNAME = "test@example.com"
    
    # JWT test configuration
    JWT_SECRET = "test-secret-key-for-integration-tests-12345678901234567890"
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = "test-auth-service"
    JWT_AUDIENCE = "api"
    
    # Semantic threshold for tests
    SEMANTIC_THRESHOLD = 0.75
    
    # Test timeouts
    SERVICE_STARTUP_TIMEOUT = 120
    API_TIMEOUT = 30


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def postgres_container() -> AsyncGenerator[PostgresContainer, None]:
    """Start PostgreSQL container for testing."""
    with PostgresContainer(
        image="postgres:15-alpine",
        dbname=TEST_DATABASE_NAME,
        username="test_user",
        password="test_password",
        port=5432
    ) as postgres:
        # Wait for PostgreSQL to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
async def auth_service_container() -> AsyncGenerator[Dict[str, Any], None]:
    """Start auth service container using docker-compose."""
    compose_path = "services/text-summarization/auth-service"
    
    with DockerCompose(
        compose_file_name="docker-compose.yml",
        filepath=compose_path,
        pull=True
    ) as compose:
        # Wait for auth service to be ready
        auth_service = compose.get_service("auth-service", TEST_AUTH_SERVICE_PORT)
        
        # Wait for the service to be healthy
        wait_for_logs(
            container=compose.get_service_container("auth-service"),
            predicate="auth-service started",
            timeout=TestConfig.SERVICE_STARTUP_TIMEOUT
        )
        
        yield {
            "host": auth_service.get_service_host("auth-service", TEST_AUTH_SERVICE_PORT),
            "port": auth_service.get_service_port("auth-service", TEST_AUTH_SERVICE_PORT),
            "base_url": f"https://{auth_service.get_service_host('auth-service', TEST_AUTH_SERVICE_PORT)}:{auth_service.get_service_port('auth-service', TEST_AUTH_SERVICE_PORT)}"
        }


@pytest.fixture(scope="session")
async def test_jwt_token() -> str:
    """Generate a test JWT token for authentication."""
    payload = {
        "sub": TestConfig.TEST_USERNAME,
        "user_id": TestConfig.TEST_USER_ID,
        "tenant_id": TestConfig.TEST_TENANT_ID,
        "iss": TestConfig.JWT_ISSUER,
        "aud": TestConfig.JWT_AUDIENCE,
        "exp": int(time.time()) + 3600,  # 1 hour
        "iat": int(time.time()),
        "scopes": ["read", "write"]
    }
    
    token = jwt.encode(
        payload,
        TestConfig.JWT_SECRET,
        algorithm=TestConfig.JWT_ALGORITHM
    )
    
    return token


@pytest.fixture(scope="session")
async def test_environment_vars(postgres_container: PostgresContainer) -> Dict[str, str]:
    """Set up environment variables for test services."""
    db_url = postgres_container.get_connection_url()
    
    return {
        # Database configuration
        "DB_HOST": postgres_container.get_container_host_ip(),
        "DB_PORT": str(postgres_container.get_exposed_port(5432)),
        "DB_NAME": TEST_DATABASE_NAME,
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        
        # Service configuration
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        
        # Security configuration (relaxed for testing)
        "ENABLE_TLS": "false",
        "ENABLE_MUTUAL_TLS": "false",
        "REQUIRE_TENANT_ID": "true",
        "REQUIRE_REQUEST_ID": "false",
        "AUTO_GENERATE_REQUEST_ID": "true",
        
        # JWT configuration
        "JWT_SECRET_KEY": TestConfig.JWT_SECRET,
        "JWT_ALGORITHM": TestConfig.JWT_ALGORITHM,
        "AUTH_SERVICE_URL": "http://localhost:8080",  # Mock for testing
        
        # Rate limiting (relaxed for testing)
        "RATE_LIMIT_CALLS": "1000",
        "RATE_LIMIT_PERIOD": "60",
        
        # AI model configuration (mock for testing)
        "OPENAI_API_KEY": "test-key",
        "DEFAULT_SEMANTIC_THRESHOLD": str(TestConfig.SEMANTIC_THRESHOLD),
    }


@pytest.fixture(scope="function")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for API testing."""
    async with httpx.AsyncClient(
        timeout=TestConfig.API_TIMEOUT,
        verify=False  # Disable SSL verification for testing
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def authenticated_headers(test_jwt_token: str) -> Dict[str, str]:
    """Create authenticated headers for API requests."""
    return {
        "Authorization": f"Bearer {test_jwt_token}",
        "Content-Type": "application/json",
        "X-Tenant-ID": TestConfig.TEST_TENANT_ID,
        "X-Request-ID": str(uuid.uuid4())
    }


@pytest.fixture(scope="function")
async def sample_context_data() -> Dict[str, Any]:
    """Generate sample context data for testing."""
    return {
        "context_data": {
            "user_preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True
            },
            "session_info": {
                "login_time": "2024-01-15T10:00:00Z",
                "last_activity": "2024-01-15T10:30:00Z"
            }
        },
        "context_type": "user_preferences",
        "title": "Test User Preferences",
        "description": "Test context data for integration testing",
        "tags": ["test", "integration", "preferences"],
        "tenant_id": TestConfig.TEST_TENANT_ID,
        "user_id": TestConfig.TEST_USER_ID
    }


@pytest.fixture(scope="function")
async def sample_text_for_summarization() -> str:
    """Generate sample text for summarization testing."""
    return """
    Artificial intelligence (AI) has become one of the most transformative technologies of our time, 
    revolutionizing industries and changing the way we work, communicate, and live. From machine learning 
    algorithms that can predict market trends to natural language processing systems that can understand 
    and generate human-like text, AI is reshaping our world in unprecedented ways.
    
    Machine learning, a subset of AI, enables computers to learn and improve from experience without 
    being explicitly programmed. This technology powers recommendation systems on streaming platforms, 
    fraud detection in banking, and autonomous vehicles that can navigate complex traffic scenarios. 
    Deep learning, which uses neural networks with multiple layers, has achieved remarkable success 
    in image recognition, speech processing, and game playing.
    
    Natural language processing (NLP) allows computers to understand, interpret, and generate human 
    language. This technology enables chatbots to provide customer service, translation services to 
    break down language barriers, and sentiment analysis tools to gauge public opinion on social media. 
    Large language models have demonstrated impressive capabilities in generating coherent and contextually 
    relevant text across various domains.
    
    The applications of AI span numerous sectors including healthcare, where it assists in medical 
    diagnosis and drug discovery; finance, where it helps with algorithmic trading and risk assessment; 
    education, where it personalizes learning experiences; and entertainment, where it creates immersive 
    gaming experiences and generates creative content. As AI continues to evolve, it promises to bring 
    even more innovative solutions to complex global challenges.
    """


@pytest.fixture(scope="function")
async def database_connection(postgres_container: PostgresContainer):
    """Create database connection for direct database testing."""
    import asyncpg
    
    connection = await asyncpg.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        database=TEST_DATABASE_NAME,
        user="test_user",
        password="test_password"
    )
    
    yield connection
    
    await connection.close()


@pytest.fixture(autouse=True)
async def setup_test_environment(test_environment_vars):
    """Automatically set up test environment variables for each test."""
    original_env = {}
    
    # Save original environment variables
    for key, value in test_environment_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment variables
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Test data cleanup utilities
@pytest.fixture(scope="function")
async def cleanup_database(database_connection):
    """Clean up test data after each test."""
    yield
    
    # Clean up test data
    test_schemas = [f"tenant_{TestConfig.TEST_TENANT_ID.replace('-', '_')}"]
    
    for schema in test_schemas:
        try:
            await database_connection.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        except Exception:
            pass  # Schema might not exist


# Performance testing utilities
class PerformanceMetrics:
    """Helper class to collect performance metrics during tests."""
    
    def __init__(self):
        self.metrics = {}
    
    def record_response_time(self, endpoint: str, duration: float):
        """Record response time for an endpoint."""
        if endpoint not in self.metrics:
            self.metrics[endpoint] = []
        self.metrics[endpoint].append(duration)
    
    def get_average_response_time(self, endpoint: str) -> float:
        """Get average response time for an endpoint."""
        if endpoint not in self.metrics:
            return 0.0
        return sum(self.metrics[endpoint]) / len(self.metrics[endpoint])
    
    def get_p95_response_time(self, endpoint: str) -> float:
        """Get 95th percentile response time for an endpoint."""
        if endpoint not in self.metrics:
            return 0.0
        
        times = sorted(self.metrics[endpoint])
        index = int(0.95 * len(times))
        return times[min(index, len(times) - 1)]


@pytest.fixture(scope="function")
def performance_metrics():
    """Provide performance metrics collection."""
    return PerformanceMetrics()
