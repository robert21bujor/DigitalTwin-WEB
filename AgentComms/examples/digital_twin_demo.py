"""
Digital Twin Communication Examples
==================================

Examples showing how to use the communication system with 
your existing digital twin agents (CMO, CSO, etc.).
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .dashboard_interface import DashboardInterface
from .agent_integration import AgentCommunicationMixin

logger = logging.getLogger(__name__)


class DigitalTwinCommunicationDemo:
    """
    Demonstration of communication between digital twin agents
    
    Use cases:
    1. Dashboard → Agent (CMO clicks to request sales data from CSO)
    2. Agent → Agent (CMO agent requests info from CSO agent)
    3. Cross-department information sharing
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.dashboard = DashboardInterface(redis_url)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the demo"""
        if not self._initialized:
            await self.dashboard.initialize()
            self._initialized = True
            logger.info("Digital Twin Communication Demo initialized")
    
    async def shutdown(self):
        """Shutdown the demo"""
        if self._initialized:
            await self.dashboard.shutdown()
            self._initialized = False
            logger.info("Digital Twin Communication Demo shutdown")
    
    async def demo_dashboard_to_agent_communication(self):
        """
        Demo: Human CMO uses dashboard to request info from CSO agent
        """
        print("\n=== Dashboard to Agent Communication Demo ===")
        print("Scenario: CMO clicks on dashboard to get sales data from CSO agent")
        
        try:
            # Check if CSO agent is available
            cso_status = await self.dashboard.check_agent_status("cso")
            print(f"CSO Agent Status: {cso_status}")
            
            if not cso_status.get("available"):
                print("❌ CSO agent not available for demo")
                return
            
            # CMO requests sales data from CSO
            response = await self.dashboard.request_sales_data(
                requester_role="cmo",
                query="What's our current sales pipeline and Q4 forecast?",
                context={
                    "priority": "high",
                    "dashboard_request": True,
                    "requested_by": "CMO John Smith"
                }
            )
            
            if response and response.get("success"):
                print("✅ Sales data received from CSO agent:")
                print(f"   Agent ID: {response['agent_id']}")
                print(f"   Data: {response['data']}")
                print(f"   Timestamp: {response['timestamp']}")
            else:
                print(f"❌ Request failed: {response.get('error')}")
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    async def demo_cross_department_request(self):
        """
        Demo: CSO requests marketing data from CMO agent
        """
        print("\n=== Cross-Department Request Demo ===")
        print("Scenario: CSO agent requests marketing performance from CMO agent")
        
        try:
            # Check available agents
            available_agents = await self.dashboard.get_available_agents()
            print(f"Available agents: {list(available_agents.keys())}")
            
            # CSO requests marketing data
            response = await self.dashboard.request_marketing_data(
                requester_role="cso",
                query="What marketing campaigns are driving the most qualified leads?",
                context={
                    "purpose": "sales_strategy_alignment",
                    "timeframe": "Q4_2024"
                }
            )
            
            if response and response.get("success"):
                print("✅ Marketing data received from CMO agent:")
                print(f"   Agent ID: {response['agent_id']}")
                print(f"   Data: {response['data']}")
            else:
                print(f"❌ Request failed: {response.get('error')}")
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    async def demo_product_roadmap_request(self):
        """
        Demo: Executive requests product roadmap
        """
        print("\n=== Product Roadmap Request Demo ===")
        print("Scenario: Executive requests product roadmap for strategic planning")
        
        try:
            response = await self.dashboard.request_product_roadmap(
                requester_role="executive",
                timeframe="Q1-Q2_2025",
                context={
                    "purpose": "strategic_planning",
                    "board_meeting": True
                }
            )
            
            if response and response.get("success"):
                print("✅ Product roadmap received:")
                print(f"   Agent ID: {response['agent_id']}")
                print(f"   Roadmap: {response['roadmap']}")
            else:
                print(f"❌ Request failed: {response.get('error')}")
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    async def demo_department_status_check(self):
        """
        Demo: Check status of all agents in a department
        """
        print("\n=== Department Status Check Demo ===")
        print("Scenario: Executive checks status of all marketing agents")
        
        try:
            marketing_status = await self.dashboard.exec_request_department_status("marketing")
            
            if marketing_status:
                print("✅ Marketing department status:")
                for agent_status in marketing_status:
                    print(f"   - {agent_status['role']}: {agent_status['status']}")
                    print(f"     Agent ID: {agent_status['agent_id']}")
                    print(f"     Capabilities: {agent_status['capabilities']}")
            else:
                print("❌ No marketing agents available")
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    async def demo_agent_discovery(self):
        """
        Demo: Discover available agents
        """
        print("\n=== Agent Discovery Demo ===")
        print("Scenario: Dashboard discovers all available agents")
        
        try:
            available_agents = await self.dashboard.get_available_agents()
            
            if available_agents:
                print("✅ Available agents by role:")
                for role, agents in available_agents.items():
                    print(f"   {role.upper()}:")
                    for agent in agents:
                        print(f"     - {agent['agent_id']} ({agent['user_name']})")
                        print(f"       Department: {agent['department']}")
                        print(f"       Status: {agent['status']}")
                        print(f"       Capabilities: {agent['capabilities']}")
            else:
                print("❌ No agents available")
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
    
    async def run_all_demos(self):
        """Run all communication demos"""
        print("🚀 Starting Digital Twin Communication Demos")
        print("=" * 50)
        
        await self.demo_agent_discovery()
        await self.demo_dashboard_to_agent_communication()
        await self.demo_cross_department_request()
        await self.demo_product_roadmap_request()
        await self.demo_department_status_check()
        
        print("\n" + "=" * 50)
        print("✅ All demos completed")


# Integration example with existing agent
class ExistingAgentExample(AgentCommunicationMixin):
    """
    Example of how to add communication to your existing agents
    """
    
    def __init__(self, agent_type: str, name: str):
        super().__init__()
        self.agent_type = agent_type  # "cmo", "cso", etc.
        self.name = name
        self.business_data = {}
        
    async def initialize(self):
        """Initialize your existing agent with communication"""
        # Setup your existing agent data
        await self.setup_business_data()
        
        # Add communication capabilities
        capabilities = {
            "cmo": ["campaign_management", "brand_strategy", "market_analysis"],
            "cso": ["sales_forecasting", "pipeline_management", "revenue_analysis"],
            "cto": ["technology_roadmap", "system_architecture", "tech_strategy"],
            "cfo": ["financial_planning", "budget_analysis", "cost_optimization"]
        }
        
        await self.initialize_communication(
            agent_id=f"agent.{self.agent_type}.{self.name.lower().replace(' ', '')}",
            role=self.agent_type,
            department=self.get_department(),
            capabilities=capabilities.get(self.agent_type, []),
            user_name=self.name
        )
    
    def get_department(self) -> str:
        """Get department based on agent type"""
        dept_mapping = {
            "cmo": "marketing",
            "cso": "sales", 
            "cto": "engineering",
            "cfo": "finance"
        }
        return dept_mapping.get(self.agent_type, "general")
    
    async def setup_business_data(self):
        """Setup business data based on agent type"""
        if self.agent_type == "cmo":
            self.business_data = {
                "campaigns": ["Q4 Holiday Campaign", "Brand Awareness Drive"],
                "performance": {
                    "leads_generated": 1250,
                    "conversion_rate": 0.045,
                    "cost_per_lead": 28.50
                }
            }
        elif self.agent_type == "cso":
            self.business_data = {
                "pipeline": {
                    "total_value": 2500000,
                    "qualified_leads": 145,
                    "deals_closing": 23
                },
                "forecast": {
                    "q4_revenue": 1250000,
                    "confidence": 0.85
                }
            }
        elif self.agent_type == "cto":
            self.business_data = {
                "roadmap": {
                    "q1_2025": ["AI Integration", "Cloud Migration"],
                    "q2_2025": ["Mobile App v2.0", "API Modernization"]
                },
                "systems": {
                    "uptime": 99.9,
                    "performance": "optimal"
                }
            }
        elif self.agent_type == "cfo":
            self.business_data = {
                "budget": {
                    "total": 5000000,
                    "spent": 3200000,
                    "remaining": 1800000
                },
                "financial_health": {
                    "revenue_growth": 0.15,
                    "profit_margin": 0.22
                }
            }
    
    # Override communication handlers with real business logic
    async def _handle_knowledge_request(self, message) -> Dict[str, Any]:
        """Handle knowledge requests with real business data"""
        query = message.payload.data.get("query", "").lower()
        requester_role = message.payload.data.get("requester_role", "unknown")
        
        # Return relevant business data based on query
        if self.agent_type == "cmo" and ("campaign" in query or "marketing" in query):
            return {
                "status": "success",
                "data": self.business_data,
                "response": f"Marketing data for {requester_role}"
            }
        elif self.agent_type == "cso" and ("sales" in query or "pipeline" in query):
            return {
                "status": "success", 
                "data": self.business_data,
                "response": f"Sales data for {requester_role}"
            }
        elif self.agent_type == "cto" and ("roadmap" in query or "tech" in query):
            return {
                "status": "success",
                "data": self.business_data,
                "response": f"Technology roadmap for {requester_role}"
            }
        elif self.agent_type == "cfo" and ("budget" in query or "financial" in query):
            return {
                "status": "success",
                "data": self.business_data,
                "response": f"Financial data for {requester_role}"
            }
        else:
            return {
                "status": "success",
                "data": {"general_info": f"General information from {self.agent_type}"},
                "response": f"General response from {self.agent_type} for {requester_role}"
            }


# Quick demo runner
async def run_digital_twin_demo():
    """Run the digital twin communication demo"""
    demo = DigitalTwinCommunicationDemo()
    
    try:
        await demo.initialize()
        await demo.run_all_demos()
    except Exception as e:
        print(f"❌ Demo error: {e}")
    finally:
        await demo.shutdown()


if __name__ == "__main__":
    asyncio.run(run_digital_twin_demo()) 