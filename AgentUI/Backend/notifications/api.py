"""
Notification API Endpoints
==========================

REST API endpoints for the notification system.
Provides endpoints for managing notifications, preferences, and subscriptions.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse

from notifications.models import (
    CreateNotificationRequest,
    NotificationResponse,
    NotificationListResponse,
    UpdateNotificationPreferenceRequest,
    NotificationPreferenceResponse,
    CreateSubscriptionRequest,
    NotificationSubscriptionResponse,
    NotificationChannel,
    DigestFrequency
)
from notifications.notification_service import get_notification_service, NotificationService

logger = logging.getLogger(__name__)

# Create router for notification endpoints
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def get_current_user_id(request: Request) -> str:
    """
    Extract user ID from request.
    In a real application, this would validate JWT tokens or session data.
    For now, we'll expect the user_id to be passed in headers or query params.
    """
    # Try to get user_id from headers first
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        # Try to get from query params
        user_id = request.query_params.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    return user_id


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    before: Optional[str] = Query(None),  # ISO datetime string
    after: Optional[str] = Query(None),   # ISO datetime string
    service: NotificationService = Depends(get_notification_service)
):
    """
    Get notifications for the current user with filtering and pagination.
    
    Query Parameters:
    - limit: Number of notifications to return (max 100)
    - offset: Number of notifications to skip
    - unread_only: Only return unread notifications
    - notification_type: Filter by notification type
    - before: Get notifications before this datetime (ISO format)
    - after: Get notifications after this datetime (ISO format)
    """
    try:
        user_id = get_current_user_id(request)
        
        # Parse datetime strings
        before_dt = None
        after_dt = None
        if before:
            try:
                before_dt = datetime.fromisoformat(before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'before' datetime format")
        
        if after:
            try:
                after_dt = datetime.fromisoformat(after.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'after' datetime format")
        
        # Get notifications
        result = await service.get_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            notification_type=notification_type,
            before=before_dt,
            after=after_dt
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@router.post("/read")
async def mark_notifications_read(
    request: Request,
    notification_ids: List[str],
    service: NotificationService = Depends(get_notification_service)
):
    """
    Mark multiple notifications as read.
    
    Body:
    - notification_ids: List of notification IDs to mark as read
    """
    try:
        user_id = get_current_user_id(request)
        
        if not notification_ids:
            raise HTTPException(status_code=400, detail="notification_ids is required")
        
        updated_count = await service.mark_as_read(notification_ids, user_id)
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Marked {updated_count} notifications as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Mark a single notification as read"""
    try:
        user_id = get_current_user_id(request)
        
        updated_count = await service.mark_as_read([notification_id], user_id)
        
        if updated_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found or already read")
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")


