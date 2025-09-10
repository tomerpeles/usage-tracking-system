"""Test API Gateway service"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from services.api_gateway.main import app


class TestAPIGateway:
    """Test API Gateway endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Test authentication headers"""
        return {"X-API-Key": "test-api-key"}
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    @patch('services.api_gateway.main.redis_client', new_callable=AsyncMock)
    @patch('services.api_gateway.main.get_session')
    def test_create_event_success(self, mock_get_session, mock_redis, client, auth_headers):
        """Test successful event creation"""
        
        # Mock Redis
        mock_redis.lpush = AsyncMock()
        
        event_data = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "service_type": "llm_service",
            "service_provider": "openai",
            "event_type": "completion",
            "model": "gpt-4",
            "temperature": 0.7,
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150
        }
        
        response = client.post(
            "/api/v1/events",
            json=event_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        assert "message" in data
    
    def test_create_event_validation_error(self, client, auth_headers):
        """Test event creation with validation error"""
        
        # Missing required fields
        event_data = {
            "tenant_id": "test-tenant",
            # Missing user_id, service_type, etc.
        }
        
        response = client.post(
            "/api/v1/events",
            json=event_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid event data" in response.json()["detail"]
    
    def test_create_event_without_auth(self, client):
        """Test event creation without authentication"""
        
        event_data = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "service_type": "llm_service",
            "service_provider": "openai",
            "event_type": "completion"
        }
        
        response = client.post("/api/v1/events", json=event_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_required"
    
    @patch('services.api_gateway.main.redis_client', new_callable=AsyncMock)
    def test_create_batch_events_success(self, mock_redis, client, auth_headers):
        """Test successful batch event creation"""
        
        # Mock Redis
        mock_pipeline = MagicMock()
        mock_pipeline.lpush = MagicMock()
        mock_pipeline.execute = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        
        batch_data = {
            "events": [
                {
                    "tenant_id": "test-tenant",
                    "user_id": "test-user",
                    "service_type": "llm_service",
                    "service_provider": "openai",
                    "event_type": "completion",
                    "model": "gpt-4",
                    "input_tokens": 100,
                    "output_tokens": 50
                },
                {
                    "tenant_id": "test-tenant", 
                    "user_id": "test-user",
                    "service_type": "api_service",
                    "service_provider": "payment_api",
                    "event_type": "request",
                    "endpoint": "/payment",
                    "method": "POST",
                    "request_count": 1
                }
            ]
        }
        
        response = client.post(
            "/api/v1/events/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["processed_count"] == 2
        assert data["failed_count"] == 0
    
    def test_create_batch_events_empty(self, client, auth_headers):
        """Test batch creation with empty events list"""
        
        batch_data = {"events": []}
        
        response = client.post(
            "/api/v1/events/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "No events provided" in response.json()["detail"]
    
    def test_create_batch_events_too_large(self, client, auth_headers):
        """Test batch creation exceeding size limit"""
        
        # Create batch larger than max size (1000)
        events = []
        for i in range(1001):
            events.append({
                "tenant_id": "test-tenant",
                "user_id": f"user_{i}",
                "service_type": "api_service",
                "service_provider": "test_api",
                "event_type": "request"
            })
        
        batch_data = {"events": events}
        
        response = client.post(
            "/api/v1/events/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "exceeds maximum" in response.json()["detail"]
    
    @patch('services.api_gateway.main.get_session')
    def test_get_usage_success(self, mock_get_session, client, auth_headers):
        """Test successful usage query"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock repository
        mock_repo = MagicMock()
        mock_event = MagicMock()
        mock_event.event_id = "test-event-id"
        mock_event.timestamp = "2024-01-01T00:00:00"
        mock_event.user_id = "test-user"
        mock_event.service_type = "llm_service"
        mock_event.service_provider = "openai"
        mock_event.event_type = "completion"
        mock_event.metrics = {"tokens": 150}
        mock_event.tags = ["test"]
        mock_event.billing_info = None
        mock_event.total_cost = None
        
        mock_repo.get_events_by_tenant = AsyncMock(return_value=([mock_event], 1))
        
        with patch('services.api_gateway.main.UsageEventRepository', return_value=mock_repo):
            response = client.get(
                "/api/v1/usage",
                params={
                    "tenant_id": "test-tenant",
                    "service_type": "llm_service",
                    "limit": 100
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["service_type"] == "llm_service"
    
    def test_get_usage_without_tenant(self, client, auth_headers):
        """Test usage query without tenant_id"""
        
        response = client.get(
            "/api/v1/usage",
            headers=auth_headers
        )
        
        # Should return validation error for missing tenant_id
        assert response.status_code == 422  # FastAPI validation error