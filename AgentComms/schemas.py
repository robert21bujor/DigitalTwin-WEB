"""
Message Schemas for Agent Communication
======================================

Pydantic models defining the structured message protocol for agent-to-agent communication.
All messages follow a strict schema for reliable inter-agent communication.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator


class MessageIntent(str, Enum):
    """Predefined message intents for agent communication"""
    
    # Task management
    GET_ROADMAP = "get_roadmap"
    ASSIGN_TASK = "assign_task"
    UPDATE_TASK_STATUS = "update_task_status"
    REQUEST_TASK_HELP = "request_task_help"
    
    # Knowledge sharing
    SHARE_INSIGHTS = "share_insights"
    REQUEST_KNOWLEDGE = "request_knowledge"
    PROVIDE_CONTEXT = "provide_context"
    
    # Collaboration
    REQUEST_REVIEW = "request_review"
    PROVIDE_FEEDBACK = "provide_feedback"
    SCHEDULE_MEETING = "schedule_meeting"
    
    # System communication
    AGENT_STATUS = "agent_status"
    HEALTH_CHECK = "health_check"
    CAPABILITY_QUERY = "capability_query"
    
    # Custom intents
    CUSTOM = "custom"


class MessagePayload(BaseModel):
    """Flexible payload structure for different message types"""
    
    # Core data - varies by intent
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    requires_response: bool = Field(default=False)
    response_timeout: Optional[int] = Field(default=None, description="Timeout in seconds")
    
    # Context information
    context: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[str] = Field(default_factory=list, description="File paths or URLs")
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class ConversationContext(BaseModel):
    """Context information for ongoing conversations"""
    
    conversation_id: str = Field(..., description="Unique conversation identifier")
    thread_id: Optional[str] = Field(default=None, description="Optional thread within conversation")
    participants: List[str] = Field(..., description="List of agent IDs in conversation")
    topic: Optional[str] = Field(default=None, description="Conversation topic")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        extra = "forbid"


class AgentMessage(BaseModel):
    """Core message structure for agent-to-agent communication"""
    
    # Required fields per specification
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message identifier")
    conversation_id: str = Field(..., description="Conversation this message belongs to")
    sender_id: str = Field(..., description="Sending agent ID (e.g., agent.user1)")
    recipient_id: str = Field(..., description="Receiving agent ID (e.g., agent.marian)")
    intent: MessageIntent = Field(..., description="Message intent/purpose")
    payload: MessagePayload = Field(..., description="Message content and metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message creation time")
    
    # Optional fields for enhanced functionality
    reply_to: Optional[str] = Field(default=None, description="Message ID this is replying to")
    correlation_id: Optional[str] = Field(default=None, description="For request-response correlation")
    ttl: Optional[int] = Field(default=3600, description="Time to live in seconds")
    
    @validator('sender_id', 'recipient_id')
    def validate_agent_id(cls, v):
        """Validate agent ID format: agent.{name} or system.{service}"""
        if not (v.startswith('agent.') or v.startswith('system.')):
            raise ValueError('Agent ID must start with "agent." or "system."')
        if len(v.split('.')) < 2:
            raise ValueError('Agent ID must be in format "agent.{name}" or "system.{service}"')
        return v.lower()
    
    @validator('message_id', 'conversation_id')
    def validate_uuid_format(cls, v):
        """Ensure IDs are valid UUIDs or UUID-like strings"""
        try:
            # Try to parse as UUID to validate format
            uuid.UUID(v)
        except ValueError:
            # Allow non-UUID strings but they should be non-empty
            if not v or not isinstance(v, str):
                raise ValueError('ID must be a valid UUID or non-empty string')
        return v
    
    def to_json(self) -> str:
        """Serialize message to JSON string for transmission"""
        return self.model_dump_json(exclude_unset=True)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """Deserialize message from JSON string"""
        return cls.model_validate_json(json_str)
    
    def create_reply(self, sender_id: str, intent: MessageIntent, payload: MessagePayload) -> 'AgentMessage':
        """Create a reply message to this message"""
        return AgentMessage(
            conversation_id=self.conversation_id,
            sender_id=sender_id,
            recipient_id=self.sender_id,  # Reply to original sender
            intent=intent,
            payload=payload,
            reply_to=self.message_id,
            correlation_id=self.correlation_id
        )
    
    class Config:
        extra = "forbid"
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentInfo(BaseModel):
    """Agent registration information"""
    
    agent_id: str = Field(..., description="Unique agent identifier")
    user_name: str = Field(..., description="Associated user name")
    role: str = Field(..., description="Agent role/type")
    department: Optional[str] = Field(default=None, description="Department/team")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    status: str = Field(default="online", pattern="^(online|offline|busy|away)$")
    
    # Communication preferences
    channel: str = Field(..., description="Redis channel for this agent")
    supports_intents: List[MessageIntent] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('agent_id')
    def validate_agent_id_format(cls, v):
        """Validate agent ID format"""
        if not (v.startswith('agent.') or v.startswith('system.')):
            raise ValueError('Agent ID must start with "agent." or "system."')
        return v.lower()
    
    class Config:
        extra = "allow"


# Custom exceptions for the communication system
class AgentCommError(Exception):
    """Base exception for agent communication errors"""
    pass


class AgentNotFoundError(AgentCommError):
    """Raised when an agent cannot be found in the registry"""
    pass


class MessageDeliveryError(AgentCommError):
    """Raised when message delivery fails"""
    pass


class InvalidMessageError(AgentCommError):
    """Raised when message validation fails"""
    pass


# Message factory functions for common use cases
def create_task_assignment_message(
    sender_id: str,
    recipient_id: str,
    task_id: str,
    task_description: str,
    priority: str = "normal",
    deadline: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> AgentMessage:
    """Factory function for task assignment messages"""
    
    payload_data = {
        "task_id": task_id,
        "description": task_description,
        "deadline": deadline
    }
    
    payload = MessagePayload(
        data=payload_data,
        priority=priority,
        requires_response=True,
        response_timeout=300  # 5 minutes
    )
    
    return AgentMessage(
        conversation_id=conversation_id or str(uuid.uuid4()),
        sender_id=sender_id,
        recipient_id=recipient_id,
        intent=MessageIntent.ASSIGN_TASK,
        payload=payload
    )


def create_knowledge_request_message(
    sender_id: str,
    recipient_id: str,
    query: str,
    context: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None
) -> AgentMessage:
    """Factory function for knowledge request messages"""
    
    payload_data = {
        "query": query,
        "requested_at": datetime.utcnow().isoformat()
    }
    
    payload = MessagePayload(
        data=payload_data,
        context=context or {},
        requires_response=True,
        response_timeout=60  # 1 minute
    )
    
    return AgentMessage(
        conversation_id=conversation_id or str(uuid.uuid4()),
        sender_id=sender_id,
        recipient_id=recipient_id,
        intent=MessageIntent.REQUEST_KNOWLEDGE,
        payload=payload
    )


def create_status_update_message(
    sender_id: str,
    recipient_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None
) -> AgentMessage:
    """Factory function for status update messages"""
    
    payload_data = {
        "status": status,
        "details": details or {},
        "updated_at": datetime.utcnow().isoformat()
    }
    
    payload = MessagePayload(
        data=payload_data,
        priority="normal"
    )
    
    return AgentMessage(
        conversation_id=conversation_id or str(uuid.uuid4()),
        sender_id=sender_id,
        recipient_id=recipient_id,
        intent=MessageIntent.UPDATE_TASK_STATUS,
        payload=payload
    ) 