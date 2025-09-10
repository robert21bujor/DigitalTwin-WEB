"""
Agent Registry for Centralized Discovery
=======================================

Production-ready agent registry system for mapping users to agents, role-based discovery,
and agent lifecycle management. Supports both in-memory and persistent storage.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

import redis.asyncio as redis

from .schemas import AgentInfo, MessageIntent, AgentNotFoundError, AgentCommError

# Configure logging
logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Centralized agent registry for discovery and lifecycle management
    
    Features:
    - Agent registration and discovery
    - Role-based agent lookup
    - Capability matching
    - Health monitoring
    - Persistent storage (Redis + file backup)
    - Agent lifecycle management
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        backup_file: str = "agent_registry.json",
        health_check_interval: int = 60,
        agent_timeout: int = 300,
        enable_persistence: bool = True
    ):
        """
        Initialize agent registry
        
        Args:
            redis_url: Redis connection URL for persistence
            backup_file: Local backup file for registry data
            health_check_interval: Interval for agent health checks (seconds)
            agent_timeout: Time after which agents are considered offline (seconds)
            enable_persistence: Whether to use Redis for persistence
        """
        self.redis_url = redis_url
        self.backup_file = Path(backup_file)
        self.health_check_interval = health_check_interval
        self.agent_timeout = agent_timeout
        self.enable_persistence = enable_persistence
        
        # In-memory storage
        self._agents: Dict[str, AgentInfo] = {}
        self._user_agent_map: Dict[str, str] = {}  # user_name -> agent_id
        self._role_agents: Dict[str, Set[str]] = {}  # role -> set of agent_ids
        self._department_agents: Dict[str, Set[str]] = {}  # department -> set of agent_ids
        
        # Redis client for persistence
        self._redis_client: Optional[redis.Redis] = None
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("AgentRegistry initialized")
    
    async def initialize(self) -> None:
        """Initialize the agent registry"""
        try:
            # Initialize Redis if enabled
            if self.enable_persistence:
                self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis_client.ping()
                logger.info("Redis connection established for agent registry")
            
            # Load existing data
            await self._load_registry_data()
            
            # Start background tasks
            self._running = True
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(f"AgentRegistry initialized with {len(self._agents)} agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentRegistry: {e}")
            raise AgentCommError(f"Registry initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent registry"""
        self._running = False
        
        # Stop background tasks
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Save data before shutdown
        await self._save_registry_data()
        
        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()
        
        logger.info("AgentRegistry shutdown complete")
    
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """
        Register a new agent or update existing agent
        
        Args:
            agent_info: AgentInfo object with agent details
            
        Returns:
            bool: True if registration successful
        """
        try:
            agent_id = agent_info.agent_id
            
            # Update timestamps
            agent_info.last_seen = datetime.utcnow()
            if agent_id not in self._agents:
                agent_info.created_at = datetime.utcnow()
            
            # Store agent info
            self._agents[agent_id] = agent_info
            
            # Update mappings
            self._user_agent_map[agent_info.user_name] = agent_id
            
            # Update role mapping
            if agent_info.role not in self._role_agents:
                self._role_agents[agent_info.role] = set()
            self._role_agents[agent_info.role].add(agent_id)
            
            # Update department mapping
            if agent_info.department:
                if agent_info.department not in self._department_agents:
                    self._department_agents[agent_info.department] = set()
                self._department_agents[agent_info.department].add(agent_id)
            
            # Save to persistent storage
            await self._save_agent_data(agent_info)
            
            logger.info(f"Registered agent {agent_id} for user {agent_info.user_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_info.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry
        
        Args:
            agent_id: Agent ID to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if agent_id not in self._agents:
                logger.warning(f"Attempted to unregister unknown agent: {agent_id}")
                return False
            
            agent_info = self._agents[agent_id]
            
            # Remove from mappings
            if agent_info.user_name in self._user_agent_map:
                del self._user_agent_map[agent_info.user_name]
            
            if agent_info.role in self._role_agents:
                self._role_agents[agent_info.role].discard(agent_id)
                if not self._role_agents[agent_info.role]:
                    del self._role_agents[agent_info.role]
            
            if agent_info.department and agent_info.department in self._department_agents:
                self._department_agents[agent_info.department].discard(agent_id)
                if not self._department_agents[agent_info.department]:
                    del self._department_agents[agent_info.department]
            
            # Remove from storage
            del self._agents[agent_id]
            
            # Remove from persistent storage
            await self._remove_agent_data(agent_id)
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by agent ID"""
        return self._agents.get(agent_id)
    
    async def get_agent_by_user(self, user_name: str) -> Optional[AgentInfo]:
        """Get agent information by user name"""
        agent_id = self._user_agent_map.get(user_name)
        if agent_id:
            return self._agents.get(agent_id)
        return None
    
    async def find_agents_by_role(self, role: str) -> List[AgentInfo]:
        """Find all agents with a specific role"""
        agent_ids = self._role_agents.get(role, set())
        return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
    
    async def find_agents_by_department(self, department: str) -> List[AgentInfo]:
        """Find all agents in a specific department"""
        agent_ids = self._department_agents.get(department, set())
        return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
    
    async def find_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """Find agents that have a specific capability"""
        matching_agents = []
        for agent in self._agents.values():
            if capability in agent.capabilities:
                matching_agents.append(agent)
        return matching_agents
    
    async def find_agents_by_intent(self, intent: MessageIntent) -> List[AgentInfo]:
        """Find agents that support a specific message intent"""
        matching_agents = []
        for agent in self._agents.values():
            if intent in agent.supports_intents:
                matching_agents.append(agent)
        return matching_agents
    
    async def get_online_agents(self) -> List[AgentInfo]:
        """Get all currently online agents"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.agent_timeout)
        online_agents = []
        
        for agent in self._agents.values():
            if agent.status == "online" and agent.last_seen > cutoff_time:
                online_agents.append(agent)
        
        return online_agents
    
    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status"""
        try:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                self._agents[agent_id].last_seen = datetime.utcnow()
                
                # Save to persistent storage
                await self._save_agent_data(self._agents[agent_id])
                
                logger.debug(f"Updated status for agent {agent_id}: {status}")
                return True
            else:
                logger.warning(f"Attempted to update status for unknown agent: {agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update status for agent {agent_id}: {e}")
            return False
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Record agent heartbeat"""
        return await self.update_agent_status(agent_id, "online")
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        online_agents = await self.get_online_agents()
        
        role_counts = {}
        for role, agent_ids in self._role_agents.items():
            role_counts[role] = len(agent_ids)
        
        department_counts = {}
        for dept, agent_ids in self._department_agents.items():
            department_counts[dept] = len(agent_ids)
        
        return {
            "total_agents": len(self._agents),
            "online_agents": len(online_agents),
            "offline_agents": len(self._agents) - len(online_agents),
            "roles": role_counts,
            "departments": department_counts,
            "registry_health": "healthy" if self._running else "stopped"
        }
    
    async def discover_agents(
        self,
        role: Optional[str] = None,
        department: Optional[str] = None,
        capability: Optional[str] = None,
        intent: Optional[MessageIntent] = None,
        online_only: bool = True
    ) -> List[AgentInfo]:
        """
        Discover agents based on multiple criteria
        
        Args:
            role: Filter by role
            department: Filter by department
            capability: Filter by capability
            intent: Filter by supported intent
            online_only: Only return online agents
            
        Returns:
            List of matching AgentInfo objects
        """
        # Start with all agents or online agents
        if online_only:
            agents = await self.get_online_agents()
        else:
            agents = list(self._agents.values())
        
        # Apply filters
        if role:
            agents = [a for a in agents if a.role == role]
        
        if department:
            agents = [a for a in agents if a.department == department]
        
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        
        if intent:
            agents = [a for a in agents if intent in a.supports_intents]
        
        return agents
    
    # Private methods
    
    async def _load_registry_data(self) -> None:
        """Load registry data from persistent storage"""
        try:
            # Try Redis first
            if self._redis_client:
                await self._load_from_redis()
            else:
                # Fallback to file
                await self._load_from_file()
                
        except Exception as e:
            logger.error(f"Failed to load registry data: {e}")
            # Continue with empty registry
    
    async def _save_registry_data(self) -> None:
        """Save registry data to persistent storage"""
        try:
            # Save to both Redis and file for redundancy
            if self._redis_client:
                await self._save_to_redis()
            
            await self._save_to_file()
            
        except Exception as e:
            logger.error(f"Failed to save registry data: {e}")
    
    async def _load_from_redis(self) -> None:
        """Load agent data from Redis"""
        try:
            agent_keys = await self._redis_client.keys("agent_registry:*")
            
            for key in agent_keys:
                agent_data = await self._redis_client.get(key)
                if agent_data:
                    agent_info = AgentInfo.model_validate_json(agent_data)
                    
                    # Rebuild in-memory structures
                    agent_id = agent_info.agent_id
                    self._agents[agent_id] = agent_info
                    self._user_agent_map[agent_info.user_name] = agent_id
                    
                    if agent_info.role not in self._role_agents:
                        self._role_agents[agent_info.role] = set()
                    self._role_agents[agent_info.role].add(agent_id)
                    
                    if agent_info.department:
                        if agent_info.department not in self._department_agents:
                            self._department_agents[agent_info.department] = set()
                        self._department_agents[agent_info.department].add(agent_id)
            
            logger.info(f"Loaded {len(self._agents)} agents from Redis")
            
        except Exception as e:
            logger.error(f"Failed to load from Redis: {e}")
            raise
    
    async def _save_to_redis(self) -> None:
        """Save agent data to Redis"""
        try:
            for agent_id, agent_info in self._agents.items():
                key = f"agent_registry:{agent_id}"
                await self._redis_client.set(key, agent_info.model_dump_json())
            
            logger.debug(f"Saved {len(self._agents)} agents to Redis")
            
        except Exception as e:
            logger.error(f"Failed to save to Redis: {e}")
    
    async def _load_from_file(self) -> None:
        """Load agent data from backup file"""
        try:
            if self.backup_file.exists():
                with open(self.backup_file, 'r') as f:
                    data = json.load(f)
                
                for agent_data in data.get('agents', []):
                    agent_info = AgentInfo(**agent_data)
                    
                    # Rebuild in-memory structures
                    agent_id = agent_info.agent_id
                    self._agents[agent_id] = agent_info
                    self._user_agent_map[agent_info.user_name] = agent_id
                    
                    if agent_info.role not in self._role_agents:
                        self._role_agents[agent_info.role] = set()
                    self._role_agents[agent_info.role].add(agent_id)
                    
                    if agent_info.department:
                        if agent_info.department not in self._department_agents:
                            self._department_agents[agent_info.department] = set()
                        self._department_agents[agent_info.department].add(agent_id)
                
                logger.info(f"Loaded {len(self._agents)} agents from file")
            
        except Exception as e:
            logger.error(f"Failed to load from file: {e}")
    
    async def _save_to_file(self) -> None:
        """Save agent data to backup file"""
        try:
            agents_data = []
            for agent_info in self._agents.values():
                agent_dict = agent_info.dict()
                # Convert datetime objects to strings
                agent_dict['created_at'] = agent_dict['created_at'].isoformat()
                agent_dict['last_seen'] = agent_dict['last_seen'].isoformat()
                agents_data.append(agent_dict)
            
            data = {
                'agents': agents_data,
                'saved_at': datetime.utcnow().isoformat()
            }
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.backup_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            temp_file.replace(self.backup_file)
            logger.debug(f"Saved {len(self._agents)} agents to file")
            
        except Exception as e:
            logger.error(f"Failed to save to file: {e}")
    
    async def _save_agent_data(self, agent_info: AgentInfo) -> None:
        """Save individual agent data to persistent storage"""
        try:
            if self._redis_client:
                key = f"agent_registry:{agent_info.agent_id}"
                await self._redis_client.set(key, agent_info.model_dump_json())
            
        except Exception as e:
            logger.error(f"Failed to save agent data for {agent_info.agent_id}: {e}")
    
    async def _remove_agent_data(self, agent_id: str) -> None:
        """Remove agent data from persistent storage"""
        try:
            if self._redis_client:
                key = f"agent_registry:{agent_id}"
                await self._redis_client.delete(key)
            
        except Exception as e:
            logger.error(f"Failed to remove agent data for {agent_id}: {e}")
    
    async def _health_check_loop(self) -> None:
        """Background task for agent health monitoring"""
        while self._running:
            try:
                await self._check_agent_health()
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)  # Short delay before retry
    
    async def _check_agent_health(self) -> None:
        """Check health of all registered agents"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.agent_timeout)
        offline_count = 0
        
        for agent_id, agent_info in self._agents.items():
            if agent_info.last_seen < cutoff_time and agent_info.status != "offline":
                agent_info.status = "offline"
                await self._save_agent_data(agent_info)
                offline_count += 1
        
        if offline_count > 0:
            logger.info(f"Marked {offline_count} agents as offline during health check") 