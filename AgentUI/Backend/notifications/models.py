"""
Notification System Models
==========================

Database models for the notification system using Supabase (PostgreSQL).
These models define the structure for notifications, user preferences, and subscriptions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class NotificationSeverity(str, Enum):
    """Notification severity levels"""
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Available notification delivery channels"""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class DeliveryState(str, Enum):
    """Notification delivery state"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"
    ARCHIVED = "archived"


class DigestFrequency(str, Enum):
    """Notification digest frequency options"""
    REALTIME = "realtime"
    HOURLY_DIGEST = "hourly_digest"
    DAILY_DIGEST = "daily_digest"


class Notification(BaseModel):
    """Core notification model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None  # For multi-tenant support
    recipient_user_id: str
    type: str  # event_key like 'chat.message.created'
    title: str
    body: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    resource_type: Optional[str] = None  # e.g., 'conversation', 'task', 'agent'
    resource_id: Optional[str] = None
    severity: NotificationSeverity = NotificationSeverity.INFO
    channels: List[NotificationChannel] = Field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    source_event_id: str  # For idempotency - must be unique
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationPreference(BaseModel):
    """User notification preferences"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    user_id: str
    notification_type: str  # event_key or '*' for all
    channel: NotificationChannel
    enabled: bool = True
    quiet_hours: Optional[Dict[str, Any]] = None  # {tz, start_hour, end_hour}
    frequency: DigestFrequency = DigestFrequency.REALTIME
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationSubscription(BaseModel):
    """User subscriptions to specific resources for notifications"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    user_id: str
    resource_type: str  # e.g., 'conversation', 'task', 'agent'
    resource_id: str
    notify_on: List[str] = Field(default_factory=list)  # List of event types
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# API Request/Response Models

class CreateNotificationRequest(BaseModel):
    """Request model for creating notifications"""
    recipient_user_id: str
    type: str
    title: str
    body: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    severity: NotificationSeverity = NotificationSeverity.INFO
    channels: List[NotificationChannel] = Field(default_factory=list)
    source_event_id: str


class NotificationResponse(BaseModel):
    """Response model for notification data"""
    id: str
    recipient_user_id: str
    type: str
    title: str
    body: str
    metadata: Dict[str, Any]
    resource_type: Optional[str]
    resource_id: Optional[str]
    severity: NotificationSeverity
    channels: List[NotificationChannel]
    delivery_state: DeliveryState
    created_at: datetime
    read_at: Optional[datetime]
    archived_at: Optional[datetime]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationListResponse(BaseModel):
    """Response model for notification lists"""
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    has_more: bool


class UpdateNotificationPreferenceRequest(BaseModel):
    """Request model for updating notification preferences"""
    notification_type: str
    channel: NotificationChannel
    enabled: bool
    quiet_hours: Optional[Dict[str, Any]] = None
    frequency: DigestFrequency = DigestFrequency.REALTIME


class NotificationPreferenceResponse(BaseModel):
    """Response model for notification preferences"""
    id: str
    user_id: str
    notification_type: str
    channel: NotificationChannel
    enabled: bool
    quiet_hours: Optional[Dict[str, Any]]
    frequency: DigestFrequency
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateSubscriptionRequest(BaseModel):
    """Request model for creating notification subscriptions"""
    resource_type: str
    resource_id: str
    notify_on: List[str] = Field(default_factory=list)


class NotificationSubscriptionResponse(BaseModel):
    """Response model for notification subscriptions"""
    id: str
    user_id: str
    resource_type: str
    resource_id: str
    notify_on: List[str]
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationEvent(BaseModel):
    """Model for notification events published to the event bus"""
    event_key: str  # e.g., 'chat.message.created'
    payload: Dict[str, Any]
    actor_id: str  # User who triggered the event
    tenant_id: Optional[str] = None
    source_event_id: str  # Unique identifier for idempotency
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketMessage(BaseModel):
    """Model for WebSocket notification messages"""
    type: str  # 'notification' | 'unread_count' | 'connection_ack'
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
