"""
Dashboard Interface for Agent Communication
==========================================

Interface for dashboard/UI to communicate with existing digital twin agents.
Allows human users (CMO, CSO, etc.) to request information from their agent counterparts.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from ..sender import MessageSender
from ..schemas import MessageIntent, AgentMessage

logger = logging.getLogger(__name__)


class DashboardInterface:
    """
    Interface for dashboard to communicate with digital twin agents
    
    Use cases:
    - CMO dashboard requests sales data from CSO agent
    - Human user asks their agent for specific information
    - Cross-department information requests through dashboard
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
            logger.info("Dashboard interface initialized")
    
    async def shutdown(self) -> None:
        """Shutdown dashboard interface"""
        if self._initialized:
            await self.message_sender.shutdown()
            self._initialized = False
            logger.info("Dashboard interface shutdown")
    
    # Main dashboard communication methods
    
    async def request_agent_info(
        self,
        requester_role: str,  # e.g., "cmo", "cso" 
        target_agent_role: str,  # e.g., "cso", "cmo"
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Request information from an agent through dashboard
        
        Args:
            requester_role: Role of person making request (cmo, cso, etc.)
            target_agent_role: Role of target agent
            query: What information is needed
            context: Additional context for the request
            timeout: Response timeout in seconds
            
        Returns:
            Agent response data or None if failed
        """
        try:
            # Find target agent
            target_agents = await self.message_sender.discover_agents(role=target_agent_role)
            
            if not target_agents:
                logger.error(f"No {target_agent_role} agent found")
                return {"error": f"No {target_agent_role} agent available"}
            
            target_agent = target_agents[0]  # Use first available agent
            
            # Prepare request data
            request_data = {
                "query": query,
                "requester_role": requester_role,
                "requested_at": datetime.utcnow().isoformat(),
                "source": "dashboard",
                "context": context or {}
            }
            
            logger.info(f"Dashboard: {requester_role} requesting info from {target_agent_role}")
            logger.info(f"Query: {query}")
            
            # Send knowledge request
            response = await self.message_sender.request_knowledge(
                agent_id=target_agent.agent_id,
                query=query,
                context=request_data,
                wait_for_response=True
            )
            
            if isinstance(response, AgentMessage):
                response_data = response.payload.data
                logger.info(f"✅ Response received from {target_agent_role}")
                return {
                    "success": True,
                    "agent_id": target_agent.agent_id,
                    "agent_role": target_agent_role,
                    "data": response_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"❌ No response from {target_agent_role}")
                return {"error": f"No response from {target_agent_role} agent"}
                
        except Exception as e:
            logger.error(f"Dashboard request failed: {e}")
            return {"error": str(e)}
    
    async def request_sales_data(
        self,
        requester_role: str,
        query: str = "current sales performance and pipeline status",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Convenience method to request sales data from CSO agent"""
        return await self.request_agent_info(
            requester_role=requester_role,
            target_agent_role="cso",
            query=query,
            context=context
        )
    
    async def request_marketing_data(
        self,
        requester_role: str,
        query: str = "current marketing campaigns and performance metrics",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Convenience method to request marketing data from CMO agent"""
        return await self.request_agent_info(
            requester_role=requester_role,
            target_agent_role="cmo", 
            query=query,
            context=context
        )
    
    async def request_product_roadmap(
        self,
        requester_role: str,
        timeframe: str = "Q1-Q2",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Request product roadmap from product agents"""
        target_agents = await self.message_sender.discover_agents(
            role="product_manager",
            online_only=True
        )
        
        if not target_agents:
            return {"error": "No product manager agent available"}
        
        target_agent = target_agents[0]
        
        try:
            response = await self.message_sender.send_message(
                recipient_id=target_agent.agent_id,
                intent=MessageIntent.GET_ROADMAP,
                data={
                    "timeframe": timeframe,
                    "requester_role": requester_role,
                    "source": "dashboard",
                    "context": context or {}
                },
                requires_response=True
            )
            
            if isinstance(response, AgentMessage):
                return {
                    "success": True,
                    "agent_id": target_agent.agent_id,
                    "roadmap": response.payload.data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {"error": "No roadmap response received"}
                
        except Exception as e:
            logger.error(f"Roadmap request failed: {e}")
            return {"error": str(e)}
    
    async def get_available_agents(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get list of available agents organized by role"""
        try:
            all_agents = await self.message_sender.discover_agents(online_only=True)
            
            agents_by_role = {}
            for agent in all_agents:
                role = agent.role
                if role not in agents_by_role:
                    agents_by_role[role] = []
                
                agents_by_role[role].append({
                    "agent_id": agent.agent_id,
                    "user_name": agent.user_name,
                    "department": agent.department,
                    "capabilities": agent.capabilities,
                    "status": agent.status,
                    "last_seen": agent.last_seen.isoformat() if agent.last_seen else None
                })
            
            return agents_by_role
            
        except Exception as e:
            logger.error(f"Failed to get available agents: {e}")
            return {}
    
    async def check_agent_status(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Check if a specific role agent is available"""
        try:
            agents = await self.message_sender.discover_agents(role=agent_role)
            
            if not agents:
                return {"available": False, "role": agent_role}
            
            agent = agents[0]
            status = await self.message_sender.get_agent_status(agent.agent_id)
            
            return {
                "available": True,
                "role": agent_role,
                "agent_id": agent.agent_id,
                "status": status,
                "capabilities": agent.capabilities
            }
            
        except Exception as e:
            logger.error(f"Status check failed for {agent_role}: {e}")
            return {"available": False, "role": agent_role, "error": str(e)}
    
    # Convenience methods for common dashboard operations
    
    async def cmo_request_sales_data(self, query: str) -> Optional[Dict[str, Any]]:
        """CMO requesting sales data from CSO"""
        return await self.request_sales_data("cmo", query)
    
    async def cso_request_marketing_data(self, query: str) -> Optional[Dict[str, Any]]:
        """CSO requesting marketing data from CMO"""
        return await self.request_marketing_data("cso", query)
    
    async def exec_request_department_status(self, department: str) -> List[Dict[str, Any]]:
        """Executive requesting status from all agents in a department"""
        try:
            agents = await self.message_sender.discover_agents(
                department=department,
                online_only=True
            )
            
            status_reports = []
            for agent in agents:
                status = await self.message_sender.get_agent_status(agent.agent_id)
                if status:
                    status_reports.append({
                        "agent_id": agent.agent_id,
                        "role": agent.role,
                        "status": status,
                        "department": department
                    })
            
            return status_reports
            
        except Exception as e:
            logger.error(f"Department status request failed: {e}")
            return []


# Usage examples for dashboard integration
class DashboardExamples:
    """Examples of how to use the dashboard interface"""
    
    @staticmethod
    async def example_cmo_requests_sales_data():
        """Example: CMO clicks on dashboard to get sales data from CSO"""
        dashboard = DashboardInterface()
        await dashboard.initialize()
        
        try:
            # CMO requests current sales pipeline
            response = await dashboard.cmo_request_sales_data(
                "What's our current sales pipeline and Q4 forecast?"
            )
            
            if response and response.get("success"):
                sales_data = response["data"]
                print(f"Sales data received: {sales_data}")
            else:
                print(f"Request failed: {response.get('error')}")
                
        finally:
            await dashboard.shutdown()
    
    @staticmethod
    async def example_cross_department_request():
        """Example: Any role requesting info from another department"""
        dashboard = DashboardInterface()
        await dashboard.initialize()
        
        try:
            # Check what agents are available
            available_agents = await dashboard.get_available_agents()
            print(f"Available agents: {available_agents}")
            
            # Request info between departments
            response = await dashboard.request_agent_info(
                requester_role="cmo",
                target_agent_role="cso",
                query="Which sales channels are performing best this quarter?",
                context={"priority": "high", "deadline": "end_of_week"}
            )
            
            print(f"Cross-department response: {response}")
            
        finally:
            await dashboard.shutdown()
    
    @staticmethod
    async def example_dashboard_agent_discovery():
        """Example: Dashboard discovering and checking agent status"""
        dashboard = DashboardInterface()
        await dashboard.initialize()
        
        try:
            # Check if CSO agent is available
            cso_status = await dashboard.check_agent_status("cso")
            print(f"CSO agent status: {cso_status}")
            
            # Get all marketing department agents
            marketing_status = await dashboard.exec_request_department_status("marketing")
            print(f"Marketing department status: {marketing_status}")
            
        finally:
            await dashboard.shutdown() 