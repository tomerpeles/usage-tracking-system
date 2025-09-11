"""Test client SDK"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from client_sdk import UsageTracker
from client_sdk.exceptions import (
    ValidationError, 
    RateLimitError, 
    AuthenticationError,
    ConfigurationError
)


class TestUsageTracker:
    """Test UsageTracker client"""
    
    def test_init_with_valid_config(self):
        """Test initializing tracker with valid configuration"""
        
        tracker = UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant"
        )
        
        assert tracker.api_key == "test-key"
        assert tracker.base_url == "http://localhost:8000"
        assert tracker.tenant_id == "test-tenant"
        assert tracker.timeout == 30.0
        assert tracker.max_retries == 3
    
    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises ConfigurationError"""
        
        with pytest.raises(ConfigurationError, match="API key is required"):
            UsageTracker(api_key="", base_url="http://localhost:8000")
    
    def test_init_without_base_url_raises_error(self):
        """Test that missing base URL raises ConfigurationError"""
        
        with pytest.raises(ConfigurationError, match="Base URL is required"):
            UsageTracker(api_key="test-key", base_url="")
    
    @pytest.mark.asyncio
    async def test_track_llm_success(self):
        """Test successful LLM event tracking"""
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "event_id": "test-event-id",
            "message": "Event tracked"
        }
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            event_id = await tracker.track_llm(
                user_id="test-user",
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                service_provider="openai"
            )
            
            assert event_id is not None
            mock_client.post.assert_called_once()
            
            # Verify call arguments
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/api/v1/events"
            
            event_data = call_args[1]["json"]
            assert event_data["user_id"] == "test-user"
            assert event_data["service_type"] == "llm_service"
            assert event_data["metrics"]["input_tokens"] == 100
            assert event_data["metrics"]["output_tokens"] == 50
            assert event_data["metrics"]["total_tokens"] == 150
    
    @pytest.mark.asyncio
    async def test_track_llm_validation_error(self):
        """Test LLM tracking with validation errors"""
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000"
        ) as tracker:
            
            # Missing user_id
            with pytest.raises(ValidationError, match="user_id is required"):
                await tracker.track_llm(
                    user_id="",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50
                )
            
            # Missing model
            with pytest.raises(ValidationError, match="model is required"):
                await tracker.track_llm(
                    user_id="test-user",
                    model="",
                    input_tokens=100,
                    output_tokens=50
                )
            
            # Invalid input tokens
            with pytest.raises(ValidationError, match="input_tokens must be >= 0"):
                await tracker.track_llm(
                    user_id="test-user",
                    model="gpt-4",
                    input_tokens=-1,
                    output_tokens=50
                )
    
    @pytest.mark.asyncio
    async def test_track_document_success(self):
        """Test successful document event tracking"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            await tracker.track_document(
                user_id="test-user",
                service_provider="document_ai",
                document_type="invoice",
                processing_type="extraction",
                pages_processed=5
            )
            
            mock_client.post.assert_called_once()
            
            event_data = mock_client.post.call_args[1]["json"]
            assert event_data["service_type"] == "document_processor"
            assert event_data["metrics"]["pages_processed"] == 5
    
    @pytest.mark.asyncio
    async def test_track_api_success(self):
        """Test successful API event tracking"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            await tracker.track_api(
                user_id="test-user",
                service_provider="payment_api",
                endpoint="/api/v1/payments",
                method="POST",
                response_time_ms=250
            )
            
            mock_client.post.assert_called_once()
            
            event_data = mock_client.post.call_args[1]["json"]
            assert event_data["service_type"] == "api_service"
            assert event_data["metadata"]["endpoint"] == "/api/v1/payments"
            assert event_data["metadata"]["method"] == "POST"
    
    @pytest.mark.asyncio
    async def test_track_custom_success(self):
        """Test successful custom event tracking"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            await tracker.track_custom(
                user_id="test-user",
                service_type="ml_model",
                service_provider="custom_ml",
                event_type="prediction",
                metrics={"predictions": 100},
                metadata={"model_version": "v1.0"}
            )
            
            mock_client.post.assert_called_once()
            
            event_data = mock_client.post.call_args[1]["json"]
            assert event_data["service_type"] == "ml_model"
            assert event_data["metrics"]["predictions"] == 100
    
    @pytest.mark.asyncio
    async def test_batch_tracking(self):
        """Test batch event tracking"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "processed_count": 2,
            "failed_count": 0
        }
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=True,
            batch_size=2
        ) as tracker:
            tracker._client = mock_client
            
            # Track two events
            await tracker.track_llm(
                user_id="user1",
                model="gpt-4",
                input_tokens=100,
                output_tokens=50
            )
            
            await tracker.track_llm(
                user_id="user2", 
                model="gpt-3.5-turbo",
                input_tokens=80,
                output_tokens=40
            )
            
            # Should have triggered batch send due to batch_size=2
            mock_client.post.assert_called_once_with(
                "/api/v1/events/batch",
                json={"events": ANY}
            )
    
    @pytest.mark.asyncio
    async def test_error_handling_401(self):
        """Test handling of 401 authentication error"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "authentication_failed",
            "message": "Invalid API key"
        }
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="invalid-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            with pytest.raises(AuthenticationError, match="Invalid API key"):
                await tracker.track_llm(
                    user_id="test-user",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50
                )
    
    @pytest.mark.asyncio
    async def test_error_handling_429(self):
        """Test handling of 429 rate limit error"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded"
        }
        mock_response.headers = {"Retry-After": "60"}
        mock_client.post.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant",
            enable_batching=False
        ) as tracker:
            tracker._client = mock_client
            
            with pytest.raises(RateLimitError) as exc_info:
                await tracker.track_llm(
                    user_id="test-user",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50
                )
            
            assert exc_info.value.retry_after == "60"
    
    @pytest.mark.asyncio
    async def test_get_usage_success(self):
        """Test successful usage query"""
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "event_id": "test-event-1",
                    "user_id": "test-user",
                    "service_type": "llm_service",
                    "metrics": {"tokens": 150}
                }
            ],
            "total_count": 1,
            "has_more": False
        }
        mock_client.get.return_value = mock_response
        
        async with UsageTracker(
            api_key="test-key",
            base_url="http://localhost:8000",
            tenant_id="test-tenant"
        ) as tracker:
            tracker._client = mock_client
            
            result = await tracker.get_usage(
                service_type="llm_service",
                limit=100
            )
            
            assert result["total_count"] == 1
            assert len(result["events"]) == 1
            assert result["events"][0]["event_id"] == "test-event-1"
            
            # Verify query parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["tenant_id"] == "test-tenant"
            assert params["service_type"] == "llm_service"
            assert params["limit"] == 100