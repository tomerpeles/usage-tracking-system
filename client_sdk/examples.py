"""Example usage of the Usage Tracking SDK"""
import asyncio
from datetime import datetime
from usage_tracker import UsageTracker


async def llm_tracking_example():
    """Example: Track LLM usage"""
    
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        # Track OpenAI GPT-4 usage
        event_id = await tracker.track_llm(
            user_id="user_456",
            model="gpt-4",
            service_provider="openai",
            input_tokens=1500,
            output_tokens=500,
            latency_ms=2500,
            temperature=0.7,
            max_tokens=2000,
            session_id="session_abc",
            metadata={
                "conversation_id": "conv_123",
                "application": "chatbot"
            },
            tags=["production", "customer-support"]
        )
        
        print(f"LLM event tracked: {event_id}")
        
        # Track Claude usage
        await tracker.track_llm(
            user_id="user_789",
            model="claude-3",
            service_provider="anthropic",
            input_tokens=800,
            output_tokens=300,
            latency_ms=1800,
            temperature=0.5,
            metadata={
                "use_case": "document_analysis"
            }
        )


async def document_tracking_example():
    """Example: Track document processing"""
    
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        # Track invoice processing
        event_id = await tracker.track_document(
            user_id="user_456",
            service_provider="document_ai",
            document_type="invoice",
            processing_type="data_extraction",
            pages_processed=5,
            characters_extracted=12000,
            processing_time_ms=4500,
            file_size_bytes=2048000,
            file_format="pdf",
            metadata={
                "extraction_accuracy": 0.98,
                "language": "en"
            },
            tags=["accounts-payable", "automation"]
        )
        
        print(f"Document event tracked: {event_id}")


async def api_tracking_example():
    """Example: Track API usage"""
    
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        # Track REST API call
        event_id = await tracker.track_api(
            user_id="user_456",
            service_provider="payment_api",
            endpoint="/api/v1/payments",
            method="POST",
            response_time_ms=850,
            payload_size_bytes=1024,
            response_size_bytes=512,
            status_code=201,
            api_version="v1",
            metadata={
                "payment_method": "credit_card",
                "amount": 99.99,
                "currency": "USD"
            },
            tags=["payments", "e-commerce"]
        )
        
        print(f"API event tracked: {event_id}")


async def custom_tracking_example():
    """Example: Track custom service usage"""
    
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        # Track custom ML model usage
        event_id = await tracker.track_custom(
            user_id="user_456",
            service_type="ml_model",
            service_provider="custom_ml_service",
            event_type="prediction",
            metrics={
                "predictions_made": 100,
                "model_version": "v2.1",
                "confidence_score": 0.95,
                "processing_time_ms": 250
            },
            metadata={
                "model_type": "sentiment_analysis",
                "dataset_version": "2024-01"
            },
            tags=["ml", "sentiment", "batch-processing"]
        )
        
        print(f"Custom event tracked: {event_id}")


async def batch_tracking_example():
    """Example: Using batch tracking for high-volume events"""
    
    # Enable batching for high-volume scenarios
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123",
        enable_batching=True,
        batch_size=50,
        flush_interval=2.0  # Flush every 2 seconds
    ) as tracker:
        
        # Track multiple events rapidly
        event_ids = []
        for i in range(100):
            event_id = await tracker.track_api(
                user_id=f"user_{i % 10}",  # Rotate users
                service_provider="high_volume_api",
                endpoint=f"/api/data/{i}",
                method="GET",
                response_time_ms=50 + (i % 100),
                status_code=200,
                metadata={"batch_id": "batch_001"}
            )
            event_ids.append(event_id)
        
        # Manually flush remaining events
        flushed_count = await tracker.flush_events()
        print(f"Tracked {len(event_ids)} events, flushed {flushed_count}")


async def usage_query_example():
    """Example: Query usage data"""
    
    async with UsageTracker(
        api_key="test-api-key",
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        # Query recent usage
        usage_data = await tracker.get_usage(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            service_type="llm_service",
            limit=100,
            include_billing=True
        )
        
        print(f"Found {usage_data['total_count']} events")
        print(f"Showing {len(usage_data['events'])} events")
        
        for event in usage_data['events'][:5]:  # Show first 5
            print(f"Event: {event['event_type']} by {event['user_id']}")
            if 'billing_info' in event:
                print(f"  Cost: ${event.get('total_cost', 0):.4f}")


async def error_handling_example():
    """Example: Error handling"""
    
    from exceptions import ValidationError, RateLimitError, AuthenticationError
    
    async with UsageTracker(
        api_key="invalid-key",  # This will cause auth error
        base_url="http://localhost:8000",
        tenant_id="tenant_123"
    ) as tracker:
        
        try:
            await tracker.track_llm(
                user_id="user_456",
                model="gpt-4",
                input_tokens=100,
                output_tokens=50
            )
        except AuthenticationError as e:
            print(f"Authentication failed: {e.message}")
        except ValidationError as e:
            print(f"Validation error: {e.message}")
            if e.field_errors:
                for error in e.field_errors:
                    print(f"  Field '{error.get('field')}': {error.get('message')}")
        except RateLimitError as e:
            print(f"Rate limited: {e.message}")
            if e.retry_after:
                print(f"Retry after {e.retry_after} seconds")
        except Exception as e:
            print(f"Unexpected error: {e}")


async def main():
    """Run all examples"""
    print("=== LLM Tracking Example ===")
    await llm_tracking_example()
    
    print("\n=== Document Tracking Example ===")
    await document_tracking_example()
    
    print("\n=== API Tracking Example ===")
    await api_tracking_example()
    
    print("\n=== Custom Tracking Example ===")
    await custom_tracking_example()
    
    print("\n=== Batch Tracking Example ===")
    await batch_tracking_example()
    
    print("\n=== Usage Query Example ===")
    await usage_query_example()
    
    print("\n=== Error Handling Example ===")
    await error_handling_example()


if __name__ == "__main__":
    asyncio.run(main())