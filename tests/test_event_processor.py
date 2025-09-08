"""Test Event Processor service"""

import json
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.event_processor.main import EventProcessor
from shared.models.enums import EventStatus


class TestEventProcessor:
    """Test Event Processor functionality"""
    
    @pytest.fixture
    def processor(self):
        """Create event processor instance"""
        return EventProcessor()
    
    @pytest.fixture
    def sample_event_json(self, sample_llm_event):
        """Sample event as JSON string (as it would come from Redis)"""
        event_data = sample_llm_event.copy()
        event_data["event_id"] = str(uuid.uuid4())
        event_data["timestamp"] = datetime.utcnow().isoformat()
        return json.dumps(event_data)
    
    def test_event_processor_init(self, processor):
        """Test event processor initialization"""
        assert processor.running is False
        assert processor.batch_size == 10
        assert processor.processing_timeout == 30
    
    def test_deserialize_event_success(self, processor, sample_event_json):
        """Test successful event deserialization"""
        
        result = processor._deserialize_event(sample_event_json.encode('utf-8'))
        
        assert isinstance(result, dict)
        assert result["tenant_id"] == "test-tenant"
        assert result["user_id"] == "test-user"
        assert result["service_type"] == "llm_service"
        assert isinstance(result["event_id"], uuid.UUID)
        assert isinstance(result["timestamp"], datetime)
    
    def test_deserialize_event_invalid_json(self, processor):
        """Test event deserialization with invalid JSON"""
        
        invalid_json = b'{"invalid": json}'
        result = processor._deserialize_event(invalid_json)
        
        assert result == {}  # Should return empty dict on error
    
    @pytest.mark.asyncio
    @patch('services.event_processor.main.get_session')
    async def test_process_single_event_success(self, mock_get_session, processor):
        """Test successful processing of single event"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock repositories
        mock_service_repo = AsyncMock()
        mock_service_repo.get_service_config.return_value = None  # No special config
        
        mock_billing_repo = AsyncMock()
        mock_billing_repo.get_active_billing_rule.return_value = None  # No billing rule
        
        with patch('services.event_processor.main.ServiceRegistryRepository', return_value=mock_service_repo):
            with patch('services.event_processor.main.BillingRuleRepository', return_value=mock_billing_repo):
                
                event_data = {
                    "event_id": uuid.uuid4(),
                    "tenant_id": "test-tenant",
                    "user_id": "test-user",
                    "service_type": "llm_service",
                    "service_provider": "openai",
                    "event_type": "completion",
                    "metadata_": {"model": "gpt-4"},
                    "metrics": {"input_tokens": 100, "output_tokens": 50}
                }
                
                result = await processor._process_single_event(event_data)
                
                assert result is not None
                assert result["status"] == EventStatus.COMPLETED
                assert result["error_message"] is None
                assert "billing_info" in result
                assert "processed_at" in result
    
    @pytest.mark.asyncio
    async def test_process_single_event_missing_fields(self, processor):
        """Test processing event with missing required fields"""
        
        event_data = {
            "event_id": uuid.uuid4(),
            "tenant_id": "test-tenant",
            # Missing user_id, service_type, etc.
        }
        
        result = await processor._process_single_event(event_data)
        
        assert result is not None
        assert result["status"] == EventStatus.FAILED
        assert "Missing required field" in result["error_message"]
        assert result["retry_count"] == 1
    
    @pytest.mark.asyncio
    @patch('services.event_processor.main.get_session')
    async def test_enrich_event_llm_service(self, mock_get_session, processor):
        """Test event enrichment for LLM service"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_repo = AsyncMock()
        mock_repo.get_service_config.return_value = None
        
        with patch('services.event_processor.main.ServiceRegistryRepository', return_value=mock_repo):
            event_data = {
                "service_type": "llm_service",
                "metadata_": {"model": "gpt-4"},
                "metrics": {
                    "input_tokens": 100,
                    "output_tokens": 50
                }
            }
            
            result = await processor._enrich_event(event_data)
            
            assert "processed_at" in result
            assert result["metrics"]["total_tokens"] == 150  # Auto-calculated
    
    @pytest.mark.asyncio
    @patch('services.event_processor.main.get_session')
    async def test_calculate_billing_with_rule(self, mock_get_session, processor):
        """Test billing calculation with active billing rule"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock billing rule
        mock_rule = MagicMock()
        mock_rule.billing_unit = "tokens"
        mock_rule.rate_per_unit = 0.00002
        mock_rule.calculation_method = "multiply"
        mock_rule.minimum_charge = None
        mock_rule.tiered_rates = None
        
        mock_repo = AsyncMock()
        mock_repo.get_active_billing_rule.return_value = mock_rule
        
        with patch('services.event_processor.main.BillingRuleRepository', return_value=mock_repo):
            event_data = {
                "service_type": "llm_service",
                "service_provider": "openai",
                "metadata_": {"model": "gpt-4"},
                "metrics": {"total_tokens": 150}
            }
            
            result = await processor._calculate_billing(event_data)
            
            assert "total_cost" in result
            assert result["billing_unit"] == "tokens"
            assert result["calculation_method"] == "multiply"
            # 150 tokens * 0.00002 = 0.003
            assert result["total_cost"] == 0.003
    
    @pytest.mark.asyncio
    @patch('services.event_processor.main.get_session') 
    async def test_calculate_billing_no_rule(self, mock_get_session, processor):
        """Test billing calculation without billing rule"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_repo = AsyncMock()
        mock_repo.get_active_billing_rule.return_value = None  # No billing rule
        
        with patch('services.event_processor.main.BillingRuleRepository', return_value=mock_repo):
            event_data = {
                "service_type": "llm_service",
                "service_provider": "openai"
            }
            
            result = await processor._calculate_billing(event_data)
            
            assert result["total_cost"] == 0.0
            assert result["billing_unit"] == "unknown"
    
    @pytest.mark.asyncio
    @patch('services.event_processor.main.get_session')
    async def test_store_events_success(self, mock_get_session, processor):
        """Test successful event storage"""
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.upsert_event = AsyncMock()
        
        events = [
            {"event_id": uuid.uuid4(), "tenant_id": "test-tenant"},
            {"event_id": uuid.uuid4(), "tenant_id": "test-tenant"}
        ]
        
        with patch('services.event_processor.main.UsageEventRepository', return_value=mock_repo):
            await processor._store_events(events)
            
            # Verify upsert was called for each event
            assert mock_repo.upsert_event.call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_failed_events_retry(self, processor):
        """Test handling failed events with retry logic"""
        
        # Mock Redis client
        processor.redis_client = AsyncMock()
        
        failed_events = [
            {"event_id": uuid.uuid4(), "retry_count": 1},  # Should retry
            {"event_id": uuid.uuid4(), "retry_count": 2},  # Should retry
            {"event_id": uuid.uuid4(), "retry_count": 3},  # Should go to dead letter
        ]
        
        await processor._handle_failed_events(failed_events)
        
        # Verify Redis calls
        assert processor.redis_client.lpush.call_count == 3  # 2 requeues + 1 dead letter
    
    def test_json_serializer(self, processor):
        """Test JSON serializer for datetime and UUID objects"""
        
        test_datetime = datetime.utcnow()
        test_uuid = uuid.uuid4()
        
        # Test datetime serialization
        result = processor._json_serializer(test_datetime)
        assert isinstance(result, str)
        assert "T" in result  # ISO format
        
        # Test UUID serialization
        result = processor._json_serializer(test_uuid)
        assert isinstance(result, str)
        assert len(result) == 36  # UUID string length
        
        # Test unsupported type
        with pytest.raises(TypeError):
            processor._json_serializer({"unsupported": "object"})