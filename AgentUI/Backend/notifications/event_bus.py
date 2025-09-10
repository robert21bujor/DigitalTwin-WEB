"""
Notification Event Bus and Processing
=====================================

Handles the publication and processing of notification events.
Supports both in-memory processing and Redis queue for scalability.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
import threading
from queue import Queue
from contextlib import asynccontextmanager

from notifications.models import (
    NotificationEvent, 
    Notification, 
    NotificationSeverity, 
    NotificationChannel,
    DeliveryState
)
from notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for handling notification events.
    Supports both synchronous and asynchronous event processing.
    """
    
    def __init__(self, notification_service: NotificationService, use_redis: bool = False):
        self.notification_service = notification_service
        self.use_redis = use_redis
        self._event_queue = Queue()
        self._processing = False
        self._worker_thread = None
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._processed_events: Set[str] = set()  # For idempotency
        
    async def emit_event(
        self, 
        event_key: str, 
        payload: Dict[str, Any], 
        actor_id: str, 
        tenant_id: Optional[str] = None,
        source_event_id: Optional[str] = None
    ) -> str:
        """
        Emit a notification event for processing.
        
        Args:
            event_key: Type of event (e.g., 'chat.message.created')
            payload: Event data
            actor_id: User who triggered the event
            tenant_id: Tenant identifier (for multi-tenant setups)
            source_event_id: Unique event identifier (auto-generated if not provided)
            
        Returns:
            source_event_id: The unique identifier for this event
        """
        if not source_event_id:
            source_event_id = f"{event_key}_{actor_id}_{uuid.uuid4()}"
            
        # Check for duplicate events (idempotency)
        if source_event_id in self._processed_events:
            logger.warning(f"Event {source_event_id} already processed, skipping")
            return source_event_id
            
        event = NotificationEvent(
            event_key=event_key,
            payload=payload,
            actor_id=actor_id,
            tenant_id=tenant_id,
            source_event_id=source_event_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        if self.use_redis:
            await self._publish_to_redis(event)
        else:
            await self._publish_to_queue(event)
            
        logger.info(f"Event emitted: {event_key} (ID: {source_event_id})")
        return source_event_id
    
    async def _publish_to_queue(self, event: NotificationEvent):
        """Publish event to in-memory queue"""
        self._event_queue.put(event)
        
        # Start worker thread if not already running
        if not self._processing:
            await self._start_processing()
    
    async def _publish_to_redis(self, event: NotificationEvent):
        """Publish event to Redis queue (future implementation)"""
        # TODO: Implement Redis queue support
        logger.warning("Redis queue not implemented yet, falling back to in-memory queue")
        await self._publish_to_queue(event)
    
    async def _start_processing(self):
        """Start the event processing worker"""
        if self._processing:
            return
            
        self._processing = True
        self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self._worker_thread.start()
        logger.info("Event processing started")
    
    def _process_events(self):
        """Background thread to process events"""
        while self._processing:
            try:
                if not self._event_queue.empty():
                    event = self._event_queue.get(timeout=1)
                    asyncio.run(self._process_single_event(event))
                else:
                    # Sleep briefly when queue is empty
                    threading.Event().wait(0.1)
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _process_single_event(self, event: NotificationEvent):
        """Process a single notification event"""
        try:
            # Mark as processed for idempotency
            self._processed_events.add(event.source_event_id)
            
            # Get event processor
            processor = NotificationEventProcessor(self.notification_service)
            
            # Process the event
            await processor.process_event(event)
            
            # Clean up old processed events (keep last 1000)
            if len(self._processed_events) > 1000:
                # Remove oldest entries (simplified approach)
                self._processed_events = set(list(self._processed_events)[-800:])
                
        except Exception as e:
            logger.error(f"Failed to process event {event.source_event_id}: {e}")
    
    async def stop_processing(self):
        """Stop the event processing worker"""
        self._processing = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("Event processing stopped")


class NotificationEventProcessor:
    """
    Processes notification events and creates notifications for users.
    Handles recipient resolution, templating, aggregation, and deduplication.
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.event_templates = self._load_event_templates()
        
    async def process_event(self, event: NotificationEvent):
        """Process a notification event and create notifications"""
        try:
            # Get event configuration
            event_config = self._get_event_config(event.event_key)
            if not event_config:
                logger.warning(f"No configuration found for event: {event.event_key}")
                return
            
            # Resolve recipients
            recipients = await self._resolve_recipients(event, event_config)
            if not recipients:
                logger.debug(f"No recipients found for event: {event.event_key}")
                return
            
            # Create notifications for each recipient
            for recipient_id in recipients:
                await self._create_notification_for_recipient(
                    event, event_config, recipient_id
                )
                
        except Exception as e:
            logger.error(f"Error processing event {event.event_key}: {e}")
    
    def _get_event_config(self, event_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an event type"""
        # This would typically come from a configuration file or database
        # For now, we'll use hardcoded configurations based on our catalog
        
        event_configs = {
            "chat.message.created": {
                "title_template": "New message from {sender_name}",
                "body_template": "{message_preview}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["conversation_participants"],
                "aggregation_key": "conversation_id",
                "aggregation_window": 300,  # 5 minutes
            },
            "chat.agent.response": {
                "title_template": "{agent_name} responded",
                "body_template": "{response_preview}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["message_sender"],
                "aggregation_key": None,  # No aggregation
            },
            "chat.conversation.created": {
                "title_template": "New conversation started",
                "body_template": "Conversation with {agent_name} started",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["conversation_participants"],
            },
            "agent.task.completed": {
                "title_template": "Task completed",
                "body_template": "{agent_name} completed: {task_title}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                "recipients": ["task_assignee", "task_watchers"],
            },
            "agent.task.failed": {
                "title_template": "Task failed",
                "body_template": "{agent_name} failed to complete: {task_title}",
                "severity": NotificationSeverity.WARN,
                "default_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                "recipients": ["task_assignee", "admins"],
            },
            "task.assigned": {
                "title_template": "Task assigned",
                "body_template": "You have been assigned: {task_title}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                "recipients": ["task_assignee"],
            },
            "task.due.soon": {
                "title_template": "Task due soon",
                "body_template": "{task_title} is due in {time_until_due}",
                "severity": NotificationSeverity.WARN,
                "default_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                "recipients": ["task_assignee", "task_watchers"],
                "bypass_quiet_hours": True,
            },
            "task.overdue": {
                "title_template": "Task overdue",
                "body_template": "{task_title} is {overdue_by} overdue",
                "severity": NotificationSeverity.CRITICAL,
                "default_channels": [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                "recipients": ["task_assignee", "task_manager", "task_watchers"],
                "bypass_quiet_hours": True,
            },
            "auth.user.login": {
                "title_template": "Login detected",
                "body_template": "Login from {ip_address} at {login_time}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["user_self"],
                "aggregation_key": "user_id",
                "aggregation_window": 86400,  # 24 hours
            },
            "system.gmail.sync.completed": {
                "title_template": "Gmail sync completed",
                "body_template": "Synced {email_count} emails in {sync_duration}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["sync_initiator"],
                "aggregation_key": "user_id",
                "aggregation_window": 3600,  # 1 hour
            },
            "integration.clickup.upload.success": {
                "title_template": "File uploaded to ClickUp",
                "body_template": "Successfully uploaded {filename}",
                "severity": NotificationSeverity.INFO,
                "default_channels": [NotificationChannel.IN_APP],
                "recipients": ["uploader"],
                "aggregation_key": "user_id",
                "aggregation_window": 300,  # 5 minutes
            },
        }
        
        return event_configs.get(event_key)
    
    async def _resolve_recipients(self, event: NotificationEvent, config: Dict[str, Any]) -> List[str]:
        """Resolve recipient user IDs for an event"""
        recipients = set()
        payload = event.payload
        
        for recipient_type in config.get("recipients", []):
            if recipient_type == "conversation_participants":
                # Get participants from conversation
                conversation_id = payload.get("conversation_id")
                if conversation_id:
                    participants = await self._get_conversation_participants(conversation_id)
                    recipients.update(participants)
                    
            elif recipient_type == "message_sender":
                sender_id = payload.get("sender_id")
                if sender_id:
                    recipients.add(sender_id)
                    
            elif recipient_type == "task_assignee":
                assignee_id = payload.get("assignee_id") or payload.get("user_id")
                if assignee_id:
                    recipients.add(assignee_id)
                    
            elif recipient_type == "task_watchers":
                watchers = payload.get("watchers", [])
                recipients.update(watchers)
                
            elif recipient_type == "admins":
                admin_users = await self._get_admin_users()
                recipients.update(admin_users)
                
            elif recipient_type == "user_self":
                user_id = payload.get("user_id") or event.actor_id
                if user_id:
                    recipients.add(user_id)
                    
            elif recipient_type == "sync_initiator" or recipient_type == "uploader":
                initiator_id = payload.get("user_id") or event.actor_id
                if initiator_id:
                    recipients.add(initiator_id)
        
        # Remove the actor from recipients if they triggered the event
        # (usually people don't want notifications for their own actions)
        if event.actor_id in recipients and len(recipients) > 1:
            recipients.discard(event.actor_id)
            
        return list(recipients)
    
    async def _create_notification_for_recipient(
        self, 
        event: NotificationEvent, 
        config: Dict[str, Any], 
        recipient_id: str
    ):
        """Create a notification for a specific recipient"""
        try:
            # Render notification content
            title = self._render_template(config["title_template"], event.payload)
            body = self._render_template(config["body_template"], event.payload)
            
            # Create notification
            notification = Notification(
                recipient_user_id=recipient_id,
                type=event.event_key,
                title=title,
                body=body,
                metadata=event.payload,
                resource_type=event.payload.get("resource_type"),
                resource_id=event.payload.get("resource_id"),
                severity=config.get("severity", NotificationSeverity.INFO),
                channels=config.get("default_channels", [NotificationChannel.IN_APP]),
                source_event_id=event.source_event_id,
                created_at=event.timestamp
            )
            
            # Save notification
            await self.notification_service.create_notification(notification)
            
            # Queue for delivery
            await self.notification_service.queue_for_delivery(notification)
            
            # Process delivery immediately for real-time WebSocket broadcasting
            await self.notification_service._deliver_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to create notification for recipient {recipient_id}: {e}")
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a notification template with variables"""
        try:
            # Simple string formatting - could be enhanced with Jinja2
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return template
    
    async def _get_conversation_participants(self, conversation_id: str) -> List[str]:
        """Get participant IDs for a conversation"""
        # This would query the conversations table
        # For now, return empty list
        return []
    
    async def _get_admin_users(self) -> List[str]:
        """Get list of admin user IDs"""
        # This would query the user_profiles table for admin users
        # For now, return empty list
        return []
    
    def _load_event_templates(self) -> Dict[str, Dict[str, str]]:
        """Load notification templates"""
        # This could be loaded from files or database
        return {}


# Global event bus instance
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus_instance
    if _event_bus_instance is None:
        from notifications.notification_service import get_notification_service
        notification_service = get_notification_service()
        _event_bus_instance = EventBus(notification_service)
    return _event_bus_instance


# Convenience function for emitting events
async def emit_notification_event(
    event_key: str,
    payload: Dict[str, Any],
    actor_id: str,
    tenant_id: Optional[str] = None,
    source_event_id: Optional[str] = None
) -> str:
    """
    Convenience function to emit a notification event.
    
    Usage:
        await emit_notification_event(
            "chat.message.created",
            {
                "sender_name": "John Doe",
                "message_preview": "Hello, how are you?",
                "conversation_id": "conv_123",
                "agent_name": "Assistant"
            },
            actor_id="user_123"
        )
    """
    event_bus = get_event_bus()
    return await event_bus.emit_event(
        event_key, payload, actor_id, tenant_id, source_event_id
    )
