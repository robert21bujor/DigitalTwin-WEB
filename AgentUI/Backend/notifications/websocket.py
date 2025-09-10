"""
WebSocket Support for Real-time Notifications
=============================================

Provides WebSocket endpoints for real-time notification delivery.
Handles user connections, authentication, and message broadcasting.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
import uuid
import weakref

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.routing import APIRouter

from notifications.models import WebSocketMessage, NotificationResponse
from notifications.notification_service import get_notification_service, NotificationService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Use WeakSet to automatically clean up closed connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = weakref.WeakKeyDictionary()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Add to user's connection set
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc)
        }
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send connection acknowledgment
        await self.send_personal_message(
            user_id, 
            WebSocketMessage(
                type="connection_ack",
                data={"message": "Connected to notifications"}
            )
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        metadata = self.connection_metadata.get(websocket)
        if metadata:
            user_id = metadata["user_id"]
            
            # Remove from user's connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty connection sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, user_id: str, message: WebSocketMessage):
        """Send a message to all connections for a specific user"""
        if user_id not in self.active_connections:
            return
        
        # Use model_dump with custom JSON encoder to handle datetime serialization
        message_json = message.model_dump_json()
        disconnected_connections = set()
        
        for websocket in self.active_connections[user_id].copy():
            try:
                # Check if WebSocket is still in a valid state before sending
                if hasattr(websocket, 'client_state') and websocket.client_state.name == 'DISCONNECTED':
                    logger.debug(f"Skipping disconnected WebSocket for user {user_id}")
                    disconnected_connections.add(websocket)
                    continue
                    
                await websocket.send_text(message_json)
            except Exception as e:
                # Log at debug level instead of warning to reduce noise for expected disconnections
                logger.debug(f"Failed to send message to user {user_id}: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket)
    
    async def send_notification(self, user_id: str, notification: NotificationResponse):
        """Send a notification to a user via WebSocket"""
        message = WebSocketMessage(
            type="notification",
            data={
                "notification": notification.dict(),
                "unread_count_delta": 1
            }
        )
        await self.send_personal_message(user_id, message)
    
    async def send_unread_count_update(self, user_id: str, unread_count: int):
        """Send unread count update to a user"""
        message = WebSocketMessage(
            type="unread_count",
            data={"unread_count": unread_count}
        )
        await self.send_personal_message(user_id, message)
    
    def get_connected_users(self) -> Set[str]:
        """Get set of currently connected user IDs"""
        return set(self.active_connections.keys())
    
    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))
    
    async def cleanup_stale_connections(self):
        """Remove stale/disconnected WebSocket connections"""
        stale_connections = []
        
        for user_id, connections in list(self.active_connections.items()):
            for websocket in list(connections):
                try:
                    # Check if WebSocket is in a disconnected state
                    if hasattr(websocket, 'client_state') and websocket.client_state.name == 'DISCONNECTED':
                        stale_connections.append((user_id, websocket))
                        logger.debug(f"Found stale connection for user {user_id}")
                except Exception as e:
                    # If we can't check state, consider it stale
                    stale_connections.append((user_id, websocket))
                    logger.debug(f"Found problematic connection for user {user_id}: {e}")
        
        # Clean up stale connections
        for user_id, websocket in stale_connections:
            self.disconnect(websocket)
            logger.debug(f"Cleaned up stale connection for user {user_id}")

    async def ping_all_connections(self):
        """Send ping to all connections to keep them alive"""
        # First clean up any stale connections
        await self.cleanup_stale_connections()
        
        ping_message = WebSocketMessage(
            type="ping",
            data={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        for user_id in list(self.active_connections.keys()):
            try:
                await self.send_personal_message(user_id, ping_message)
            except Exception as e:
                logger.debug(f"Failed to ping user {user_id}: {e}")


# Global connection manager
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return connection_manager


# Create router for WebSocket endpoints
ws_router = APIRouter()


async def authenticate_websocket(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
) -> str:
    """
    Authenticate WebSocket connection.
    In production, this would validate JWT tokens or session data.
    """
    if not user_id:
        await websocket.close(code=4001, reason="User ID required")
        raise HTTPException(status_code=401, detail="User ID required")
    
    # In production, validate the token here
    # For now, we'll accept any user_id
    return user_id


@ws_router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    user_id: str = Depends(authenticate_websocket),
    service: NotificationService = Depends(get_notification_service)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Query parameters:
    - user_id: User identifier
    - token: Authentication token (optional, for future use)
    
    Message types sent to client:
    - connection_ack: Connection established
    - notification: New notification received
    - unread_count: Updated unread count
    - ping: Keep-alive ping
    """
    await connection_manager.connect(websocket, user_id)
    
    try:
        # Send initial unread count
        unread_count = await service.get_unread_count(user_id)
        await connection_manager.send_unread_count_update(user_id, unread_count)
        
        # Send recent notifications (last 20)
        recent_notifications = await service.get_notifications(
            user_id=user_id,
            limit=20,
            unread_only=False
        )
        
        if recent_notifications.notifications:
            message = WebSocketMessage(
                type="initial_notifications",
                data={
                    "notifications": [n.dict() for n in recent_notifications.notifications],
                    "total_count": recent_notifications.total_count,
                    "unread_count": recent_notifications.unread_count
                }
            )
            await connection_manager.send_personal_message(user_id, message)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for incoming messages (like ping responses)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle incoming messages
                try:
                    message = json.loads(data)
                    await handle_websocket_message(websocket, user_id, message, service)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from user {user_id}")
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                ping_message = WebSocketMessage(
                    type="ping",
                    data={"timestamp": datetime.now(timezone.utc).isoformat()}
                )
                await connection_manager.send_personal_message(user_id, ping_message)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        connection_manager.disconnect(websocket)


