import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
import structlog
from sqlalchemy.exc import IntegrityError

from config import settings
from shared.database import get_session, UsageEventRepository, ServiceRegistryRepository, BillingRuleRepository
from shared.models.enums import ServiceType, EventStatus
from shared.utils import setup_logging, get_logger, calculate_event_cost

# Setup logging
setup_logging()
logger = get_logger("event_processor")


class EventProcessor:
    """Main event processor for handling usage events"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.batch_size = 10
        self.processing_timeout = 30
    
    async def start(self):
        """Start the event processor"""
        logger.info("Starting event processor")
        
        # Connect to Redis
        try:
            self.redis_client = redis.from_url(settings.redis.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis", redis_url=settings.redis.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
        
        self.running = True
        
        # Start processing loop
        await self._processing_loop()
    
    async def stop(self):
        """Stop the event processor"""
        logger.info("Stopping event processor")
        self.running = False
        
        if self.redis_client:
            await self.redis_client.close()
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Get batch of events from Redis queue
                events = await self._get_event_batch()
                
                if not events:
                    # No events to process, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                # Process the batch
                await self._process_event_batch(events)
                
            except Exception as e:
                logger.error("Error in processing loop", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _get_event_batch(self) -> List[Dict[str, Any]]:
        """Get a batch of events from Redis queue"""
        if not self.redis_client:
            return []
        
        try:
            # Use BRPOP to block until events are available
            result = await self.redis_client.brpop(
                ["usage_events"], 
                timeout=self.processing_timeout
            )
            
            if not result:
                return []
            
            queue_name, event_data = result
            events = [self._deserialize_event(event_data)]
            
            # Try to get more events for batch processing (non-blocking)
            for _ in range(self.batch_size - 1):
                additional_event = await self.redis_client.rpop("usage_events")
                if additional_event:
                    events.append(self._deserialize_event(additional_event))
                else:
                    break
            
            logger.info("Retrieved event batch", batch_size=len(events))
            return events
            
        except Exception as e:
            logger.error("Failed to get events from queue", error=str(e))
            return []
    
    def _deserialize_event(self, event_data: bytes) -> Dict[str, Any]:
        """Deserialize event data from Redis"""
        try:
            event_dict = json.loads(event_data.decode('utf-8'))
            
            # Convert string UUIDs back to UUID objects
            if 'event_id' in event_dict:
                event_dict['event_id'] = uuid.UUID(event_dict['event_id'])
            if 'id' in event_dict:
                event_dict['id'] = uuid.UUID(event_dict['id'])
            
            # Convert timestamp strings back to datetime
            if 'timestamp' in event_dict:
                event_dict['timestamp'] = datetime.fromisoformat(event_dict['timestamp'])
            if 'created_at' in event_dict:
                event_dict['created_at'] = datetime.fromisoformat(event_dict['created_at'])
            if 'updated_at' in event_dict:
                event_dict['updated_at'] = datetime.fromisoformat(event_dict['updated_at'])
            
            return event_dict
            
        except Exception as e:
            logger.error("Failed to deserialize event", error=str(e))
            return {}
    
    async def _process_event_batch(self, events: List[Dict[str, Any]]):
        """Process a batch of events"""
        successful_events = []
        failed_events = []
        
        for event in events:
            try:
                processed_event = await self._process_single_event(event)
                if processed_event:
                    successful_events.append(processed_event)
                else:
                    failed_events.append(event)
                    
            except Exception as e:
                logger.error("Failed to process event", error=str(e), event_id=event.get('event_id'))
                failed_events.append(event)
        
        # Store successful events in database
        if successful_events:
            await self._store_events(successful_events)
        
        # Handle failed events
        if failed_events:
            await self._handle_failed_events(failed_events)
        
        logger.info(
            "Processed event batch",
            successful=len(successful_events),
            failed=len(failed_events)
        )
    
    async def _process_single_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single event"""
        event_id = event.get('event_id')
        if not event_id:
            logger.warning("Event missing event_id", event=event)
            return None
        
        try:
            # Validate required fields
            required_fields = ['tenant_id', 'user_id', 'service_type', 'service_provider', 'event_type']
            for field in required_fields:
                if field not in event:
                    raise ValueError(f"Missing required field: {field}")
            
            # Enrich event with additional data
            enriched_event = await self._enrich_event(event)
            
            # Calculate billing information
            billing_info = await self._calculate_billing(enriched_event)
            enriched_event['billing_info'] = billing_info
            enriched_event['total_cost'] = billing_info.get('total_cost', 0.0)
            
            # Set processing status
            enriched_event['status'] = EventStatus.COMPLETED
            enriched_event['error_message'] = None
            
            return enriched_event
            
        except Exception as e:
            logger.error("Failed to process event", error=str(e), event_id=event_id)
            
            # Mark event as failed
            event['status'] = EventStatus.FAILED
            event['error_message'] = str(e)
            event['retry_count'] = event.get('retry_count', 0) + 1
            
            return event
    
    async def _enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with additional metadata and calculated fields"""
        
        # Add processing metadata
        event['processed_at'] = datetime.utcnow()
        
        # Get service configuration for additional enrichment
        service_type = event.get('service_type')
        if service_type:
            async with get_session() as session:
                service_repo = ServiceRegistryRepository(session)
                service_config = await service_repo.get_service_config(ServiceType(service_type))
                
                if service_config:
                    # Add service-specific enrichment based on configuration
                    enrichment_rules = service_config.aggregation_rules.get('enrichment', {})
                    
                    # Apply enrichment rules
                    for field, rule in enrichment_rules.items():
                        if rule.get('calculate'):
                            # Implement custom field calculations
                            event['metadata_'] = event.get('metadata_', {})
                            event['metadata_'][field] = self._apply_calculation_rule(event, rule)
        
        # Calculate derived metrics
        metrics = event.get('metrics', {})
        if service_type == ServiceType.LLM_SERVICE:
            # Ensure total_tokens is calculated
            if 'input_tokens' in metrics and 'output_tokens' in metrics:
                metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens']
        
        # Add session duration if timestamps are available
        if 'session_start' in metrics and 'session_end' in metrics:
            try:
                start = datetime.fromisoformat(metrics['session_start'])
                end = datetime.fromisoformat(metrics['session_end'])
                metrics['session_duration_ms'] = int((end - start).total_seconds() * 1000)
            except Exception:
                pass
        
        event['metrics'] = metrics
        return event
    
    def _apply_calculation_rule(self, event: Dict[str, Any], rule: Dict[str, Any]) -> Any:
        """Apply a calculation rule to derive field values"""
        
        # This is a simplified version - in production you'd want a more robust
        # expression evaluation system (like using AST or a safe eval library)
        
        calculation = rule.get('calculate', '')
        metrics = event.get('metrics', {})
        
        # Simple calculations
        if calculation == 'total_tokens':
            return metrics.get('input_tokens', 0) + metrics.get('output_tokens', 0)
        elif calculation == 'cost_per_token':
            total_tokens = metrics.get('total_tokens', 1)  # Avoid division by zero
            total_cost = event.get('billing_info', {}).get('total_cost', 0)
            return total_cost / total_tokens if total_tokens > 0 else 0
        
        return None
    
    async def _calculate_billing(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate billing information for an event"""
        
        service_type = event.get('service_type')
        provider = event.get('service_provider')
        
        if not service_type or not provider:
            return {'total_cost': 0.0, 'billing_unit': 'unknown'}
        
        try:
            # Get billing rules for this service/provider
            async with get_session() as session:
                billing_repo = BillingRuleRepository(session)
                
                # Try to get model-specific rule first
                model = event.get('metadata_', {}).get('model')
                billing_rule = await billing_repo.get_active_billing_rule(
                    ServiceType(service_type), 
                    provider,
                    model
                )
                
                if not billing_rule:
                    # Fall back to general provider rule
                    billing_rule = await billing_repo.get_active_billing_rule(
                        ServiceType(service_type), 
                        provider
                    )
                
                if billing_rule:
                    # Convert SQLAlchemy model to dict for billing calculation
                    rule_dict = {
                        'billing_unit': billing_rule.billing_unit,
                        'rate_per_unit': float(billing_rule.rate_per_unit),
                        'calculation_method': billing_rule.calculation_method,
                        'minimum_charge': float(billing_rule.minimum_charge) if billing_rule.minimum_charge else None,
                        'tiered_rates': billing_rule.tiered_rates,
                    }
                    
                    return calculate_event_cost(event, rule_dict)
                
        except Exception as e:
            logger.error("Failed to calculate billing", error=str(e), event_id=event.get('event_id'))
        
        # Return default billing info
        return {
            'total_cost': 0.0,
            'billing_unit': 'unknown',
            'rate_per_unit': 0.0,
            'calculation_method': 'none'
        }
    
    async def _store_events(self, events: List[Dict[str, Any]]):
        """Store processed events in database"""
        try:
            async with get_session() as session:
                repo = UsageEventRepository(session)
                
                # Use upsert to handle potential duplicates
                for event in events:
                    await repo.upsert_event(event)
                
                logger.info("Stored events in database", count=len(events))
                
        except Exception as e:
            logger.error("Failed to store events", error=str(e))
            # Re-queue failed events for retry
            await self._requeue_events(events)
    
    async def _handle_failed_events(self, failed_events: List[Dict[str, Any]]):
        """Handle events that failed to process"""
        
        retry_events = []
        dead_letter_events = []
        
        for event in failed_events:
            retry_count = event.get('retry_count', 0)
            
            if retry_count < 3:  # Max retries
                retry_events.append(event)
            else:
                dead_letter_events.append(event)
        
        # Requeue events for retry
        if retry_events:
            await self._requeue_events(retry_events)
        
        # Send dead letter events to special queue for manual review
        if dead_letter_events:
            await self._send_to_dead_letter_queue(dead_letter_events)
    
    async def _requeue_events(self, events: List[Dict[str, Any]]):
        """Requeue events for retry"""
        if not self.redis_client:
            return
        
        try:
            for event in events:
                event_json = json.dumps(event, default=self._json_serializer)
                await self.redis_client.lpush("usage_events", event_json)
            
            logger.info("Requeued events for retry", count=len(events))
            
        except Exception as e:
            logger.error("Failed to requeue events", error=str(e))
    
    async def _send_to_dead_letter_queue(self, events: List[Dict[str, Any]]):
        """Send failed events to dead letter queue"""
        if not self.redis_client:
            return
        
        try:
            for event in events:
                event['status'] = 'dead_letter'
                event['dead_letter_at'] = datetime.utcnow()
                
                event_json = json.dumps(event, default=self._json_serializer)
                await self.redis_client.lpush("dead_letter_events", event_json)
            
            logger.warning("Sent events to dead letter queue", count=len(events))
            
        except Exception as e:
            logger.error("Failed to send events to dead letter queue", error=str(e))
    
    def _json_serializer(self, obj):
        """JSON serializer for datetime and UUID objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def main():
    """Main entry point for event processor"""
    processor = EventProcessor()
    
    try:
        await processor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error("Event processor crashed", error=str(e), exc_info=True)
    finally:
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())