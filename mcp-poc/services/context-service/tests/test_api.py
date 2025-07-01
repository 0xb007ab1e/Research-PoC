"""
API tests for context-service using TestClient.

The tests cover:
- Basic HTTP operations
- Multitenant isolation logic
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models import ContextCreateRequest, ContextUpdateRequest, ContextResponse, ErrorResponse
from repository import TenantAwareDB

client = TestClient(app)

def test_create_context(context_create_request):
    """Test creating a new context"""
    response = client.post("/context", json=context_create_request.dict())
    
    assert response.status_code == 201
    context_response = ContextResponse(**response.json())
    assert context_response.context_data == context_create_request.context_data
    assert context_response.context_type == context_create_request.context_type


def test_get_context():
    """Test retrieving an existing context"""
    # Setup initial data
    create_request = ContextCreateRequest(
        context_data={"key": "value"},
        context_type="test",
    )
    create_response = client.post("/context", json=create_request.dict())
    context_id = create_response.json().get("id")

    # Test retrieval
    response = client.get(f"/context/{context_id}")
    assert response.status_code == 200
    context_response = ContextResponse(**response.json())
    assert context_response.id == context_id


def test_update_context():
    """Test updating an existing context"""
    # Setup initial data
    create_request = ContextCreateRequest(
        context_data={"key": "value"},
        context_type="test",
    )
    create_response = client.post("/context", json=create_request.dict())
    context_id = create_response.json().get("id")

    # Perform update
    update_request = ContextUpdateRequest(title="Updated Title")
    response = client.put(f"/context/{context_id}", json=update_request.dict())
    assert response.status_code == 200
    context_response = ContextResponse(**response.json())
    assert context_response.title == "Updated Title"


def test_multitenant_isolation():
    """Test multitenant isolation where context written for tenant A should not be visible to tenant B"""
    tenant_a_id = "tenant-a"
    tenant_b_id = "tenant-b"

    headers_a = {"X-Tenant-ID": tenant_a_id}
    headers_b = {"X-Tenant-ID": tenant_b_id}

    # Create a context for tenant A
    create_request_a = ContextCreateRequest(
        context_data={"key": "value-a"},
        context_type="type-a",
    )
    response_a = client.post("/context", json=create_request_a.dict(), headers=headers_a)
    context_id_a = response_a.json().get("id")

    # Attempt to retrieve the same context under tenant B (should fail)
    response_b = client.get(f"/context/{context_id_a}", headers=headers_b)
    assert response_b.status_code == 404

    # Tenant A should be able to retrieve their own context
    response_a_retrieve = client.get(f"/context/{context_id_a}", headers=headers_a)
    assert response_a_retrieve.status_code == 200
    context_response_a = ContextResponse(**response_a_retrieve.json())
    assert context_response_a.context_data == create_request_a.context_data