async def handle_websocket_message(
    websocket: WebSocket,
    user_id: str,
    message: Dict[str, Any],
    service: NotificationService
):
    """Handle incoming WebSocket messages from clients"""
    try:
        message_type = message.get("type")
        
        if message_type == "pong":
            # Update last ping time
            metadata = connection_manager.connection_metadata.get(websocket)
            if metadata:
                metadata["last_ping"] = datetime.now(timezone.utc)
        
        elif message_type == "mark_read":
            # Mark notifications as read
            notification_ids = message.get("data", {}).get("notification_ids", [])
            if notification_ids:
                await service.mark_as_read(notification_ids, user_id)
                
                # Send updated unread count
                unread_count = await service.get_unread_count(user_id)
                await connection_manager.send_unread_count_update(user_id, unread_count)
        
        elif message_type == "get_unread_count":
            # Send current unread count
            unread_count = await service.get_unread_count(user_id)
            await connection_manager.send_unread_count_update(user_id, unread_count)
        
        elif message_type == "subscribe":
            # Subscribe to notifications for a specific resource
            resource_type = message.get("data", {}).get("resource_type")
            resource_id = message.get("data", {}).get("resource_id")
            notify_on = message.get("data", {}).get("notify_on", [])
            
            if resource_type and resource_id:
                await service.create_subscription(user_id, resource_type, resource_id, notify_on)
                
                response = WebSocketMessage(
                    type="subscription_created",
                    data={"resource_type": resource_type, "resource_id": resource_id}
                )
                await connection_manager.send_personal_message(user_id, response)
        
        else:
            logger.warning(f"Unknown message type '{message_type}' from user {user_id}")
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message from user {user_id}: {e}")


class NotificationBroadcaster:
    """Service for broadcasting notifications to connected WebSocket clients"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def broadcast_notification(self, user_id: str, notification: NotificationResponse):
        """Broadcast a new notification to user's WebSocket connections"""
        if user_id in self.connection_manager.active_connections:
            await self.connection_manager.send_notification(user_id, notification)
    
    async def broadcast_unread_count_update(self, user_id: str, unread_count: int):
        """Broadcast unread count update to user's WebSocket connections"""
        if user_id in self.connection_manager.active_connections:
            await self.connection_manager.send_unread_count_update(user_id, unread_count)
    
    def get_online_users(self) -> Set[str]:
        """Get set of currently online user IDs"""
        return self.connection_manager.get_connected_users()


# Global broadcaster instance
_broadcaster_instance: Optional[NotificationBroadcaster] = None


def get_notification_broadcaster() -> NotificationBroadcaster:
    """Get the global notification broadcaster instance"""
    global _broadcaster_instance
    if _broadcaster_instance is None:
        _broadcaster_instance = NotificationBroadcaster(connection_manager)
    return _broadcaster_instance


# Background task to keep connections alive
async def websocket_keepalive_task():
    """Background task to ping all WebSocket connections periodically"""
    while True:
        try:
            await connection_manager.ping_all_connections()
            await asyncio.sleep(30)  # Ping every 30 seconds
        except Exception as e:
            logger.error(f"Error in WebSocket keepalive task: {e}")
            await asyncio.sleep(30)


# Export the router and manager
__all__ = ["ws_router", "get_connection_manager", "get_notification_broadcaster", "websocket_keepalive_task"]
