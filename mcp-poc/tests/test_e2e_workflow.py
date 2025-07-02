"""
End-to-end integration tests for the MCP services.
Validates the complete workflow using testcontainers.

Workflow:
1. Obtain JWT from mock auth service.
2. Create context data via Context Service.
3. Summarize text via Text Summarization Service.
4. Validate database state and metrics.
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any
import time
import uuid
from jose import jwt

# Import test configuration and fixtures
from .conftest import TestConfig, PerformanceMetrics


@pytest.mark.asyncio
@pytest.mark.e2e
class TestE2EWorkflow:
    """End-to-end test suite for the complete service workflow."""
    
    # Service base URLs
    CONTEXT_SERVICE_URL = f"http://localhost:{TestConfig.TEST_CONTEXT_SERVICE_PORT}"
    SUMMARIZATION_SERVICE_URL = f"http://localhost:{TestConfig.TEST_SUMMARIZATION_SERVICE_PORT}"
    
    async def test_full_workflow(
        self,
        http_client: httpx.AsyncClient,
        authenticated_headers: Dict[str, str],
        sample_context_data: Dict[str, Any],
        sample_text_for_summarization: str,
        database_connection,
        cleanup_database,
        performance_metrics: PerformanceMetrics
    ):
        """Test the complete workflow from context creation to summarization."""
        
        # -- Step 1: Health checks --
        await self.check_service_health(http_client, self.CONTEXT_SERVICE_URL, "Context Service")
        await self.check_service_health(http_client, self.SUMMARIZATION_SERVICE_URL, "Summarization Service")
        
        # -- Step 2: Create context data --
        context_id = await self.create_context(
            http_client,
            authenticated_headers,
            sample_context_data,
            performance_metrics
        )
        
        # -- Step 3: Summarize text --
        await self.summarize_text(
            http_client,
            authenticated_headers,
            sample_text_for_summarization,
            performance_metrics
        )
        
        # -- Step 4: Verify database state --
        await self.verify_database_state(database_connection, context_id)
        
        # -- Step 5: Verify metrics endpoints --
        await self.verify_metrics(http_client, self.CONTEXT_SERVICE_URL, "Context Service")
        await self.verify_metrics(http_client, self.SUMMARIZATION_SERVICE_URL, "Summarization Service")
        
        # -- Step 6: Print performance report --
        self.print_performance_report(performance_metrics)
    
    async def check_service_health(self, client: httpx.AsyncClient, base_url: str, service_name: str):
        """Check the health of a service."""
        response = await client.get(f"{base_url}/healthz")
        assert response.status_code == 200, f"{service_name} health check failed"
        health_data = response.json()
        assert health_data["status"] == "healthy", f"{service_name} is not healthy"
        
        # Check for database dependency health in context service
        if service_name == "Context Service":
            assert health_data["dependencies"]["database"] == "healthy"
    
    async def create_context(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        context_data: Dict[str, Any],
        metrics: PerformanceMetrics
    ) -> str:
        """Create context data and validate the response."""
        start_time = time.time()
        response = await client.post(
            f"{self.CONTEXT_SERVICE_URL}/context",
            json=context_data,
            headers=headers
        )
        metrics.record_response_time("create_context", time.time() - start_time)
        
        assert response.status_code == 200, "Failed to create context"
        response_data = response.json()
        
        # Validate response schema
        assert "id" in response_data
        assert response_data["context_type"] == context_data["context_type"]
        assert response_data["tenant_id"] == TestConfig.TEST_TENANT_ID
        
        return response_data["id"]
    
    async def summarize_text(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        text: str,
        metrics: PerformanceMetrics
    ):
        """Summarize text and validate the response."""
        summarization_request = {
            "text_blob": text,
            "semantic_threshold": TestConfig.SEMANTIC_THRESHOLD,
            "ai_model": "openai",
            "tenant_id": TestConfig.TEST_TENANT_ID,
            "user_id": TestConfig.TEST_USER_ID
        }
        
        start_time = time.time()
        response = await client.post(
            f"{self.SUMMARIZATION_SERVICE_URL}/v1/summarize",
            json=summarization_request,
            headers=headers
        )
        metrics.record_response_time("summarize_text", time.time() - start_time)
        
        assert response.status_code == 200, "Failed to summarize text"
        response_data = response.json()
        
        # Validate response schema
        assert "refined_text" in response_data
        assert "semantic_score" in response_data
        assert response_data["semantic_score"] >= TestConfig.SEMANTIC_THRESHOLD
        assert response_data["model_used"] == "openai"
    
    async def verify_database_state(self, db_connection, context_id: str):
        """Verify that the context data was correctly saved to the database."""
        schema_name = f"tenant_{TestConfig.TEST_TENANT_ID.replace('-', '_')}"
        
        # Verify that the tenant schema was created
        schema_exists = await db_connection.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
            schema_name
        )
        assert schema_exists, f"Tenant schema {schema_name} not created"
        
        # Verify that the context entry exists
        context_row = await db_connection.fetchrow(
            f'SELECT * FROM "{schema_name}".contexts WHERE id = $1',
            uuid.UUID(context_id)
        )
        assert context_row is not None, f"Context with ID {context_id} not found in database"
        assert str(context_row["id"]) == context_id
        assert context_row["tenant_id"] == TestConfig.TEST_TENANT_ID
    
    async def verify_metrics(self, client: httpx.AsyncClient, base_url: str, service_name: str):
        """Verify that the metrics endpoint is working and contains expected metrics."""
        response = await client.get(f"{base_url}/metrics")
        assert response.status_code == 200, f"{service_name} metrics endpoint failed"
        
        metrics_text = response.text
        
        # Check for core HTTP metrics
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        
        # Check for service-specific metrics
        if service_name == "Context Service":
            assert "contexts_total" in metrics_text
        elif service_name == "Summarization Service":
            assert "summarizations_total" in metrics_text
            assert "semantic_similarity_score" in metrics_text
    
    def print_performance_report(self, metrics: PerformanceMetrics):
        """Print a summary of performance metrics."""
        print("\n-- Performance Report --")
        for endpoint, times in metrics.metrics.items():
            avg_time = metrics.get_average_response_time(endpoint)
            p95_time = metrics.get_p95_response_time(endpoint)
            print(f"Endpoint: {endpoint}")
            print(f"  - Average response time: {avg_time:.4f}s")
            print(f"  - P95 response time: {p95_time:.4f}s")
            print(f"  - Total requests: {len(times)}")
        print("----------------------")

