"""
Universal Agent Communication Mixin
===================================

Generic mixin to add communication capabilities to ANY agent type.
No predefined roles or business logic - completely modular.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime

from ..sender import MessageSender
from ..registry import AgentRegistry
from ..schemas import MessageIntent, AgentMessage, MessagePayload, AgentInfo

logger = logging.getLogger(__name__)


class UniversalAgentMixin:
    """
    Universal mixin to add communication capabilities to ANY agent
    
    Features:
    - Works with any agent role/type/department
    - No hardcoded business logic
    - Completely configurable
    - Dynamic capability registration
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comm_initialized = False
        self._message_sender = None
        self._agent_registry = None
        self._communication_handlers = {}
        self._agent_config = {}
        
    async def initialize_agent_communication(
        self,
        agent_id: str,
        role: str,                    # Any role: "engineer", "designer", "analyst", etc.
        department: str,              # Any department: "engineering", "design", "data", etc.
        capabilities: List[str],      # Any capabilities: ["python", "figma", "sql", etc.]
        user_name: str = None,
        redis_url: str = "redis://localhost:6379",
        custom_handlers: Optional[Dict[MessageIntent, Callable]] = None
    ) -> None:
        """
        Initialize communication capabilities for ANY agent type
        
        Args:
            agent_id: Unique identifier (e.g., "agent.engineer.john")
            role: Agent role (any string - "engineer", "designer", "analyst")
            department: Department (any string - "engineering", "design", "data")
            capabilities: What this agent can do (any list of strings)
            user_name: Human counterpart name
            redis_url: Redis connection URL
            custom_handlers: Optional custom message handlers
        """
        if self._comm_initialized:
            return
            
        try:
            # Store agent config
            self._agent_config = {
                "agent_id": agent_id,
                "role": role,
                "department": department,
                "capabilities": capabilities,
                "user_name": user_name or f"Agent {role}"
            }
            
            # Initialize message sender
            self._message_sender = MessageSender(
                redis_url=redis_url,
                sender_id=agent_id
            )
            await self._message_sender.initialize()
            
            # Initialize agent registry
            self._agent_registry = AgentRegistry(redis_url=redis_url)
            await self._agent_registry.initialize()
            
            # Register this agent
            agent_info = AgentInfo(
                agent_id=agent_id,
                role=role,
                department=department,
                capabilities=capabilities,
                user_name=user_name or f"Agent {role}",
                status="online",
                last_seen=datetime.utcnow(),
                channel=f"agent.{role}.{department}"
            )
            
            await self._agent_registry.register_agent(agent_info)
            
            # Set up message handlers
            self._setup_universal_handlers(custom_handlers or {})
            
            self._comm_initialized = True
            logger.info(f"Communication initialized for {agent_id} ({role})")
            
        except Exception as e:
            logger.error(f"Failed to initialize communication for {agent_id}: {e}")
            raise
    
    async def shutdown_agent_communication(self) -> None:
        """Shutdown communication capabilities"""
        if not self._comm_initialized:
            return
            
        try:
            if self._message_sender:
                await self._message_sender.shutdown()
            if self._agent_registry:
                await self._agent_registry.shutdown()
            
            self._comm_initialized = False
            logger.info("Agent communication shutdown")
            
        except Exception as e:
            logger.error(f"Communication shutdown error: {e}")
    
    def _setup_universal_handlers(self, custom_handlers: Dict[MessageIntent, Callable]) -> None:
        """Set up universal message handlers"""
        # Default handlers
        default_handlers = {
            MessageIntent.REQUEST_KNOWLEDGE: self._handle_knowledge_request,
            MessageIntent.ASSIGN_TASK: self._handle_task_assignment,
            MessageIntent.AGENT_STATUS: self._handle_status_request,
            MessageIntent.GET_ROADMAP: self._handle_roadmap_request,
            MessageIntent.HEALTH_CHECK: self._handle_health_check,
            MessageIntent.CAPABILITY_QUERY: self._handle_capability_query,
        }
        
        # Merge with custom handlers (custom takes precedence)
        self._communication_handlers = {**default_handlers, **custom_handlers}
    
    # ===============================
    # UNIVERSAL COMMUNICATION METHODS
    # ===============================
    
    async def send_message_to_agent(
        self,
        target_agent_role: str,
        message: str,
        intent: MessageIntent = MessageIntent.REQUEST_KNOWLEDGE,
        context: Optional[Dict[str, Any]] = None,
        wait_for_response: bool = False,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Send message to any agent type
        
        Args:
            target_agent_role: Role of target agent (any string)
            message: Message content
            intent: Message intent
            context: Additional context
            wait_for_response: Whether to wait for response
            timeout: Response timeout
            
        Returns:
            Agent response or None
        """
        if not self._comm_initialized:
            logger.error("Communication not initialized")
            return None
            
        try:
            # Find target agent
            target_agents = await self._message_sender.discover_agents(role=target_agent_role)
            
            if not target_agents:
                logger.error(f"No {target_agent_role} agent found")
                return {"error": f"No {target_agent_role} agent available"}
            
            target_agent = target_agents[0]
            
            # Send message
            response = await self._message_sender.send_message(
                recipient_id=target_agent.agent_id,
                intent=intent,
                data={
                    "message": message,
                    "sender_role": self._agent_config["role"],
                    "sender_department": self._agent_config["department"],
                    "context": context or {},
                    "timestamp": datetime.utcnow().isoformat()
                },
                requires_response=wait_for_response
            )
            
            if isinstance(response, AgentMessage):
                return {
                    "success": True,
                    "data": response.payload.data,
                    "from_agent": target_agent.agent_id,
                    "from_role": target_agent.role,
                    "timestamp": response.timestamp.isoformat()
                }
            else:
                return {"error": f"No response from {target_agent_role}"}
                
        except Exception as e:
            logger.error(f"Message sending failed: {e}")
            return {"error": str(e)}
    
    async def request_information_from_agent(
        self,
        target_agent_role: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Request information from any agent type
        
        Examples:
        - request_information_from_agent("data_scientist", "What's the user churn rate?")
        - request_information_from_agent("devops_engineer", "What's the system status?")
        - request_information_from_agent("designer", "Can you review this mockup?")
        """
        return await self.send_message_to_agent(
            target_agent_role=target_agent_role,
            message=query,
            intent=MessageIntent.REQUEST_KNOWLEDGE,
            context=context,
            wait_for_response=True,
            timeout=timeout
        )
    
    async def assign_task_to_agent(
        self,
        target_agent_role: str,
        task_description: str,
        priority: str = "normal",
        deadline: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Assign task to any agent type
        
        Examples:
        - assign_task_to_agent("content_writer", "Write blog post about ML")
        - assign_task_to_agent("qa_engineer", "Test the new API endpoints")
        - assign_task_to_agent("designer", "Create mobile app wireframes")
        """
        return await self.send_message_to_agent(
            target_agent_role=target_agent_role,
            message=task_description,
            intent=MessageIntent.ASSIGN_TASK,
            context={
                "priority": priority,
                "deadline": deadline,
                "task_type": "assignment",
                **(context or {})
            },
            wait_for_response=True
        )
    
    async def broadcast_to_department(
        self,
        department: str,
        message: str,
        intent: MessageIntent = MessageIntent.AGENT_STATUS,
        data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Broadcast message to all agents in any department
        
        Examples:
        - broadcast_to_department("engineering", "Code freeze starts tomorrow")
        - broadcast_to_department("design", "New brand guidelines available")
        - broadcast_to_department("data", "Monthly analytics review scheduled")
        """
        if not self._comm_initialized:
            logger.error("Communication not initialized")
            return []
            
        try:
            # Find all agents in department
            dept_agents = await self._message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            sent_to = []
            for agent in dept_agents:
                try:
                    await self._message_sender.send_message(
                        recipient_id=agent.agent_id,
                        intent=intent,
                        data={
                            "message": message,
                            "sender_role": self._agent_config["role"],
                            "sender_department": self._agent_config["department"],
                            "broadcast_data": data or {},
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    sent_to.append(agent.agent_id)
                except Exception as e:
                    logger.error(f"Failed to send to {agent.agent_id}: {e}")
            
            return sent_to
            
        except Exception as e:
            logger.error(f"Department broadcast failed: {e}")
            return []
    
    async def discover_agents_by_capability(
        self, 
        capability: str
    ) -> List[Dict[str, Any]]:
        """
        Find agents by capability (not role)
        
        Examples:
        - discover_agents_by_capability("python") → finds all Python developers
        - discover_agents_by_capability("figma") → finds all Figma users
        - discover_agents_by_capability("sql") → finds all SQL experts
        """
        if not self._comm_initialized:
            return []
            
        try:
            agents = await self._message_sender.discover_agents(
                capability=capability,
                online_only=True
            )
            
            return [{
                "agent_id": agent.agent_id,
                "role": agent.role,
                "department": agent.department,
                "capabilities": agent.capabilities,
                "user_name": agent.user_name
            } for agent in agents]
            
        except Exception as e:
            logger.error(f"Capability discovery failed: {e}")
            return []
    
    async def get_department_agents(self, department: str) -> List[Dict[str, Any]]:
        """Get all agents in any department"""
        if not self._comm_initialized:
            return []
            
        try:
            agents = await self._message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            return [{
                "agent_id": agent.agent_id,
                "role": agent.role,
                "capabilities": agent.capabilities,
                "status": agent.status
            } for agent in agents]
            
        except Exception as e:
            logger.error(f"Department discovery failed: {e}")
            return []
    
    # ===============================
    # UNIVERSAL MESSAGE HANDLERS
    # ===============================
    
    async def _handle_knowledge_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Universal knowledge request handler
        Override this in your agent to provide specific responses
        """
        query = message.payload.data.get("message", "")
        sender_role = message.payload.data.get("sender_role", "unknown")
        
        # Default response - override this in your specific agent
        return {
            "status": "received",
            "query": query,
            "response": f"Knowledge request received from {sender_role}",
            "agent_role": self._agent_config["role"],
            "capabilities": self._agent_config["capabilities"],
            "handler": "universal_knowledge_handler"
        }
    
    async def _handle_task_assignment(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Universal task assignment handler
        Override this in your agent to handle tasks specifically
        """
        task_description = message.payload.data.get("message", "")
        priority = message.payload.data.get("context", {}).get("priority", "normal")
        deadline = message.payload.data.get("context", {}).get("deadline")
        
        # Default response - override this in your specific agent
        return {
            "accepted": True,
            "task": task_description,
            "priority": priority,
            "deadline": deadline,
            "estimated_completion": "TBD",
            "agent_role": self._agent_config["role"],
            "handler": "universal_task_handler"
        }
    
    async def _handle_status_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Universal status request handler"""
        return {
            "status": "online",
            "agent_role": self._agent_config["role"],
            "department": self._agent_config["department"],
            "capabilities": self._agent_config["capabilities"],
            "current_tasks": [],
            "availability": "available",
            "handler": "universal_status_handler"
        }
    
    async def _handle_roadmap_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Universal roadmap request handler"""
        timeframe = message.payload.data.get("context", {}).get("timeframe", "Q1")
        
        return {
            "timeframe": timeframe,
            "roadmap": f"No specific roadmap available for {self._agent_config['role']}",
            "agent_role": self._agent_config["role"],
            "handler": "universal_roadmap_handler"
        }
    
    async def _handle_health_check(self, message: AgentMessage) -> Dict[str, Any]:
        """Universal health check handler"""
        return {
            "health": "healthy",
            "agent_role": self._agent_config["role"],
            "uptime": "unknown",
            "last_activity": datetime.utcnow().isoformat(),
            "handler": "universal_health_handler"
        }
    
    async def _handle_capability_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Universal capability query handler"""
        return {
            "capabilities": self._agent_config["capabilities"],
            "agent_role": self._agent_config["role"],
            "department": self._agent_config["department"],
            "handler": "universal_capability_handler"
        }
    
    # ===============================
    # HANDLER REGISTRATION
    # ===============================
    
    def register_message_handler(
        self, 
        intent: MessageIntent, 
        handler: Callable[[AgentMessage], Dict[str, Any]]
    ) -> None:
        """Register a custom handler for a specific message intent"""
        self._communication_handlers[intent] = handler
        logger.info(f"Registered custom handler for {intent}")
    
    async def handle_incoming_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Handle incoming communication messages"""
        intent = message.intent
        
        if intent in self._communication_handlers:
            try:
                return await self._communication_handlers[intent](message)
            except Exception as e:
                logger.error(f"Handler error for {intent}: {e}")
                return {"error": f"Handler failed: {e}"}
        else:
            logger.warning(f"No handler for intent: {intent}")
            return {"error": f"No handler for intent: {intent}"}


# =================================
# EXAMPLE USAGE FOR ANY AGENT TYPE
# =================================

class UniversalAgentExample(UniversalAgentMixin):
    """
    Example showing how to create ANY agent type with communication
    """
    
    def __init__(self, agent_type: str, name: str, department: str, capabilities: List[str]):
        super().__init__()
        self.agent_type = agent_type  # Any type: "engineer", "designer", "analyst", etc.
        self.name = name
        self.department = department
        self.capabilities = capabilities
        self.agent_data = {}
        
    async def initialize(self):
        """Initialize any agent type with communication"""
        # Setup agent-specific data
        await self.setup_agent_data()
        
        # Add communication capabilities
        await self.initialize_agent_communication(
            agent_id=f"agent.{self.agent_type}.{self.name.lower().replace(' ', '')}",
            role=self.agent_type,
            department=self.department,
            capabilities=self.capabilities,
            user_name=self.name
        )
    
    async def setup_agent_data(self):
        """Setup data for any agent type"""
        # This can be customized for any agent type
        self.agent_data = {
            "agent_type": self.agent_type,
            "name": self.name,
            "department": self.department,
            "initialized_at": datetime.utcnow().isoformat(),
            "status": "ready"
        }
    
    # Override handlers with agent-specific logic
    async def _handle_knowledge_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle knowledge requests with agent-specific logic"""
        query = message.payload.data.get("message", "").lower()
        sender_role = message.payload.data.get("sender_role", "unknown")
        
        # Return agent-specific information
        return {
            "status": "success",
            "agent_type": self.agent_type,
            "data": self.agent_data,
            "capabilities": self.capabilities,
            "response": f"{self.agent_type} agent response for: {query}",
            "sender_acknowledged": sender_role
        }


# Quick helper function
def create_agent_with_communication(
    agent_type: str, 
    name: str, 
    department: str, 
    capabilities: List[str]
) -> UniversalAgentExample:
    """
    Quick helper to create any agent type with communication
    
    Examples:
    - create_agent_with_communication("data_scientist", "Alice", "analytics", ["python", "sql", "ml"])
    - create_agent_with_communication("devops_engineer", "Bob", "engineering", ["docker", "kubernetes", "aws"])
    - create_agent_with_communication("ux_designer", "Carol", "design", ["figma", "sketch", "user_research"])
    """
    return UniversalAgentExample(agent_type, name, department, capabilities)


# ===============================
# EXAMPLE FOR ANY ORGANIZATION
# ===============================

async def demo_universal_agents():
    """Demo creating and communicating with any agent types"""
    print("🌐 Universal Agent Communication Demo")
    print("Works with ANY agent types!")
    
    # Create different agent types (not predefined!)
    agents = [
        create_agent_with_communication("data_scientist", "Alice", "analytics", ["python", "sql", "ml"]),
        create_agent_with_communication("devops_engineer", "Bob", "engineering", ["docker", "k8s", "aws"]),
        create_agent_with_communication("ux_designer", "Carol", "design", ["figma", "research", "prototyping"]),
        create_agent_with_communication("content_writer", "Dave", "marketing", ["writing", "seo", "social_media"])
    ]
    
    try:
        # Initialize all agents
        for agent in agents:
            await agent.initialize()
            print(f"✅ {agent.agent_type} agent '{agent.name}' initialized")
        
        # Test cross-agent communication
        data_scientist = agents[0]
        
        # Data scientist asks devops engineer about system status
        response = await data_scientist.request_information_from_agent(
            "devops_engineer",
            "What's the current system performance?"
        )
        print(f"\n🔄 Data scientist → DevOps: {response}")
        
        # Data scientist asks UX designer for user insights
        response = await data_scientist.request_information_from_agent(
            "ux_designer", 
            "What user behavior patterns should I analyze?"
        )
        print(f"\n🔄 Data scientist → UX Designer: {response}")
        
    finally:
        # Cleanup
        for agent in agents:
            await agent.shutdown_agent_communication()
        print(f"\n✅ All agents shutdown")


if __name__ == "__main__":
    asyncio.run(demo_universal_agents()) 