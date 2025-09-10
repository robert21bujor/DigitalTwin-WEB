"""
Base Agent for Agent Communication Infrastructure
==============================================

Abstract base class that all agents inherit from. Provides core functionality
for Redis-based communication, message routing, and intent handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Callable, Optional, Any, List
from datetime import datetime

from .schemas import AgentMessage, MessageIntent, MessagePayload, AgentInfo, AgentCommError
from .broker import MessageBroker
from .registry import AgentRegistry
from .memory import AgentMemoryInterface

# Configure logging
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the communication infrastructure
    
    Features:
    - Redis Pub/Sub message handling
    - Intent-based message routing
    - Memory interface integration
    - Agent registry management
    - Heartbeat and health monitoring
    - Error handling and logging
    """
    
    def __init__(
        self,
        agent_id: str,
        user_name: str,
        role: str,
        department: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        redis_url: str = "redis://localhost:6379",
        memory_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique agent identifier (e.g., "agent.user1")
            user_name: Associated user name
            role: Agent role/type
            department: Department/team (optional)
            capabilities: List of agent capabilities
            redis_url: Redis connection URL
            memory_config: Memory interface configuration
        """
        # Validate agent ID format
        if not agent_id.startswith('agent.'):
            raise ValueError("Agent ID must start with 'agent.'")
        
        self.agent_id = agent_id
        self.user_name = user_name
        self.role = role
        self.department = department
        self.capabilities = capabilities or []
        self.redis_url = redis_url
        
        # Communication infrastructure
        self._message_broker: Optional[MessageBroker] = None
        self._agent_registry: Optional[AgentRegistry] = None
        self._memory_interface: Optional[AgentMemoryInterface] = None
        
        # Message handling
        self._intent_handlers: Dict[MessageIntent, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        
        # Background tasks
        self._message_processor_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # State management
        self._running = False
        self._initialized = False
        
        # Setup intent handlers
        self._setup_default_handlers()
        
        logger.info(f"BaseAgent initialized: {agent_id} ({role})")
    
    async def initialize(self) -> None:
        """Initialize the agent and all infrastructure components"""
        if self._initialized:
            logger.warning(f"Agent {self.agent_id} already initialized")
            return
        
        try:
            # Initialize message broker
            self._message_broker = MessageBroker(redis_url=self.redis_url)
            await self._message_broker.initialize()
            
            # Initialize agent registry
            self._agent_registry = AgentRegistry(redis_url=self.redis_url)
            await self._agent_registry.initialize()
            
            # Initialize memory interface
            self._memory_interface = AgentMemoryInterface()
            await self._memory_interface.initialize()
            
            # Register this agent
            await self._register_agent()
            
            # Subscribe to messages
            await self._message_broker.subscribe_to_agent(
                self.agent_id,
                self._handle_incoming_message
            )
            
            # Start background tasks
            self._running = True
            self._message_processor_task = asyncio.create_task(self._process_messages())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Call subclass initialization
            await self._on_initialize()
            
            self._initialized = True
            logger.info(f"Agent {self.agent_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            await self.shutdown()
            raise AgentCommError(f"Agent initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent"""
        self._running = False
        
        # Stop background tasks
        if self._message_processor_task and not self._message_processor_task.done():
            self._message_processor_task.cancel()
        
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        
        # Unregister from registry
        if self._agent_registry:
            await self._agent_registry.unregister_agent(self.agent_id)
        
        # Shutdown infrastructure
        if self._message_broker:
            await self._message_broker.shutdown()
        
        if self._agent_registry:
            await self._agent_registry.shutdown()
        
        # Call subclass cleanup
        await self._on_shutdown()
        
        logger.info(f"Agent {self.agent_id} shutdown complete")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message to another agent
        
        Args:
            message: AgentMessage to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            if not self._message_broker:
                logger.error(f"Message broker not initialized for {self.agent_id}")
                return False
            
            # Add sender validation
            if message.sender_id != self.agent_id:
                logger.warning(f"Message sender mismatch: {message.sender_id} != {self.agent_id}")
                message.sender_id = self.agent_id
            
            # Send message
            success = await self._message_broker.publish_message(message)
            
            if success:
                logger.debug(f"Sent message {message.message_id} to {message.recipient_id}")
            else:
                logger.error(f"Failed to send message {message.message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending message from {self.agent_id}: {e}")
            return False
    
    async def discover_agents(
        self,
        role: Optional[str] = None,
        department: Optional[str] = None,
        capability: Optional[str] = None,
        intent: Optional[MessageIntent] = None
    ) -> List[AgentInfo]:
        """
        Discover other agents based on criteria
        
        Args:
            role: Filter by role
            department: Filter by department
            capability: Filter by capability
            intent: Filter by supported intent
            
        Returns:
            List of matching AgentInfo objects
        """
        if not self._agent_registry:
            logger.error(f"Agent registry not initialized for {self.agent_id}")
            return []
        
        try:
            agents = await self._agent_registry.discover_agents(
                role=role,
                department=department,
                capability=capability,
                intent=intent,
                online_only=True
            )
            
            # Exclude self from results
            agents = [agent for agent in agents if agent.agent_id != self.agent_id]
            
            logger.debug(f"Discovered {len(agents)} agents matching criteria")
            return agents
            
        except Exception as e:
            logger.error(f"Agent discovery failed for {self.agent_id}: {e}")
            return []
    
    async def search_knowledge(
        self,
        query: str,
        intent: Optional[MessageIntent] = None,
        context: Optional[Dict[str, Any]] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant knowledge
        
        Args:
            query: Search query
            intent: Message intent for context
            context: Additional context
            max_results: Maximum results to return
            
        Returns:
            List of knowledge items
        """
        if not self._memory_interface:
            logger.error(f"Memory interface not initialized for {self.agent_id}")
            return []
        
        try:
            results = await self._memory_interface.search_knowledge(
                agent_id=self.agent_id,
                role=self.role,
                query=query,
                intent=intent,
                context=context,
                max_results=max_results
            )
            
            logger.debug(f"Found {len(results)} knowledge items for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Knowledge search failed for {self.agent_id}: {e}")
            return []
    
    def register_intent_handler(self, intent: MessageIntent, handler: Callable[[AgentMessage], None]) -> None:
        """
        Register a handler for a specific message intent
        
        Args:
            intent: Message intent to handle
            handler: Handler function (can be async)
        """
        self._intent_handlers[intent] = handler
        logger.debug(f"Registered handler for intent {intent.value}")
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    async def handle_get_roadmap(self, message: AgentMessage) -> None:
        """Handle roadmap requests"""
        pass
    
    @abstractmethod
    async def handle_assign_task(self, message: AgentMessage) -> None:
        """Handle task assignment"""
        pass
    
    @abstractmethod
    async def handle_request_knowledge(self, message: AgentMessage) -> None:
        """Handle knowledge requests"""
        pass
    
    @abstractmethod
    async def get_supported_intents(self) -> List[MessageIntent]:
        """Return list of supported message intents"""
        pass
    
    @abstractmethod
    async def get_agent_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass
    
    # Hook methods for subclass customization
    
    async def _on_initialize(self) -> None:
        """Called after base initialization, override in subclasses"""
        pass
    
    async def _on_shutdown(self) -> None:
        """Called during shutdown, override in subclasses"""
        pass
    
    async def _on_message_received(self, message: AgentMessage) -> None:
        """Called when any message is received, override in subclasses"""
        pass
    
    # Private methods
    
    def _setup_default_handlers(self) -> None:
        """Setup default intent handlers"""
        self._intent_handlers = {
            MessageIntent.GET_ROADMAP: self.handle_get_roadmap,
            MessageIntent.ASSIGN_TASK: self.handle_assign_task,
            MessageIntent.REQUEST_KNOWLEDGE: self.handle_request_knowledge,
            MessageIntent.HEALTH_CHECK: self._handle_health_check,
            MessageIntent.CAPABILITY_QUERY: self._handle_capability_query,
            MessageIntent.AGENT_STATUS: self._handle_agent_status
        }
    
    async def _register_agent(self) -> None:
        """Register this agent with the registry"""
        if not self._agent_registry:
            return
        
        try:
            supported_intents = await self.get_supported_intents()
            capabilities = await self.get_agent_capabilities()
            
            agent_info = AgentInfo(
                agent_id=self.agent_id,
                user_name=self.user_name,
                role=self.role,
                department=self.department,
                capabilities=capabilities,
                status="online",
                channel=f"agent_comm:{self.agent_id}",
                supports_intents=supported_intents
            )
            
            await self._agent_registry.register_agent(agent_info)
            logger.info(f"Registered agent {self.agent_id} with registry")
            
        except Exception as e:
            logger.error(f"Failed to register agent {self.agent_id}: {e}")
    
    async def _handle_incoming_message(self, message: AgentMessage) -> None:
        """Handle incoming message from broker"""
        try:
            # Add to message queue for processing
            await self._message_queue.put(message)
            
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
    
    async def _process_messages(self) -> None:
        """Background task to process incoming messages"""
        while self._running:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                
                # Call hook for subclass processing
                await self._on_message_received(message)
                
                # Route to appropriate handler
                await self._route_message(message)
                
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1.0)
    
    async def _route_message(self, message: AgentMessage) -> None:
        """Route message to appropriate handler based on intent"""
        try:
            handler = self._intent_handlers.get(message.intent)
            
            if handler:
                # Call handler (handle both sync and async)
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
                    
                logger.debug(f"Handled message {message.message_id} with intent {message.intent.value}")
            else:
                logger.warning(f"No handler for intent {message.intent.value}")
                await self._handle_unknown_intent(message)
                
        except Exception as e:
            logger.error(f"Error routing message {message.message_id}: {e}")
    
    async def _handle_unknown_intent(self, message: AgentMessage) -> None:
        """Handle messages with unknown intents"""
        # Send error response if response is required
        if message.payload.requires_response:
            error_response = message.create_reply(
                sender_id=self.agent_id,
                intent=MessageIntent.AGENT_STATUS,
                payload=MessagePayload(
                    data={"error": f"Unknown intent: {message.intent.value}"},
                    priority="normal"
                )
            )
            await self.send_message(error_response)
    
    async def _handle_health_check(self, message: AgentMessage) -> None:
        """Handle health check requests"""
        try:
            health_data = {
                "agent_id": self.agent_id,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "capabilities": await self.get_agent_capabilities(),
                "supported_intents": [intent.value for intent in await self.get_supported_intents()]
            }
            
            response = message.create_reply(
                sender_id=self.agent_id,
                intent=MessageIntent.AGENT_STATUS,
                payload=MessagePayload(
                    data=health_data,
                    priority="normal"
                )
            )
            
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _handle_capability_query(self, message: AgentMessage) -> None:
        """Handle capability query requests"""
        try:
            capabilities = await self.get_agent_capabilities()
            supported_intents = await self.get_supported_intents()
            
            capability_data = {
                "agent_id": self.agent_id,
                "role": self.role,
                "department": self.department,
                "capabilities": capabilities,
                "supported_intents": [intent.value for intent in supported_intents],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = message.create_reply(
                sender_id=self.agent_id,
                intent=MessageIntent.AGENT_STATUS,
                payload=MessagePayload(
                    data=capability_data,
                    priority="normal"
                )
            )
            
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Capability query failed: {e}")
    
    async def _handle_agent_status(self, message: AgentMessage) -> None:
        """Handle agent status messages"""
        # Log status message
        status_data = message.payload.data
        logger.info(f"Received status from {message.sender_id}: {status_data}")
    
    async def _heartbeat_loop(self) -> None:
        """Background task for sending heartbeats"""
        while self._running:
            try:
                if self._agent_registry:
                    await self._agent_registry.heartbeat(self.agent_id)
                
                # Sleep for heartbeat interval
                await asyncio.sleep(30)  # 30-second heartbeat
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat failed for {self.agent_id}: {e}")
                await asyncio.sleep(10)  # Shorter sleep on error
    
    # Utility methods for subclasses
    
    async def create_and_send_message(
        self,
        recipient_id: str,
        intent: MessageIntent,
        data: Dict[str, Any],
        priority: str = "normal",
        requires_response: bool = False,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Utility method to create and send a message
        
        Args:
            recipient_id: Target agent ID
            intent: Message intent
            data: Message data
            priority: Message priority
            requires_response: Whether response is required
            conversation_id: Optional conversation ID
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            payload = MessagePayload(
                data=data,
                priority=priority,
                requires_response=requires_response
            )
            
            message = AgentMessage(
                conversation_id=conversation_id or f"conv_{self.agent_id}_{datetime.utcnow().timestamp()}",
                sender_id=self.agent_id,
                recipient_id=recipient_id,
                intent=intent,
                payload=payload
            )
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to create and send message: {e}")
            return False
    
    async def reply_to_message(
        self,
        original_message: AgentMessage,
        intent: MessageIntent,
        data: Dict[str, Any],
        priority: str = "normal"
    ) -> bool:
        """
        Utility method to reply to a message
        
        Args:
            original_message: Message to reply to
            intent: Reply intent
            data: Reply data
            priority: Reply priority
            
        Returns:
            bool: True if reply sent successfully
        """
        try:
            payload = MessagePayload(
                data=data,
                priority=priority
            )
            
            reply = original_message.create_reply(
                sender_id=self.agent_id,
                intent=intent,
                payload=payload
            )
            
            return await self.send_message(reply)
            
        except Exception as e:
            logger.error(f"Failed to reply to message: {e}")
            return False 