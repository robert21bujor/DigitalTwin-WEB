"""
Redis Message Broker for Agent Communication
==========================================

Production-ready Redis Pub/Sub implementation for asynchronous agent-to-agent messaging.
Handles message publishing, subscription, and delivery with proper error handling and logging.
"""

import asyncio
import json
import logging
import time
from typing import Callable, Dict, Optional, Set, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

from .schemas import AgentMessage, AgentCommError, MessageDeliveryError, InvalidMessageError

# Configure logging
logger = logging.getLogger(__name__)


class MessageBroker:
    """
    Redis-based message broker for agent communication
    
    Features:
    - Asynchronous Redis Pub/Sub
    - Message persistence and delivery guarantees
    - Connection pooling and retry logic
    - Message serialization/deserialization
    - Error handling and logging
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 20,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        message_ttl: int = 3600,
        enable_persistence: bool = True
    ):
        """
        Initialize message broker
        
        Args:
            redis_url: Redis connection URL
            max_connections: Maximum Redis connections in pool
            retry_attempts: Number of retry attempts for failed operations
            retry_delay: Delay between retry attempts (seconds)
            message_ttl: Default message time-to-live (seconds)
            enable_persistence: Whether to persist messages for offline agents
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.message_ttl = message_ttl
        self.enable_persistence = enable_persistence
        
        # Connection management
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._pubsub_client: Optional[redis.Redis] = None
        self._publish_client: Optional[redis.Redis] = None
        
        # Subscription management
        self._subscriptions: Dict[str, Callable] = {}
        self._subscription_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"MessageBroker initialized with Redis: {redis_url}")
    
    async def initialize(self) -> None:
        """Initialize Redis connections and start broker"""
        try:
            # Create connection pool
            self._redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis clients
            self._pubsub_client = redis.Redis(connection_pool=self._redis_pool)
            self._publish_client = redis.Redis(connection_pool=self._redis_pool)
            
            # Test connection
            await self._publish_client.ping()
            
            self._running = True
            logger.info("MessageBroker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MessageBroker: {e}")
            raise AgentCommError(f"Broker initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the message broker"""
        self._running = False
        
        # Stop subscription task
        if self._subscription_task and not self._subscription_task.done():
            self._subscription_task.cancel()
            try:
                await self._subscription_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connections
        if self._pubsub_client:
            await self._pubsub_client.close()
        if self._publish_client:
            await self._publish_client.close()
        if self._redis_pool:
            await self._redis_pool.disconnect()
        
        logger.info("MessageBroker shutdown complete")
    
    async def publish_message(self, message: AgentMessage) -> bool:
        """
        Publish message to recipient's channel
        
        Args:
            message: AgentMessage to publish
            
        Returns:
            bool: True if message was published successfully
            
        Raises:
            MessageDeliveryError: If message delivery fails
        """
        if not self._running:
            raise AgentCommError("Broker not initialized")
        
        try:
            # Validate message
            if not isinstance(message, AgentMessage):
                raise InvalidMessageError("Invalid message type")
            
            # Serialize message
            message_json = message.to_json()
            
            # Determine target channel
            channel = self._get_agent_channel(message.recipient_id)
            
            # Publish with retry logic
            success = await self._publish_with_retry(channel, message_json)
            
            if success:
                # Store message for persistence if enabled
                if self.enable_persistence:
                    await self._store_message(message)
                
                logger.debug(f"Published message {message.message_id} to {channel}")
                return True
            else:
                raise MessageDeliveryError(f"Failed to publish message {message.message_id}")
                
        except Exception as e:
            logger.error(f"Error publishing message {message.message_id}: {e}")
            raise MessageDeliveryError(f"Message publication failed: {e}")
    
    async def subscribe_to_agent(self, agent_id: str, message_handler: Callable[[AgentMessage], None]) -> None:
        """
        Subscribe to messages for a specific agent
        
        Args:
            agent_id: Agent ID to subscribe for
            message_handler: Callback function to handle incoming messages
        """
        if not self._running:
            raise AgentCommError("Broker not initialized")
        
        channel = self._get_agent_channel(agent_id)
        self._subscriptions[channel] = message_handler
        
        # Start subscription task if not already running
        if not self._subscription_task or self._subscription_task.done():
            self._subscription_task = asyncio.create_task(self._subscription_loop())
        
        logger.info(f"Subscribed to messages for agent {agent_id} on channel {channel}")
    
    async def unsubscribe_agent(self, agent_id: str) -> None:
        """Unsubscribe from messages for a specific agent"""
        channel = self._get_agent_channel(agent_id)
        
        if channel in self._subscriptions:
            del self._subscriptions[channel]
            logger.info(f"Unsubscribed from messages for agent {agent_id}")
    
    async def get_pending_messages(self, agent_id: str) -> list[AgentMessage]:
        """
        Retrieve pending messages for an agent (if persistence is enabled)
        
        Args:
            agent_id: Agent ID to get messages for
            
        Returns:
            List of pending AgentMessage objects
        """
        if not self.enable_persistence:
            return []
        
        try:
            pending_key = f"pending:{agent_id}"
            message_data = await self._publish_client.lrange(pending_key, 0, -1)
            
            messages = []
            for data in message_data:
                try:
                    message = AgentMessage.from_json(data)
                    messages.append(message)
                except Exception as e:
                    logger.warning(f"Failed to parse stored message: {e}")
            
            # Clear pending messages
            await self._publish_client.delete(pending_key)
            
            logger.debug(f"Retrieved {len(messages)} pending messages for {agent_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving pending messages for {agent_id}: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the message broker
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Test Redis connection
            start_time = time.time()
            await self._publish_client.ping()
            response_time = time.time() - start_time
            
            # Get Redis info
            redis_info = await self._publish_client.info()
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "response_time_ms": round(response_time * 1000, 2),
                "active_subscriptions": len(self._subscriptions),
                "redis_memory_usage": redis_info.get("used_memory_human", "unknown"),
                "redis_version": redis_info.get("redis_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "error": str(e),
                "active_subscriptions": len(self._subscriptions)
            }
    
    # Private methods
    
    def _get_agent_channel(self, agent_id: str) -> str:
        """Get Redis channel name for agent"""
        return f"agent_comm:{agent_id}"
    
    async def _publish_with_retry(self, channel: str, message: str) -> bool:
        """Publish message with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                result = await self._publish_client.publish(channel, message)
                return result >= 0  # Redis returns number of subscribers
                
            except (ConnectionError, TimeoutError) as e:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Publish attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All publish attempts failed: {e}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error during publish: {e}")
                return False
        
        return False
    
    async def _store_message(self, message: AgentMessage) -> None:
        """Store message for offline agent retrieval"""
        try:
            pending_key = f"pending:{message.recipient_id}"
            message_json = message.to_json()
            
            # Add to pending list with TTL
            await self._publish_client.lpush(pending_key, message_json)
            await self._publish_client.expire(pending_key, message.ttl or self.message_ttl)
            
        except Exception as e:
            logger.warning(f"Failed to store message {message.message_id}: {e}")
    
    async def _subscription_loop(self) -> None:
        """Main subscription loop for handling incoming messages"""
        try:
            pubsub = self._pubsub_client.pubsub()
            
            # Subscribe to all channels we're interested in
            channels = list(self._subscriptions.keys())
            if channels:
                await pubsub.subscribe(*channels)
                logger.info(f"Subscribed to channels: {channels}")
            
            # Process messages
            while self._running:
                try:
                    # Check for new subscriptions
                    current_channels = set(self._subscriptions.keys())
                    subscribed_channels = set(channels)
                    
                    # Subscribe to new channels
                    new_channels = current_channels - subscribed_channels
                    if new_channels:
                        await pubsub.subscribe(*new_channels)
                        channels.extend(new_channels)
                        logger.debug(f"Added subscriptions: {new_channels}")
                    
                    # Unsubscribe from removed channels
                    removed_channels = subscribed_channels - current_channels
                    if removed_channels:
                        await pubsub.unsubscribe(*removed_channels)
                        channels = [c for c in channels if c not in removed_channels]
                        logger.debug(f"Removed subscriptions: {removed_channels}")
                    
                    # Get message with timeout
                    message = await asyncio.wait_for(pubsub.get_message(), timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        await self._handle_incoming_message(message)
                        
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Error in subscription loop: {e}")
                    await asyncio.sleep(1.0)
            
            await pubsub.close()
            
        except Exception as e:
            logger.error(f"Subscription loop failed: {e}")
    
    async def _handle_incoming_message(self, redis_message: Dict[str, Any]) -> None:
        """Handle incoming Redis message"""
        try:
            channel = redis_message['channel']
            data = redis_message['data']
            
            if channel in self._subscriptions:
                # Parse agent message
                try:
                    agent_message = AgentMessage.from_json(data)
                except Exception as e:
                    logger.error(f"Failed to parse message from {channel}: {e}")
                    return
                
                # Call message handler
                handler = self._subscriptions[channel]
                try:
                    # Handle both sync and async handlers
                    if asyncio.iscoroutinefunction(handler):
                        await handler(agent_message)
                    else:
                        handler(agent_message)
                        
                    logger.debug(f"Handled message {agent_message.message_id} from {channel}")
                    
                except Exception as e:
                    logger.error(f"Message handler failed for {agent_message.message_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for broker connections"""
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown() 