@router.post("/{notification_id}/archive")
async def archive_notification(
    notification_id: str,
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Archive a single notification"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Archive request: notification_id={notification_id}, user_id={user_id}")
        
        updated_count = await service.mark_as_archived([notification_id], user_id)
        
        if updated_count == 0:
            logger.warning(f"Archive failed: no notifications updated for {notification_id} and user {user_id}")
            raise HTTPException(status_code=404, detail="Notification not found")
        
        logger.info(f"Archive successful: {updated_count} notifications archived")
        return {
            "success": True,
            "message": "Notification archived"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive notification")


@router.get("/unread-count")
async def get_unread_count(
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Get the count of unread notifications for the current user"""
    try:
        user_id = get_current_user_id(request)
        
        unread_count = await service.get_unread_count(user_id)
        
        return {
            "unread_count": unread_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail="Failed to get unread count")


@router.get("/preferences")
async def get_notification_preferences(
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Get notification preferences for the current user"""
    try:
        user_id = get_current_user_id(request)
        
        preferences = await service.get_preferences(user_id)
        
        # Convert to response format
        preference_responses = []
        for pref in preferences:
            response = NotificationPreferenceResponse(
                id=pref.id,
                user_id=pref.user_id,
                notification_type=pref.notification_type,
                channel=pref.channel,
                enabled=pref.enabled,
                quiet_hours=pref.quiet_hours,
                frequency=pref.frequency
            )
            preference_responses.append(response)
        
        return {
            "preferences": preference_responses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get preferences")


@router.put("/preferences")
async def update_notification_preference(
    request: Request,
    preference_update: UpdateNotificationPreferenceRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """Update a notification preference for the current user"""
    try:
        user_id = get_current_user_id(request)
        
        success = await service.update_preference(
            user_id=user_id,
            notification_type=preference_update.notification_type,
            channel=preference_update.channel,
            enabled=preference_update.enabled,
            quiet_hours=preference_update.quiet_hours,
            frequency=preference_update.frequency
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preference")
        
        return {
            "success": True,
            "message": "Preference updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preference: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preference")


@router.get("/subscriptions")
async def get_notification_subscriptions(
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Get notification subscriptions for the current user"""
    try:
        user_id = get_current_user_id(request)
        
        subscriptions = await service.get_subscriptions(user_id)
        
        # Convert to response format
        subscription_responses = []
        for sub in subscriptions:
            response = NotificationSubscriptionResponse(
                id=sub.id,
                user_id=sub.user_id,
                resource_type=sub.resource_type,
                resource_id=sub.resource_id,
                notify_on=sub.notify_on,
                created_at=sub.created_at
            )
            subscription_responses.append(response)
        
        return {
            "subscriptions": subscription_responses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscriptions")


@router.post("/subscriptions")
async def create_notification_subscription(
    request: Request,
    subscription_request: CreateSubscriptionRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """Create a notification subscription for the current user"""
    try:
        user_id = get_current_user_id(request)
        
        subscription_id = await service.create_subscription(
            user_id=user_id,
            resource_type=subscription_request.resource_type,
            resource_id=subscription_request.resource_id,
            notify_on=subscription_request.notify_on
        )
        
        return {
            "success": True,
            "subscription_id": subscription_id,
            "message": "Subscription created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.delete("/subscriptions/{subscription_id}")
async def delete_notification_subscription(
    subscription_id: str,
    request: Request,
    service: NotificationService = Depends(get_notification_service)
):
    """Delete a notification subscription"""
    try:
        user_id = get_current_user_id(request)
        
        success = await service.delete_subscription(subscription_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {
            "success": True,
            "message": "Subscription deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete subscription")


# Admin endpoints (would require admin authentication in production)
@router.post("/admin/create", response_model=Dict[str, Any])
async def create_notification_admin(
    notification_request: CreateNotificationRequest,
    service: NotificationService = Depends(get_notification_service)
):
    """
    Admin endpoint to create notifications directly.
    This would typically be used by backend services.
    """
    try:
        from notifications.models import Notification, NotificationSeverity, NotificationChannel
        
        # Create notification object
        notification = Notification(
            recipient_user_id=notification_request.recipient_user_id,
            type=notification_request.type,
            title=notification_request.title,
            body=notification_request.body,
            metadata=notification_request.metadata,
            resource_type=notification_request.resource_type,
            resource_id=notification_request.resource_id,
            severity=notification_request.severity,
            channels=notification_request.channels,
            source_event_id=notification_request.source_event_id
        )
        
        # Create in database
        notification_id = await service.create_notification(notification)
        
        # Queue for delivery
        await service.queue_for_delivery(notification)
        
        # Process delivery immediately (for real-time WebSocket broadcasting)
        await service._deliver_notification(notification)
        
        return {
            "success": True,
            "notification_id": notification_id,
            "message": "Notification created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to create notification")


@router.get("/admin/stats")
async def get_notification_stats(
    days: int = Query(7, ge=1, le=30),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Admin endpoint to get notification statistics.
    This would require admin authentication in production.
    """
    try:
        # This is a placeholder - would implement actual stats queries
        return {
            "total_notifications": 0,
            "notifications_by_type": {},
            "delivery_stats": {
                "sent": 0,
                "failed": 0,
                "pending": 0
            },
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification stats")


# Health check endpoint
@router.get("/health")
async def notification_health_check():
    """Health check endpoint for the notification system"""
    try:
        # Basic health check - could be enhanced to check database connectivity
        return {
            "status": "healthy",
            "service": "notifications",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


# Export the router
__all__ = ["router"]
