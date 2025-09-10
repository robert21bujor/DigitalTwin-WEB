"""
Notification Service
===================

Core service for managing notifications, preferences, and subscriptions.
Handles database operations and notification delivery coordination.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import uuid

from supabase import Client
from notifications.models import (
    Notification,
    NotificationPreference, 
    NotificationSubscription,
    NotificationResponse,
    NotificationListResponse,
    DeliveryState,
    NotificationChannel,
    DigestFrequency
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and user preferences"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.delivery_queue = []  # Simple in-memory queue for now
        
    async def create_notification(self, notification: Notification) -> str:
        """Create a new notification"""
        try:
            # Convert notification to dict for database
            notification_data = {
                "id": notification.id,
                "tenant_id": notification.tenant_id,
                "recipient_user_id": notification.recipient_user_id,
                "type": notification.type,
                "title": notification.title,
                "body": notification.body,
                "metadata": notification.metadata,
                "resource_type": notification.resource_type,
                "resource_id": notification.resource_id,
                "severity": notification.severity.value,
                "channels": [channel.value for channel in notification.channels],
                "delivery_state": notification.delivery_state.value,
                "created_at": notification.created_at.isoformat(),
                "source_event_id": notification.source_event_id
            }
            
            result = self.supabase.table("notifications").insert(notification_data).execute()
            
            if result.data:
                logger.info(f"Created notification {notification.id} for user {notification.recipient_user_id}")
                return notification.id
            else:
                raise Exception("Failed to create notification")
                
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise
    
    async def get_notifications(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None
    ) -> NotificationListResponse:
        """Get notifications for a user with filtering and pagination"""
        try:
            query = self.supabase.table("notifications").select("*")
            
            # Filter by user
            query = query.eq("recipient_user_id", user_id)
            
            # Always exclude archived notifications (they shouldn't appear in normal lists)
            query = query.is_("archived_at", "null")
            
            # Filter by read status  
            if unread_only:
                query = query.in_("delivery_state", ["pending", "sent"])
            
            # Filter by type
            if notification_type:
                query = query.eq("type", notification_type)
            
            # Filter by date range
            if before:
                query = query.lt("created_at", before.isoformat())
            if after:
                query = query.gt("created_at", after.isoformat())
            
            # Order and paginate
            query = query.order("created_at", desc=True)
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            
            # Get total count and unread count
            count_query = self.supabase.table("notifications").select("id", count="exact")
            count_query = count_query.eq("recipient_user_id", user_id)
            # Always exclude archived notifications from counts
            count_query = count_query.is_("archived_at", "null")
            if unread_only:
                count_query = count_query.in_("delivery_state", ["pending", "sent"])
            
            count_result = count_query.execute()
            total_count = count_result.count or 0
            
            # Get unread count
            unread_query = self.supabase.table("notifications").select("id", count="exact")
            unread_query = unread_query.eq("recipient_user_id", user_id)
            unread_query = unread_query.in_("delivery_state", ["pending", "sent"])
            unread_query = unread_query.is_("archived_at", "null")
            unread_result = unread_query.execute()
            unread_count = unread_result.count or 0
            
            # Convert to response models
            notifications = []
            for item in result.data:
                notification = NotificationResponse(
                    id=item["id"],
                    recipient_user_id=item["recipient_user_id"],
                    type=item["type"],
                    title=item["title"],
                    body=item["body"],
                    metadata=item["metadata"] or {},
                    resource_type=item["resource_type"],
                    resource_id=item["resource_id"],
                    severity=item["severity"],
                    channels=[NotificationChannel(ch) for ch in (item["channels"] or [])],
                    delivery_state=DeliveryState(item["delivery_state"]),
                    created_at=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')),
                    read_at=datetime.fromisoformat(item["read_at"].replace('Z', '+00:00')) if item["read_at"] else None,
                    archived_at=datetime.fromisoformat(item["archived_at"].replace('Z', '+00:00')) if item["archived_at"] else None
                )
                notifications.append(notification)
            
            has_more = len(result.data) == limit and (offset + limit) < total_count
            
            return NotificationListResponse(
                notifications=notifications,
                total_count=total_count,
                unread_count=unread_count,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {e}")
            raise
    
    async def mark_as_read(self, notification_ids: List[str], user_id: str) -> int:
        """Mark notifications as read"""
        try:
            logger.info(f"Marking notifications as read: {notification_ids} for user {user_id}")
            
            # Use direct update since we have service role key
            result = self.supabase.table("notifications").update({
                "delivery_state": "read",
                "read_at": datetime.now(timezone.utc).isoformat()
            }).in_("id", notification_ids).eq("recipient_user_id", user_id).in_("delivery_state", ["pending", "sent"]).execute()
            
            updated_count = len(result.data) if result.data else 0
            logger.info(f"Successfully marked {updated_count} notifications as read for user {user_id}")
            
            # Broadcast updated unread count via WebSocket if any notifications were updated
            if updated_count > 0:
                try:
                    # Import here to avoid circular imports
                    from notifications.websocket import get_notification_broadcaster
                    broadcaster = get_notification_broadcaster()
                    
                    # Get new unread count and broadcast it
                    new_unread_count = await self.get_unread_count(user_id)
                    await broadcaster.broadcast_unread_count_update(user_id, new_unread_count)
                    logger.info(f"Broadcasted unread count update to user {user_id}: {new_unread_count}")
                except Exception as e:
                    logger.warning(f"Failed to broadcast unread count update: {e}")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error marking notifications as read: {e}")
            raise
    
    async def mark_as_archived(self, notification_ids: List[str], user_id: str) -> int:
        """Archive notifications"""
        try:
            logger.info(f"Attempting to archive notifications {notification_ids} for user {user_id}")
            
            # Simplified approach: just update without complex filtering first
            updated_count = 0
            for notification_id in notification_ids:
                try:
                    # Update each notification individually for better debugging
                    result = self.supabase.table("notifications").update({
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                        "delivery_state": "archived"
                    }).eq("id", notification_id).eq("recipient_user_id", user_id).execute()
                    
                    if result.data and len(result.data) > 0:
                        updated_count += 1
                        logger.info(f"Successfully archived notification {notification_id}")
                    else:
                        logger.warning(f"Failed to archive notification {notification_id} - no rows updated")
                        
                except Exception as e:
                    logger.error(f"Error archiving individual notification {notification_id}: {e}")
            
            logger.info(f"Total archived: {updated_count} out of {len(notification_ids)} notifications")
            
            # Broadcast updated unread count via WebSocket if any notifications were archived
            if updated_count > 0:
                try:
                    # Import here to avoid circular imports
                    from notifications.websocket import get_notification_broadcaster
                    broadcaster = get_notification_broadcaster()
                    
                    # Get new unread count and broadcast it
                    new_unread_count = await self.get_unread_count(user_id)
                    await broadcaster.broadcast_unread_count_update(user_id, new_unread_count)
                    logger.info(f"Broadcasted unread count update after archiving to user {user_id}: {new_unread_count}")
                except Exception as e:
                    logger.warning(f"Failed to broadcast unread count update after archiving: {e}")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in mark_as_archived: {e}")
            raise
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user"""
        try:
            # Use direct query for consistency with other methods
            result = self.supabase.table("notifications").select("id", count="exact").eq("recipient_user_id", user_id).in_("delivery_state", ["pending", "sent"]).is_("archived_at", "null").execute()
            return result.count or 0
            
        except Exception as e:
            logger.error(f"Error getting unread count for user {user_id}: {e}")
            return 0
    
    async def get_preferences(self, user_id: str) -> List[NotificationPreference]:
        """Get notification preferences for a user"""
        try:
            result = self.supabase.table("notification_preferences")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            preferences = []
            for item in result.data:
                preference = NotificationPreference(
                    id=item["id"],
                    tenant_id=item["tenant_id"],
                    user_id=item["user_id"],
                    notification_type=item["notification_type"],
                    channel=NotificationChannel(item["channel"]),
                    enabled=item["enabled"],
                    quiet_hours=item["quiet_hours"],
                    frequency=DigestFrequency(item["frequency"]),
                    created_at=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(item["updated_at"].replace('Z', '+00:00'))
                )
                preferences.append(preference)
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            raise
    
    async def update_preference(
        self, 
        user_id: str, 
        notification_type: str, 
        channel: NotificationChannel,
        enabled: bool,
        quiet_hours: Optional[Dict[str, Any]] = None,
        frequency: DigestFrequency = DigestFrequency.REALTIME
    ) -> bool:
        """Update or create a notification preference"""
        try:
            preference_data = {
                "user_id": user_id,
                "notification_type": notification_type,
                "channel": channel.value,
                "enabled": enabled,
                "quiet_hours": quiet_hours,
                "frequency": frequency.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Use upsert to update or create
            result = self.supabase.table("notification_preferences")\
                .upsert(preference_data, on_conflict="user_id,notification_type,channel")\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating preference for user {user_id}: {e}")
            raise
    
    async def get_subscriptions(self, user_id: str) -> List[NotificationSubscription]:
        """Get notification subscriptions for a user"""
        try:
            result = self.supabase.table("notification_subscriptions")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            subscriptions = []
            for item in result.data:
                subscription = NotificationSubscription(
                    id=item["id"],
                    tenant_id=item["tenant_id"],
                    user_id=item["user_id"],
                    resource_type=item["resource_type"],
                    resource_id=item["resource_id"],
                    notify_on=item["notify_on"] or [],
                    created_at=datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
                )
                subscriptions.append(subscription)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error getting subscriptions for user {user_id}: {e}")
            raise
    
    async def create_subscription(
        self, 
        user_id: str, 
        resource_type: str, 
        resource_id: str,
        notify_on: List[str]
    ) -> str:
        """Create a notification subscription"""
        try:
            subscription_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "notify_on": notify_on,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("notification_subscriptions")\
                .upsert(subscription_data, on_conflict="user_id,resource_type,resource_id")\
                .execute()
            
            if result.data:
                return subscription_data["id"]
            else:
                raise Exception("Failed to create subscription")
                
        except Exception as e:
            logger.error(f"Error creating subscription for user {user_id}: {e}")
            raise
    
    async def delete_subscription(self, subscription_id: str, user_id: str) -> bool:
        """Delete a notification subscription"""
        try:
            result = self.supabase.table("notification_subscriptions")\
                .delete()\
                .eq("id", subscription_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            raise
    
    async def queue_for_delivery(self, notification: Notification):
        """Queue notification for delivery"""
        # Simple in-memory queue for now
        # In production, this would use Redis or another queue system
        self.delivery_queue.append(notification)
        logger.debug(f"Queued notification {notification.id} for delivery")
    
    async def process_delivery_queue(self):
        """Process pending notifications for delivery"""
        # This would be called by a background task
        while self.delivery_queue:
            notification = self.delivery_queue.pop(0)
            await self._deliver_notification(notification)
    
    async def _deliver_notification(self, notification: Notification):
        """Deliver a notification through configured channels"""
        try:
            # Get user preferences
            preferences = await self.get_preferences(notification.recipient_user_id)
            
            # Check if user wants this type of notification
            relevant_prefs = [
                p for p in preferences 
                if p.notification_type == notification.type or p.notification_type == "*"
            ]
            
            if not relevant_prefs:
                # No preferences found, use defaults
                await self._deliver_in_app(notification)
                return
            
            # Deliver through enabled channels
            for pref in relevant_prefs:
                if not pref.enabled:
                    continue
                    
                # Check quiet hours
                if self._is_quiet_hours(pref) and notification.severity.value != "critical":
                    continue
                
                if pref.channel == NotificationChannel.IN_APP:
                    await self._deliver_in_app(notification)
                elif pref.channel == NotificationChannel.EMAIL:
                    await self._deliver_email(notification, pref)
                elif pref.channel == NotificationChannel.PUSH:
                    await self._deliver_push(notification)
            
            # Update delivery state
            await self._update_delivery_state(notification.id, DeliveryState.SENT)
            
        except Exception as e:
            logger.error(f"Error delivering notification {notification.id}: {e}")
            await self._update_delivery_state(notification.id, DeliveryState.FAILED)
    
    async def _deliver_in_app(self, notification: Notification):
        """Deliver in-app notification (already stored in database)"""
        try:
            # Import here to avoid circular imports
            from notifications.websocket import get_notification_broadcaster
            from notifications.models import NotificationResponse
            
            broadcaster = get_notification_broadcaster()
            
            # Convert to response format
            notification_response = NotificationResponse(
                id=notification.id,
                recipient_user_id=notification.recipient_user_id,
                type=notification.type,
                title=notification.title,
                body=notification.body,
                severity=notification.severity,
                channels=notification.channels,
                created_at=notification.created_at,
                delivery_state=notification.delivery_state,
                metadata=notification.metadata,
                resource_type=notification.resource_type,
                resource_id=notification.resource_id,
                read_at=None,  # New notifications are unread
                archived_at=None  # New notifications are not archived
            )
            
            # Broadcast new notification via WebSocket
            await broadcaster.broadcast_notification(notification.recipient_user_id, notification_response)
            
            # Also broadcast updated unread count
            new_unread_count = await self.get_unread_count(notification.recipient_user_id)
            await broadcaster.broadcast_unread_count_update(notification.recipient_user_id, new_unread_count)
            
            logger.info(f"In-app notification delivered via WebSocket: {notification.id} to user {notification.recipient_user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to broadcast new notification via WebSocket: {e}")
            # Don't fail the whole delivery if WebSocket fails
            logger.debug(f"In-app notification delivered (WebSocket failed): {notification.id}")
    
    async def _deliver_email(self, notification: Notification, preference: NotificationPreference):
        """Deliver email notification"""
        # TODO: Implement email delivery
        # This would integrate with an email service like SendGrid, SES, etc.
        if preference.frequency == DigestFrequency.REALTIME:
            logger.debug(f"Would send immediate email for notification: {notification.id}")
        else:
            logger.debug(f"Queued for {preference.frequency.value} digest: {notification.id}")
    
    async def _deliver_push(self, notification: Notification):
        """Deliver push notification"""
        # TODO: Implement push notification delivery
        # This would integrate with FCM, APNs, etc.
        logger.debug(f"Would send push notification: {notification.id}")
    
    def _is_quiet_hours(self, preference: NotificationPreference) -> bool:
        """Check if current time is within user's quiet hours"""
        if not preference.quiet_hours:
            return False
        
        # TODO: Implement quiet hours logic
        # This would check the current time against the user's timezone and quiet hours
        return False
    
    async def _update_delivery_state(self, notification_id: str, state: DeliveryState):
        """Update notification delivery state"""
        try:
            update_data = {"delivery_state": state.value}
            if state == DeliveryState.READ:
                update_data["read_at"] = datetime.now(timezone.utc).isoformat()
            
            self.supabase.table("notifications")\
                .update(update_data)\
                .eq("id", notification_id)\
                .execute()
                
        except Exception as e:
            logger.error(f"Error updating delivery state for {notification_id}: {e}")


# Global service instance
_notification_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    global _notification_service_instance
    if _notification_service_instance is None:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from Utils.config import Config
        from supabase import create_client
        
        # Initialize Supabase client
        supabase_config = Config.get_supabase_config()
        service_key = supabase_config.get("service_role_key") or supabase_config["key"]
        supabase_client = create_client(supabase_config["url"], service_key)
        
        _notification_service_instance = NotificationService(supabase_client)
    
    return _notification_service_instance
