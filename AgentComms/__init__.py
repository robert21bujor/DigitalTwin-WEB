"""
Agent-to-Agent Communication Infrastructure
==========================================

A production-ready, modular system for asynchronous agent communication
using Redis Pub/Sub with structured message passing.

Components:
- Message Schema: Pydantic models for structured messaging
- Message Broker: Redis Pub/Sub interface
- Agent Registry: Centralized agent discovery and mapping
- Memory Interface: Role-based knowledge retrieval
- Base Agent: Abstract agent with message routing
- Message Sender: External message publishing interface

Features:
- Asynchronous Redis-based communication
- Structured JSON message protocol
- Role-based agent discovery
- Intent-based message routing
- Production logging and error handling
- Independent module deployment
"""

from .schemas import *
from .broker import MessageBroker
from .registry import AgentRegistry
from .memory import AgentMemoryInterface
from .base_agent import BaseAgent
from .sender import MessageSender

__version__ = "1.0.0"
__all__ = [
    # Core components
    "MessageBroker",
    "AgentRegistry", 
    "AgentMemoryInterface",
    "BaseAgent",
    "MessageSender",
    
    # Message schemas
    "AgentMessage",
    "MessagePayload",
    "MessageIntent",
    "AgentInfo",
    "ConversationContext",
    
    # Exceptions
    "AgentCommError",
    "AgentNotFoundError",
    "MessageDeliveryError",
    "InvalidMessageError"
] 