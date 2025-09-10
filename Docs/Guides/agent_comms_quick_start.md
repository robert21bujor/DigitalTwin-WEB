# Digital Twin Communication - Quick Start Guide

Your **Digital Twin Agent Communication System** is now ready! Here's how to use it:

## 🎯 Main Use Cases

### 1. Dashboard → Agent Communication
**Scenario**: CMO clicks dashboard to request sales data from CSO agent

```python
from AgentComms.examples import DashboardInterface

# Initialize dashboard
dashboard = DashboardInterface()
await dashboard.initialize()

# CMO requests sales data from CSO
response = await dashboard.request_sales_data(
    requester_role="cmo",
    query="What's our current Q4 sales forecast?",
    context={"priority": "high", "dashboard_request": True}
)

if response and response.get("success"):
    sales_data = response["data"]
    print(f"Sales data: {sales_data}")
```

### 2. Agent → Agent Communication
**Scenario**: CMO agent needs information from CSO agent

```python
from AgentComms.examples import AgentCommunicationMixin

class CMOAgent(AgentCommunicationMixin):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
    
    async def initialize(self):
        await self.initialize_communication(
            agent_id=f"agent.cmo.{self.name.lower()}",
            role="cmo",
            department="marketing",
            capabilities=["campaign_management", "brand_strategy"],
            user_name=self.name
        )
    
    async def get_sales_insights(self):
        # CMO agent requests info from CSO agent
        response = await self.request_info_from_agent(
            "cso", 
            "What sales channels are performing best this quarter?"
        )
        
        if response and response.get("success"):
            return response["data"]
        return None

# Usage
cmo = CMOAgent("John Smith")
await cmo.initialize()
sales_insights = await cmo.get_sales_insights()
```

### 3. Add Communication to Your Existing Agents

```python
# Your existing agent class
class YourExistingCMOAgent:
    def __init__(self, name):
        self.name = name
        self.campaigns = []
    
    def get_campaign_performance(self):
        return {"campaigns": self.campaigns, "performance": {...}}

# Enhanced with communication
class CommunicationEnabledCMO(AgentCommunicationMixin, YourExistingCMOAgent):
    async def initialize(self):
        # Initialize your existing logic
        await super().__init__(self.name)
        
        # Add communication capabilities
        await self.initialize_communication(
            agent_id=f"agent.cmo.{self.name.lower()}",
            role="cmo",
            department="marketing",
            capabilities=["campaign_management"]
        )
    
    # Override handlers with your business logic
    async def _handle_knowledge_request(self, message):
        query = message.payload.data.get("query", "")
        
        if "campaign" in query.lower():
            return {
                "status": "success",
                "data": self.get_campaign_performance()
            }
        
        return {"status": "success", "response": "General CMO information"}
```

## 🔧 Quick Setup

1. **Install the package**:
```bash
cd AgentComms
pip install -e .
```

2. **Start Redis**:
```bash
redis-server
# OR with Docker:
docker run -p 6379:6379 redis:latest
```

3. **Test the system**:
```bash
python -m AgentComms.test_digital_twin
```

4. **Run the full demo**:
```bash
python -m AgentComms.demo
```

## 📊 What You Get

- **Dashboard Interface**: Ready-to-use interface for human-agent communication
- **Agent Mixin**: Easy integration with existing agents
- **Cross-Department Communication**: CMO ↔ CSO ↔ CTO ↔ CFO communication
- **Real-time Discovery**: Find agents by role, department, capabilities
- **Production Ready**: Error handling, logging, monitoring, Redis persistence

## 🌟 Key Features for Digital Twins

- **Role-Based Discovery**: Find agents by role (`cmo`, `cso`, `cto`, etc.)
- **Department Broadcasting**: Send messages to entire departments
- **Knowledge Requests**: Agents can request specific information from each other
- **Status Monitoring**: Check agent availability and health
- **Context-Aware Messaging**: Include business context in communications

## 📝 Example Integrations

### Dashboard Integration
```python
# In your dashboard/frontend
async def handle_cmo_sales_request():
    dashboard = DashboardInterface()
    await dashboard.initialize()
    
    response = await dashboard.request_sales_data(
        requester_role="cmo",
        query="Current pipeline status and Q4 forecast"
    )
    
    return response["data"] if response.get("success") else "No data available"
```

### Agent Cross-Communication
```python
# In your CMO agent
async def optimize_campaigns_with_sales_data(self):
    sales_data = await self.request_info_from_agent(
        "cso",
        "Which marketing channels are converting best?"
    )
    
    if sales_data and sales_data.get("success"):
        # Use sales insights to optimize marketing campaigns
        return self.adjust_campaigns(sales_data["data"])
```

## 🎯 Perfect for Your Digital Twin Environment

This system enables the exact scenarios you described:
- **Human CMO** clicks dashboard → gets data from **CSO agent**
- **CMO agent** asks **CSO agent** for sales data when making decisions
- **Cross-department collaboration** without calling real people
- **Fast access to specialized information** from the right agent

Your digital twin agents can now communicate seamlessly! 🚀 