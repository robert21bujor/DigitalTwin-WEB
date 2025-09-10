"""
Message Sender Module
===================

External interface for sending messages to agents from UI, orchestrator, or other systems.
Provides a clean API for non-agent components to communicate with agents.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .schemas import (
    AgentMessage, MessageIntent, MessagePayload, AgentInfo,
    create_task_assignment_message, create_knowledge_request_message,
    create_status_update_message, AgentNotFoundError, MessageDeliveryError
)
from .broker import MessageBroker
from .registry import AgentRegistry

# Configure logging
logger = logging.getLogger(__name__)


class MessageSender:
    """
    External message sender for communicating with agents
    
    Features:
    - Send messages to agents from external systems
    - Agent discovery and validation
    - Message delivery tracking
    - Response handling
    - Batch message operations
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        sender_id: str = "system.orchestrator",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize message sender
        
        Args:
            redis_url: Redis connection URL
            sender_id: Identifier for this sender
            timeout: Message timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.redis_url = redis_url
        self.sender_id = sender_id
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Infrastructure components
        self._message_broker: Optional[MessageBroker] = None
        self._agent_registry: Optional[AgentRegistry] = None
        
        # Response tracking
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._response_handlers: Dict[str, Any] = {}
        
        # Statistics
        self._messages_sent = 0
        self._messages_failed = 0
        self._responses_received = 0
        
        logger.info(f"MessageSender initialized with sender_id: {sender_id}")
    
    async def initialize(self) -> None:
        """Initialize the message sender"""
        try:
            # Initialize message broker
            self._message_broker = MessageBroker(redis_url=self.redis_url)
            await self._message_broker.initialize()
            
            # Initialize agent registry
            self._agent_registry = AgentRegistry(redis_url=self.redis_url)
            await self._agent_registry.initialize()
            
            # Subscribe to responses (use sender_id as agent_id for responses)
            await self._message_broker.subscribe_to_agent(
                self.sender_id,
                self._handle_response
            )
            
            logger.info(f"MessageSender initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MessageSender: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the message sender"""
        try:
            # Cancel pending responses
            for future in self._pending_responses.values():
                if not future.done():
                    future.cancel()
            
            # Shutdown infrastructure
            if self._message_broker:
                await self._message_broker.shutdown()
            
            if self._agent_registry:
                await self._agent_registry.shutdown()
            
            logger.info("MessageSender shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during MessageSender shutdown: {e}")
    
    async def send_message(
        self,
        recipient_id: str,
        intent: MessageIntent,
        data: Dict[str, Any],
        priority: str = "normal",
        requires_response: bool = False,
        response_timeout: Optional[int] = None,
        conversation_id: Optional[str] = None
    ) -> Union[bool, AgentMessage]:
        """
        Send a message to an agent
        
        Args:
            recipient_id: Target agent ID
            intent: Message intent
            data: Message data
            priority: Message priority
            requires_response: Whether to wait for response
            response_timeout: Response timeout (overrides default)
            conversation_id: Optional conversation ID
            
        Returns:
            bool: True if sent successfully (no response expected)
            AgentMessage: Response message (if response expected)
        """
        try:
            # Validate recipient
            if not await self._validate_recipient(recipient_id):
                raise AgentNotFoundError(f"Agent not found: {recipient_id}")
            
            # Create message
            payload = MessagePayload(
                data=data,
                priority=priority,
                requires_response=requires_response,
                response_timeout=response_timeout or self.timeout
            )
            
            message = AgentMessage(
                conversation_id=conversation_id or f"conv_{self.sender_id}_{datetime.utcnow().timestamp()}",
                sender_id=self.sender_id,
                recipient_id=recipient_id,
                intent=intent,
                payload=payload
            )
            
            # Send message
            success = await self._send_with_retry(message)
            
            if not success:
                self._messages_failed += 1
                raise MessageDeliveryError(f"Failed to send message to {recipient_id}")
            
            self._messages_sent += 1
            
            # Wait for response if required
            if requires_response:
                response = await self._wait_for_response(message)
                return response
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {recipient_id}: {e}")
            self._messages_failed += 1
            raise
    
    async def assign_task(
        self,
        agent_id: str,
        task_id: str,
        task_description: str,
        priority: str = "normal",
        deadline: Optional[str] = None,
        wait_for_response: bool = True
    ) -> Union[bool, AgentMessage]:
        """
        Assign a task to an agent
        
        Args:
            agent_id: Target agent ID
            task_id: Task identifier
            task_description: Task description
            priority: Task priority
            deadline: Task deadline (ISO format)
            wait_for_response: Whether to wait for acknowledgment
            
        Returns:
            bool or AgentMessage: Response or success status
        """
        try:
            message = create_task_assignment_message(
                sender_id=self.sender_id,
                recipient_id=agent_id,
                task_id=task_id,
                task_description=task_description,
                priority=priority,
                deadline=deadline
            )
            
            # Override response requirement
            message.payload.requires_response = wait_for_response
            
            success = await self._send_with_retry(message)
            
            if not success:
                raise MessageDeliveryError(f"Failed to assign task to {agent_id}")
            
            if wait_for_response:
                response = await self._wait_for_response(message)
                return response
            
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task to {agent_id}: {e}")
            raise
    
    async def request_knowledge(
        self,
        agent_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        wait_for_response: bool = True
    ) -> Union[bool, AgentMessage]:
        """
        Request knowledge from an agent
        
        Args:
            agent_id: Target agent ID
            query: Knowledge query
            context: Additional context
            wait_for_response: Whether to wait for response
            
        Returns:
            bool or AgentMessage: Response or success status
        """
        try:
            message = create_knowledge_request_message(
                sender_id=self.sender_id,
                recipient_id=agent_id,
                query=query,
                context=context
            )
            
            # Override response requirement
            message.payload.requires_response = wait_for_response
            
            success = await self._send_with_retry(message)
            
            if not success:
                raise MessageDeliveryError(f"Failed to request knowledge from {agent_id}")
            
            if wait_for_response:
                response = await self._wait_for_response(message)
                return response
            
            return True
            
        except Exception as e:
            logger.error(f"Error requesting knowledge from {agent_id}: {e}")
            raise
    
    async def broadcast_message(
        self,
        intent: MessageIntent,
        data: Dict[str, Any],
        role: Optional[str] = None,
        department: Optional[str] = None,
        capability: Optional[str] = None,
        priority: str = "normal",
        max_recipients: int = 10
    ) -> Dict[str, bool]:
        """
        Broadcast a message to multiple agents
        
        Args:
            intent: Message intent
            data: Message data
            role: Filter by role
            department: Filter by department
            capability: Filter by capability
            priority: Message priority
            max_recipients: Maximum number of recipients
            
        Returns:
            Dictionary mapping agent_id to success status
        """
        try:
            # Discover target agents
            if not self._agent_registry:
                raise Exception("Agent registry not initialized")
            
            agents = await self._agent_registry.discover_agents(
                role=role,
                department=department,
                capability=capability,
                intent=intent,
                online_only=True
            )
            
            # Limit recipients
            agents = agents[:max_recipients]
            
            if not agents:
                logger.warning("No agents found for broadcast")
                return {}
            
            # Send to all agents
            results = {}
            tasks = []
            
            for agent in agents:
                task = asyncio.create_task(
                    self.send_message(
                        recipient_id=agent.agent_id,
                        intent=intent,
                        data=data,
                        priority=priority,
                        requires_response=False
                    )
                )
                tasks.append((agent.agent_id, task))
            
            # Wait for all sends to complete
            for agent_id, task in tasks:
                try:
                    result = await task
                    results[agent_id] = result
                except Exception as e:
                    logger.error(f"Broadcast failed for {agent_id}: {e}")
                    results[agent_id] = False
            
            success_count = sum(1 for success in results.values() if success)
            logger.info(f"Broadcast completed: {success_count}/{len(results)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return {}
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific agent
        
        Args:
            agent_id: Target agent ID
            
        Returns:
            Agent status information or None
        """
        try:
            response = await self.send_message(
                recipient_id=agent_id,
                intent=MessageIntent.HEALTH_CHECK,
                data={},
                requires_response=True,
                response_timeout=10
            )
            
            if isinstance(response, AgentMessage):
                return response.payload.data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get agent status for {agent_id}: {e}")
            return None
    
    async def discover_agents(
        self,
        role: Optional[str] = None,
        department: Optional[str] = None,
        capability: Optional[str] = None,
        intent: Optional[MessageIntent] = None,
        online_only: bool = True
    ) -> List[AgentInfo]:
        """
        Discover agents based on criteria
        
        Args:
            role: Filter by role
            department: Filter by department
            capability: Filter by capability
            intent: Filter by supported intent
            online_only: Only return online agents
            
        Returns:
            List of matching agents
        """
        if not self._agent_registry:
            logger.error("Agent registry not initialized")
            return []
        
        try:
            return await self._agent_registry.discover_agents(
                role=role,
                department=department,
                capability=capability,
                intent=intent,
                online_only=online_only
            )
            
        except Exception as e:
            logger.error(f"Agent discovery failed: {e}")
            return []
    
    async def get_sender_stats(self) -> Dict[str, Any]:
        """
        Get message sender statistics
        
        Returns:
            Dictionary with sender statistics
        """
        return {
            "sender_id": self.sender_id,
            "messages_sent": self._messages_sent,
            "messages_failed": self._messages_failed,
            "responses_received": self._responses_received,
            "pending_responses": len(self._pending_responses),
            "success_rate": (
                self._messages_sent / (self._messages_sent + self._messages_failed)
                if (self._messages_sent + self._messages_failed) > 0
                else 0
            )
        }
    
    # Private methods
    
    async def _validate_recipient(self, recipient_id: str) -> bool:
        """Validate that recipient agent exists and is online"""
        if not self._agent_registry:
            logger.warning("Agent registry not available for validation")
            return True  # Assume valid if registry not available
        
        try:
            agent = await self._agent_registry.get_agent(recipient_id)
            if not agent:
                return False
            
            # Check if agent is online
            online_agents = await self._agent_registry.get_online_agents()
            return any(a.agent_id == recipient_id for a in online_agents)
            
        except Exception as e:
            logger.error(f"Error validating recipient {recipient_id}: {e}")
            return False
    
    async def _send_with_retry(self, message: AgentMessage) -> bool:
        """Send message with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if not self._message_broker:
                    raise Exception("Message broker not initialized")
                
                success = await self._message_broker.publish_message(message)
                
                if success:
                    logger.debug(f"Message {message.message_id} sent successfully")
                    return True
                else:
                    last_error = "Broker returned failure"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Send attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
        
        logger.error(f"All send attempts failed for message {message.message_id}: {last_error}")
        return False
    
    async def _wait_for_response(self, message: AgentMessage) -> AgentMessage:
        """Wait for response to a message"""
        message_id = message.message_id
        timeout = message.payload.response_timeout or self.timeout
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[message_id] = response_future
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            self._responses_received += 1
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Response timeout for message {message_id}")
            raise MessageDeliveryError(f"Response timeout for message {message_id}")
        
        finally:
            # Clean up
            self._pending_responses.pop(message_id, None)
    
    async def _handle_response(self, message: AgentMessage) -> None:
        """Handle response messages"""
        try:
            # Check if this is a response to a pending request
            correlation_id = message.correlation_id or message.reply_to
            
            if correlation_id and correlation_id in self._pending_responses:
                future = self._pending_responses[correlation_id]
                if not future.done():
                    future.set_result(message)
                    logger.debug(f"Response received for message {correlation_id}")
                else:
                    logger.warning(f"Response received for already completed message {correlation_id}")
            else:
                logger.debug(f"Received unsolicited message from {message.sender_id}")
                
        except Exception as e:
            logger.error(f"Error handling response: {e}")


# Utility functions for common operations

async def send_task_to_agent(
    agent_id: str,
    task_id: str,
    task_description: str,
    priority: str = "normal",
    deadline: Optional[str] = None,
    redis_url: str = "redis://localhost:6379"
) -> bool:
    """
    Utility function to send a task to an agent
    
    Args:
        agent_id: Target agent ID
        task_id: Task identifier
        task_description: Task description
        priority: Task priority
        deadline: Task deadline
        redis_url: Redis URL
        
    Returns:
        bool: True if task sent successfully
    """
    sender = MessageSender(redis_url=redis_url)
    
    try:
        await sender.initialize()
        
        result = await sender.assign_task(
            agent_id=agent_id,
            task_id=task_id,
            task_description=task_description,
            priority=priority,
            deadline=deadline,
            wait_for_response=False
        )
        
        return isinstance(result, bool) and result
        
    except Exception as e:
        logger.error(f"Error sending task to agent: {e}")
        return False
    
    finally:
        await sender.shutdown()


async def request_agent_knowledge(
    agent_id: str,
    query: str,
    context: Optional[Dict[str, Any]] = None,
    redis_url: str = "redis://localhost:6379"
) -> Optional[Dict[str, Any]]:
    """
    Utility function to request knowledge from an agent
    
    Args:
        agent_id: Target agent ID
        query: Knowledge query
        context: Additional context
        redis_url: Redis URL
        
    Returns:
        Knowledge response or None
    """
    sender = MessageSender(redis_url=redis_url)
    
    try:
        await sender.initialize()
        
        response = await sender.request_knowledge(
            agent_id=agent_id,
            query=query,
            context=context,
            wait_for_response=True
        )
        
        if isinstance(response, AgentMessage):
            return response.payload.data
        
        return None
        
    except Exception as e:
        logger.error(f"Error requesting knowledge from agent: {e}")
        return None
    
    finally:
        await sender.shutdown()


async def discover_online_agents(
    role: Optional[str] = None,
    department: Optional[str] = None,
    redis_url: str = "redis://localhost:6379"
) -> List[AgentInfo]:
    """
    Utility function to discover online agents
    
    Args:
        role: Filter by role
        department: Filter by department
        redis_url: Redis URL
        
    Returns:
        List of online agents
    """
    sender = MessageSender(redis_url=redis_url)
    
    try:
        await sender.initialize()
        
        return await sender.discover_agents(
            role=role,
            department=department,
            online_only=True
        )
        
    except Exception as e:
        logger.error(f"Error discovering agents: {e}")
        return []
    
    finally:
        await sender.shutdown() 