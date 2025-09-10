"""
Agent Communication Integration
==============================

Mixin classes and utilities to integrate communication capabilities
with your existing digital twin agents (CMO, CSO, etc.).
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime

from ..base_agent import BaseAgent
from ..sender import MessageSender
from ..registry import AgentRegistry
from ..schemas import MessageIntent, AgentMessage, MessagePayload, AgentInfo

logger = logging.getLogger(__name__)


class AgentCommunicationMixin:
    """
    Mixin to add communication capabilities to existing agents
    
    Add this to your existing CMO, CSO, and other agents to enable:
    - Agent-to-agent communication
    - Cross-department information requests
    - Integration with dashboard interface
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comm_initialized = False
        self._message_sender = None
        self._agent_registry = None
        self._communication_handlers = {}
        
    async def initialize_communication(
        self,
        agent_id: str,
        role: str,
        department: str,
        capabilities: List[str],
        user_name: str = None,
        redis_url: str = "redis://localhost:6379"
    ) -> None:
        """
        Initialize communication capabilities for this agent
        
        Args:
            agent_id: Unique identifier (e.g., "agent.cmo.john")
            role: Agent role (e.g., "cmo", "cso")
            department: Department (e.g., "marketing", "sales")
            capabilities: What this agent can do
            user_name: Human counterpart name
            redis_url: Redis connection URL
        """
        if self._comm_initialized:
            return
            
        try:
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
                user_name=user_name or f"Agent {role.upper()}",
                status="online",
                last_seen=datetime.utcnow(),
                channel=f"agent.{role}.{department}"
            )
            
            await self._agent_registry.register_agent(agent_info)
            
            # Set up default communication handlers
            self._setup_default_handlers()
            
            self._comm_initialized = True
            logger.info(f"Communication initialized for {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize communication for {agent_id}: {e}")
            raise
    
    async def shutdown_communication(self) -> None:
        """Shutdown communication capabilities"""
        if not self._comm_initialized:
            return
            
        try:
            if self._message_sender:
                await self._message_sender.shutdown()
            if self._agent_registry:
                await self._agent_registry.shutdown()
            
            self._comm_initialized = False
            logger.info("Communication shutdown")
            
        except Exception as e:
            logger.error(f"Communication shutdown error: {e}")
    
    def _setup_default_handlers(self) -> None:
        """Set up default message handlers"""
        self._communication_handlers = {
            MessageIntent.REQUEST_KNOWLEDGE: self._handle_knowledge_request,
            MessageIntent.ASSIGN_TASK: self._handle_task_assignment,
            MessageIntent.AGENT_STATUS: self._handle_status_update,
            MessageIntent.GET_ROADMAP: self._handle_roadmap_request,
        }
    
    # Communication methods for existing agents
    
    async def request_info_from_agent(
        self,
        target_role: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Request information from another agent
        
        Usage in your existing agent:
        response = await self.request_info_from_agent("cso", "What's the Q4 sales forecast?")
        """
        if not self._comm_initialized:
            logger.error("Communication not initialized")
            return None
            
        try:
            # Find target agent
            target_agents = await self._message_sender.discover_agents(role=target_role)
            
            if not target_agents:
                logger.error(f"No {target_role} agent found")
                return {"error": f"No {target_role} agent available"}
            
            target_agent = target_agents[0]
            
            # Send knowledge request
            response = await self._message_sender.request_knowledge(
                agent_id=target_agent.agent_id,
                query=query,
                context=context or {},
                wait_for_response=True
            )
            
            if isinstance(response, AgentMessage):
                return {
                    "success": True,
                    "data": response.payload.data,
                    "from_agent": target_agent.agent_id,
                    "timestamp": response.timestamp.isoformat()
                }
            else:
                return {"error": f"No response from {target_role}"}
                
        except Exception as e:
            logger.error(f"Info request failed: {e}")
            return {"error": str(e)}
    
    async def broadcast_to_department(
        self,
        department: str,
        message: str,
        intent: MessageIntent = MessageIntent.AGENT_STATUS,
        data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Broadcast message to all agents in a department
        
        Usage:
        sent_to = await self.broadcast_to_department("sales", "Q4 targets updated")
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
    
    async def get_department_status(self, department: str) -> List[Dict[str, Any]]:
        """Get status of all agents in a department"""
        if not self._comm_initialized:
            return []
            
        try:
            agents = await self._message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            status_list = []
            for agent in agents:
                status = await self._message_sender.get_agent_status(agent.agent_id)
                if status:
                    status_list.append({
                        "agent_id": agent.agent_id,
                        "role": agent.role,
                        "status": status,
                        "capabilities": agent.capabilities
                    })
            
            return status_list
            
        except Exception as e:
            logger.error(f"Department status request failed: {e}")
            return []
    
    async def assign_task_to_agent(
        self,
        target_role: str,
        task_description: str,
        priority: str = "medium",
        deadline: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Assign a task to another agent
        
        Usage:
        result = await self.assign_task_to_agent(
            "seo_specialist", 
            "Optimize landing page for Q4 campaign",
            priority="high",
            deadline="2024-01-15"
        )
        """
        if not self._comm_initialized:
            return None
            
        try:
            target_agents = await self._message_sender.discover_agents(role=target_role)
            
            if not target_agents:
                return {"error": f"No {target_role} agent available"}
            
            target_agent = target_agents[0]
            
            response = await self._message_sender.assign_task(
                agent_id=target_agent.agent_id,
                task_description=task_description,
                priority=priority,
                deadline=deadline,
                context=context or {},
                wait_for_response=True
            )
            
            if isinstance(response, AgentMessage):
                return {
                    "success": True,
                    "task_accepted": response.payload.data.get("accepted", False),
                    "assigned_to": target_agent.agent_id,
                    "response": response.payload.data
                }
            else:
                return {"error": f"No response from {target_role}"}
                
        except Exception as e:
            logger.error(f"Task assignment failed: {e}")
            return {"error": str(e)}
    
    # Default message handlers (can be overridden)
    
    async def _handle_knowledge_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle knowledge requests from other agents (override in your agent)"""
        query = message.payload.data.get("query", "")
        requester_role = message.payload.data.get("requester_role", "unknown")
        
        # Default response - override this in your agent
        return {
            "status": "received",
            "query": query,
            "response": f"Knowledge request received from {requester_role}",
            "handler": "default_knowledge_handler"
        }
    
    async def _handle_task_assignment(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle task assignments (override in your agent)"""
        task_description = message.payload.data.get("task_description", "")
        priority = message.payload.data.get("priority", "medium")
        
        # Default response - override this in your agent
        return {
            "accepted": True,
            "task": task_description,
            "priority": priority,
            "estimated_completion": "TBD",
            "handler": "default_task_handler"
        }
    
    async def _handle_status_update(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle status update requests (override in your agent)"""
        return {
            "status": "online",
            "current_tasks": [],
            "availability": "available",
            "handler": "default_status_handler"
        }
    
    async def _handle_roadmap_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle roadmap requests (override in your agent)"""
        timeframe = message.payload.data.get("timeframe", "Q1")
        
        return {
            "timeframe": timeframe,
            "roadmap": "No roadmap available",
            "handler": "default_roadmap_handler"
        }
    
    # Handler registration for custom intents
    
    def register_communication_handler(
        self, 
        intent: MessageIntent, 
        handler: Callable[[AgentMessage], Dict[str, Any]]
    ) -> None:
        """Register a custom handler for a specific message intent"""
        self._communication_handlers[intent] = handler
        logger.info(f"Registered handler for {intent}")
    
    async def handle_communication_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
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


# Integration examples for existing agents

class ExistingAgentIntegration:
    """Examples of how to integrate with existing agents"""
    
    @staticmethod
    def example_cmo_agent_integration():
        """Example: Add communication to existing CMO agent"""
        
        # Your existing CMO agent class
        class CMOAgent(AgentCommunicationMixin):
            def __init__(self, name: str):
                super().__init__()
                self.name = name
                self.campaigns = []
                self.performance_data = {}
            
            async def initialize(self):
                """Initialize both your agent and communication"""
                # Initialize your existing agent logic
                await self.setup_campaigns()
                
                # Initialize communication
                await self.initialize_communication(
                    agent_id=f"agent.cmo.{self.name.lower().replace(' ', '')}",
                    role="cmo",
                    department="marketing",
                    capabilities=["campaign_management", "brand_strategy", "content_strategy"],
                    user_name=self.name
                )
            
            async def setup_campaigns(self):
                """Your existing agent logic"""
                self.campaigns = ["Q4 Holiday Campaign", "Brand Awareness Drive"]
                
            # Override communication handlers with your logic
            async def _handle_knowledge_request(self, message: AgentMessage) -> Dict[str, Any]:
                """Handle knowledge requests with real marketing data"""
                query = message.payload.data.get("query", "")
                requester_role = message.payload.data.get("requester_role", "unknown")
                
                # Your real logic here
                if "campaign" in query.lower():
                    return {
                        "status": "success",
                        "campaigns": self.campaigns,
                        "performance": self.performance_data,
                        "response": f"Here are our current campaigns for {requester_role}"
                    }
                elif "marketing data" in query.lower():
                    return {
                        "status": "success",
                        "metrics": {
                            "leads_generated": 1250,
                            "conversion_rate": 0.045,
                            "cost_per_lead": 28.50
                        },
                        "response": "Current marketing performance metrics"
                    }
                else:
                    return {
                        "status": "success",
                        "response": f"General marketing info for: {query}"
                    }
            
            # Your existing methods can now use communication
            async def collaborate_with_sales(self, question: str):
                """Example: CMO asking CSO for sales data"""
                response = await self.request_info_from_agent("cso", question)
                
                if response and response.get("success"):
                    sales_data = response["data"]
                    # Use sales data to adjust marketing strategy
                    return f"Adjusted marketing strategy based on sales data: {sales_data}"
                else:
                    return "Could not get sales data"
        
        return CMOAgent
    
    @staticmethod
    def example_cso_agent_integration():
        """Example: Add communication to existing CSO agent"""
        
        class CSOAgent(AgentCommunicationMixin):
            def __init__(self, name: str):
                super().__init__()
                self.name = name
                self.pipeline_data = {}
                self.forecasts = {}
            
            async def initialize(self):
                """Initialize both your agent and communication"""
                # Initialize your existing agent logic
                await self.setup_sales_data()
                
                # Initialize communication
                await self.initialize_communication(
                    agent_id=f"agent.cso.{self.name.lower().replace(' ', '')}",
                    role="cso",
                    department="sales",
                    capabilities=["sales_forecasting", "pipeline_management", "revenue_analysis"],
                    user_name=self.name
                )
            
            async def setup_sales_data(self):
                """Your existing agent logic"""
                self.pipeline_data = {
                    "total_pipeline": 2500000,
                    "qualified_leads": 145,
                    "deals_in_negotiation": 23
                }
                
            # Override communication handlers with your logic
            async def _handle_knowledge_request(self, message: AgentMessage) -> Dict[str, Any]:
                """Handle knowledge requests with real sales data"""
                query = message.payload.data.get("query", "")
                requester_role = message.payload.data.get("requester_role", "unknown")
                
                # Your real logic here
                if "sales performance" in query.lower() or "pipeline" in query.lower():
                    return {
                        "status": "success",
                        "pipeline": self.pipeline_data,
                        "forecast": self.forecasts,
                        "response": f"Current sales performance for {requester_role}"
                    }
                elif "forecast" in query.lower():
                    return {
                        "status": "success",
                        "q4_forecast": {
                            "revenue": 1250000,
                            "deals_expected": 45,
                            "confidence": 0.85
                        },
                        "response": "Q4 sales forecast"
                    }
                else:
                    return {
                        "status": "success",
                        "response": f"General sales info for: {query}"
                    }
            
            # Your existing methods can now use communication
            async def request_marketing_support(self, campaign_type: str):
                """Example: CSO asking CMO for marketing support"""
                response = await self.request_info_from_agent(
                    "cmo", 
                    f"Can you create a {campaign_type} campaign to support our Q4 sales push?"
                )
                
                if response and response.get("success"):
                    return f"Marketing support secured: {response['data']}"
                else:
                    return "Could not get marketing support"
        
        return CSOAgent


# Quick integration helper
def add_communication_to_agent(agent_class):
    """
    Decorator to quickly add communication capabilities to existing agents
    
    Usage:
    @add_communication_to_agent
    class MyExistingAgent:
        # your existing agent code
    """
    class CommunicationEnabledAgent(AgentCommunicationMixin, agent_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    return CommunicationEnabledAgent 