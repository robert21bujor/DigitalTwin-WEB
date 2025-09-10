"""
Universal Dashboard Interface
============================

Generic dashboard interface that works with ANY agent type.
No predefined roles - completely modular and extensible.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from ..sender import MessageSender
from ..schemas import MessageIntent, AgentMessage

logger = logging.getLogger(__name__)


class UniversalDashboard:
    """
    Universal dashboard interface for ANY agent communication
    
    Features:
    - Works with any agent role/type
    - Dynamic agent discovery  
    - Generic message routing
    - No hardcoded business logic
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.message_sender = MessageSender(
            redis_url=redis_url,
            sender_id="system.dashboard"
        )
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize dashboard interface"""
        if not self._initialized:
            await self.message_sender.initialize()
            self._initialized = True
            logger.info("Universal dashboard initialized")
    
    async def shutdown(self) -> None:
        """Shutdown dashboard interface"""
        if self._initialized:
            await self.message_sender.shutdown()
            self._initialized = False
            logger.info("Universal dashboard shutdown")
    
    # ===============================
    # UNIVERSAL COMMUNICATION METHODS
    # ===============================
    
    async def send_request_to_agent(
        self,
        target_agent_role: str,        # Any role: "cmo", "engineer", "data_scientist", etc.
        target_agent_id: Optional[str] = None,  # Specific agent or None for any
        query: str = "",
        intent: MessageIntent = MessageIntent.REQUEST_KNOWLEDGE,
        context: Optional[Dict[str, Any]] = None,
        requester_info: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Send any request to any agent type
        
        Args:
            target_agent_role: Role of target agent (any string)
            target_agent_id: Specific agent ID or None for first available
            query: What you're asking for
            intent: Type of request (knowledge, task, status, etc.)
            context: Additional context
            requester_info: Who is making the request
            timeout: Response timeout
            
        Returns:
            Agent response or error
        """
        try:
            # Find target agent(s)
            if target_agent_id:
                # Use specific agent
                target_agents = await self.message_sender.discover_agents(
                    agent_id=target_agent_id
                )
            else:
                # Find any agent with this role
                target_agents = await self.message_sender.discover_agents(
                    role=target_agent_role
                )
            
            if not target_agents:
                return {
                    "error": f"No agent found",
                    "target_role": target_agent_role,
                    "target_id": target_agent_id
                }
            
            target_agent = target_agents[0]
            
            # Prepare generic request
            request_data = {
                "query": query,
                "requester_info": requester_info or {},
                "requested_at": datetime.utcnow().isoformat(),
                "source": "dashboard",
                "context": context or {}
            }
            
            logger.info(f"Dashboard requesting from {target_agent_role}: {query}")
            
            # Send request based on intent
            if intent == MessageIntent.REQUEST_KNOWLEDGE:
                response = await self.message_sender.request_knowledge(
                    agent_id=target_agent.agent_id,
                    query=query,
                    context=request_data,
                    wait_for_response=True
                )
            elif intent == MessageIntent.ASSIGN_TASK:
                response = await self.message_sender.assign_task(
                    agent_id=target_agent.agent_id,
                    task_description=query,
                    context=request_data,
                    wait_for_response=True
                )
            else:
                # Generic message
                response = await self.message_sender.send_message(
                    recipient_id=target_agent.agent_id,
                    intent=intent,
                    data=request_data,
                    requires_response=True
                )
            
            if isinstance(response, AgentMessage):
                return {
                    "success": True,
                    "agent_id": target_agent.agent_id,
                    "agent_role": target_agent.role,
                    "department": target_agent.department,
                    "data": response.payload.data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "error": f"No response from {target_agent_role}",
                    "agent_id": target_agent.agent_id
                }
                
        except Exception as e:
            logger.error(f"Dashboard request failed: {e}")
            return {"error": str(e)}
    
    async def discover_agents(
        self,
        role: Optional[str] = None,
        department: Optional[str] = None, 
        capability: Optional[str] = None,
        online_only: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover any agents in the system
        
        Args:
            role: Filter by role (optional)
            department: Filter by department (optional) 
            capability: Filter by capability (optional)
            online_only: Only return online agents
            
        Returns:
            Organized agent information
        """
        try:
            all_agents = await self.message_sender.discover_agents(
                role=role,
                department=department,
                capability=capability,
                online_only=online_only
            )
            
            # Organize by role
            agents_by_role = {}
            for agent in all_agents:
                agent_role = agent.role
                if agent_role not in agents_by_role:
                    agents_by_role[agent_role] = []
                
                agents_by_role[agent_role].append({
                    "agent_id": agent.agent_id,
                    "user_name": agent.user_name,
                    "department": agent.department,
                    "capabilities": agent.capabilities,
                    "status": agent.status,
                    "last_seen": agent.last_seen.isoformat() if agent.last_seen else None
                })
            
            return agents_by_role
            
        except Exception as e:
            logger.error(f"Agent discovery failed: {e}")
            return {}
    
    async def get_agent_capabilities(
        self, 
        agent_role: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Get capabilities of agents by role or specific agent"""
        try:
            if agent_id:
                agents = await self.message_sender.discover_agents(agent_id=agent_id)
            elif agent_role:
                agents = await self.message_sender.discover_agents(role=agent_role)
            else:
                agents = await self.message_sender.discover_agents()
            
            capabilities_map = {}
            for agent in agents:
                capabilities_map[agent.agent_id] = {
                    "role": agent.role,
                    "department": agent.department,
                    "capabilities": agent.capabilities
                }
            
            return capabilities_map
            
        except Exception as e:
            logger.error(f"Capability query failed: {e}")
            return {}
    
    async def broadcast_to_department(
        self,
        department: str,
        message: str,
        intent: MessageIntent = MessageIntent.AGENT_STATUS,
        data: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Broadcast message to all agents in a department
        
        Args:
            department: Target department name
            message: Message to broadcast
            intent: Message intent
            data: Additional data
            sender_info: Information about sender
            
        Returns:
            Results for each agent
        """
        try:
            dept_agents = await self.message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            broadcast_data = {
                "message": message,
                "sender_info": sender_info or {},
                "broadcast_data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            results = {}
            for agent in dept_agents:
                try:
                    await self.message_sender.send_message(
                        recipient_id=agent.agent_id,
                        intent=intent,
                        data=broadcast_data
                    )
                    results[agent.agent_id] = True
                except Exception as e:
                    logger.error(f"Failed to send to {agent.agent_id}: {e}")
                    results[agent.agent_id] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Department broadcast failed: {e}")
            return {}
    
    async def get_department_status(self, department: str) -> List[Dict[str, Any]]:
        """Get status of all agents in any department"""
        try:
            agents = await self.message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            status_list = []
            for agent in agents:
                status = await self.message_sender.get_agent_status(agent.agent_id)
                status_list.append({
                    "agent_id": agent.agent_id,
                    "role": agent.role,
                    "status": status or "unknown",
                    "capabilities": agent.capabilities,
                    "department": agent.department
                })
            
            return status_list
            
        except Exception as e:
            logger.error(f"Department status request failed: {e}")
            return []
    
    # ===============================
    # CONVENIENCE METHODS (EXAMPLES)
    # ===============================
    
    async def ask_any_agent(
        self,
        agent_role: str,
        question: str,
        requester: str = "dashboard_user"
    ) -> Optional[Dict[str, Any]]:
        """
        Simple method to ask any agent type a question
        
        Examples:
        - ask_any_agent("data_scientist", "What's the churn prediction?")
        - ask_any_agent("devops_engineer", "What's the system uptime?")
        - ask_any_agent("sales_manager", "How many deals closed this week?")
        """
        return await self.send_request_to_agent(
            target_agent_role=agent_role,
            query=question,
            requester_info={"requester": requester}
        )
    
    async def assign_task_to_agent(
        self,
        agent_role: str,
        task_description: str,
        priority: str = "normal",
        deadline: Optional[str] = None,
        requester: str = "dashboard_user"
    ) -> Optional[Dict[str, Any]]:
        """
        Assign task to any agent type
        
        Examples:
        - assign_task_to_agent("content_writer", "Write blog post about AI")
        - assign_task_to_agent("qa_engineer", "Test the new feature")
        - assign_task_to_agent("designer", "Create landing page mockup")
        """
        return await self.send_request_to_agent(
            target_agent_role=agent_role,
            query=task_description,
            intent=MessageIntent.ASSIGN_TASK,
            context={
                "priority": priority,
                "deadline": deadline,
                "task_type": "assignment"
            },
            requester_info={"requester": requester}
        )


# =================================
# USAGE EXAMPLES FOR ANY AGENT TYPE
# =================================

class UniversalDashboardExamples:
    """Examples showing how to use the universal dashboard with ANY agent type"""
    
    @staticmethod
    async def example_any_role_communication():
        """Example: Communicate with any type of agent"""
        dashboard = UniversalDashboard()
        await dashboard.initialize()
        
        try:
            # Discover what agents exist (no predefined roles)
            all_agents = await dashboard.discover_agents()
            print(f"Available agent types: {list(all_agents.keys())}")
            
            # Ask any agent type a question
            for agent_role in all_agents.keys():
                response = await dashboard.ask_any_agent(
                    agent_role, 
                    f"What can you help me with?"
                )
                print(f"{agent_role} response: {response}")
            
        finally:
            await dashboard.shutdown()
    
    @staticmethod
    async def example_dynamic_discovery():
        """Example: Dynamically discover and communicate with agents"""
        dashboard = UniversalDashboard()
        await dashboard.initialize()
        
        try:
            # Find agents by capability (not role)
            agents_by_capability = {}
            all_agents = await dashboard.discover_agents()
            
            for role, agents in all_agents.items():
                for agent in agents:
                    for capability in agent["capabilities"]:
                        if capability not in agents_by_capability:
                            agents_by_capability[capability] = []
                        agents_by_capability[capability].append({
                            "role": role,
                            "agent_id": agent["agent_id"]
                        })
            
            print("Agents by capability:")
            for capability, agents in agents_by_capability.items():
                print(f"  {capability}: {[a['role'] for a in agents]}")
            
            # Request help from any agent with specific capability
            if "data_analysis" in agents_by_capability:
                response = await dashboard.ask_any_agent(
                    agents_by_capability["data_analysis"][0]["role"],
                    "Can you analyze our quarterly metrics?"
                )
                print(f"Data analysis response: {response}")
                
        finally:
            await dashboard.shutdown()


async def demo_universal_dashboard():
    """Demo the universal dashboard with any agent types"""
    print("🌐 Universal Dashboard Demo")
    print("Works with ANY agent type!")
    
    dashboard = UniversalDashboard()
    await dashboard.initialize()
    
    try:
        # Discovery
        agents = await dashboard.discover_agents()
        print(f"\n📋 Discovered agent types: {list(agents.keys())}")
        
        # Generic communication
        for agent_role in agents.keys():
            response = await dashboard.ask_any_agent(
                agent_role,
                "What's your current status?"
            )
            print(f"\n🤖 {agent_role}: {response}")
        
    finally:
        await dashboard.shutdown()


if __name__ == "__main__":
    asyncio.run(demo_universal_dashboard()) 