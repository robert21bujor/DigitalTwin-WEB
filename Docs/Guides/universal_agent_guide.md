# Universal Agent Communication System

**Completely modular communication infrastructure that works with ANY agent type.**

## 🎯 Key Principle: No Predefined Roles

This system is designed to be **completely role-agnostic**. It doesn't hardcode specific business roles like "CMO" or "CSO". Instead, it provides universal interfaces that work with ANY agent type that can appear in ANY organization.

## 🌟 Features

- ✅ **Any Agent Type**: Works with `data_scientist`, `devops_engineer`, `ux_designer`, `legal_advisor`, etc.
- ✅ **Any Department**: `engineering`, `design`, `marketing`, `legal`, `research`, etc.
- ✅ **Any Capabilities**: `python`, `figma`, `kubernetes`, `contract_review`, etc.
- ✅ **Dynamic Discovery**: Find agents by role, department, or capability
- ✅ **Universal Dashboard**: One interface for all agent types
- ✅ **Modular Integration**: Add communication to existing agents with one mixin

## 🚀 Quick Start

### 1. Universal Dashboard (Works with ANY agent)

```python
from AgentComms.examples import UniversalDashboard

# Create universal dashboard
dashboard = UniversalDashboard()
await dashboard.initialize()

# Ask ANY agent type a question
response = await dashboard.ask_any_agent(
    "data_scientist",  # Or any role: "devops_engineer", "ux_designer", etc.
    "What's the current churn prediction?"
)

# Assign task to ANY agent type  
response = await dashboard.assign_task_to_agent(
    "content_writer",  # Or any role: "qa_engineer", "designer", etc.
    "Write a blog post about machine learning trends"
)

# Discover agents dynamically
all_agents = await dashboard.discover_agents()
print(f"Available agent types: {list(all_agents.keys())}")
```

### 2. Add Communication to ANY Existing Agent

```python
from AgentComms.examples import UniversalAgentMixin

# Your existing agent (any type)
class YourExistingAgent(UniversalAgentMixin):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        # Your existing agent logic here
    
    async def initialize(self):
        # Add communication capabilities (any role/department/capabilities)
        await self.initialize_agent_communication(
            agent_id=f"agent.your_role.{self.name.lower()}",
            role="your_role",           # Any string: "engineer", "designer", etc.
            department="your_dept",     # Any string: "engineering", "design", etc.
            capabilities=["skill1", "skill2"],  # Any skills
            user_name=self.name
        )
    
    # Handle requests with your business logic
    async def _handle_knowledge_request(self, message):
        query = message.payload.data.get("message", "")
        
        # Your agent-specific response logic
        return {
            "status": "success",
            "data": self.get_your_agent_data(),  # Your method
            "response": f"Response from {self.name}"
        }

# Use it
agent = YourExistingAgent("Alice")
await agent.initialize()

# Now your agent can communicate with any other agent
response = await agent.request_information_from_agent(
    "any_other_role",
    "Any question you want to ask"
)
```

### 3. Create ANY Agent Type Dynamically

```python
from AgentComms.examples import create_agent_with_communication

# Create any agent type (not predefined!)
agent = create_agent_with_communication(
    agent_type="ml_engineer",      # Any role
    name="Bob", 
    department="ai_research",      # Any department
    capabilities=["pytorch", "tensorflow", "model_optimization"]  # Any skills
)

await agent.initialize()

# Communicate with any other agent
response = await agent.request_information_from_agent(
    "data_scientist",
    "What features should I focus on for the churn model?"
)
```

## 🔧 Examples for Any Organization

### Tech Company
```python
# Create tech company agents
agents = [
    create_agent_with_communication("frontend_developer", "Alice", "engineering", ["react", "typescript"]),
    create_agent_with_communication("backend_developer", "Bob", "engineering", ["python", "postgres"]),
    create_agent_with_communication("devops_engineer", "Carol", "infrastructure", ["docker", "kubernetes"]),
    create_agent_with_communication("product_designer", "Dave", "design", ["figma", "prototyping"])
]
```

### Consulting Firm
```python
# Create consulting firm agents
agents = [
    create_agent_with_communication("strategy_consultant", "Eve", "strategy", ["market_analysis", "frameworks"]),
    create_agent_with_communication("financial_analyst", "Frank", "finance", ["excel", "modeling"]),
    create_agent_with_communication("change_manager", "Grace", "transformation", ["change_management", "training"])
]
```

### Research Lab
```python
# Create research lab agents
agents = [
    create_agent_with_communication("research_scientist", "Henry", "research", ["statistical_analysis", "r"]),
    create_agent_with_communication("lab_technician", "Ivy", "lab", ["equipment_operation", "safety"]),
    create_agent_with_communication("data_analyst", "Jack", "analysis", ["python", "visualization"])
]
```

### Healthcare Organization
```python
# Create healthcare agents
agents = [
    create_agent_with_communication("clinical_researcher", "Kate", "research", ["clinical_trials", "regulatory"]),
    create_agent_with_communication("biostatistician", "Leo", "statistics", ["sas", "clinical_data"]),
    create_agent_with_communication("regulatory_affairs", "Mia", "compliance", ["fda_submissions", "documentation"])
]
```

## 📊 Dynamic Discovery Examples

### Find Agents by Capability
```python
# Find all agents who can code in Python (regardless of role)
python_experts = await dashboard.discover_agents(capability="python")

# Find all agents who can use Figma (regardless of department)
figma_users = await dashboard.discover_agents(capability="figma")

# Find all agents in a specific department
engineering_team = await dashboard.discover_agents(department="engineering")
```

### Cross-Department Communication
```python
# Any agent can talk to any other agent
data_scientist = agents[0]

# Ask DevOps about infrastructure
infra_status = await data_scientist.request_information_from_agent(
    "devops_engineer",
    "What's the current system performance?"
)

# Ask designer about user feedback
user_insights = await data_scientist.request_information_from_agent(
    "ux_researcher", 
    "What user behavior patterns should I analyze?"
)

# Ask legal about compliance
compliance_info = await data_scientist.request_information_from_agent(
    "legal_advisor",
    "Are there any data privacy constraints for this analysis?"
)
```

## 🧪 Test the Universal System

```bash
# Test with completely dynamic agent types
python -m AgentComms.universal_test
```

This will create and test communication between:
- `data_scientist`, `devops_engineer`, `ux_researcher`, `content_strategist`, `security_analyst`
- Plus dynamically created: `ml_engineer`, `product_manager`, `legal_advisor`, `sales_engineer`

## 🎯 Perfect for Any Organization

The system automatically adapts to:

- **Startups**: `founder`, `full_stack_developer`, `growth_hacker`
- **Enterprise**: `solution_architect`, `business_analyst`, `compliance_officer`
- **Creative Agencies**: `creative_director`, `copywriter`, `account_manager`
- **Non-profits**: `program_manager`, `fundraising_coordinator`, `volunteer_coordinator`
- **Government**: `policy_analyst`, `public_affairs_specialist`, `budget_analyst`

## 💡 Key Benefits

1. **Zero Configuration**: No hardcoded roles or business logic
2. **Infinite Extensibility**: Add any agent type at runtime
3. **Universal Interface**: One dashboard for all agent types
4. **Capability-Based Discovery**: Find agents by what they can do, not their title
5. **Department Agnostic**: Works with any organizational structure
6. **Future-Proof**: New agent types can be added without changing the core system

## 🚀 Production Ready

- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Redis Persistence**: Messages and agent registry persist across restarts
- ✅ **Health Monitoring**: Built-in agent health checks and status monitoring
- ✅ **Scalable**: Designed for horizontal scaling across multiple instances
- ✅ **Secure**: Message validation and agent authentication
- ✅ **Modular**: Each component can be deployed independently

Your communication system will work with any agent type that exists now or in the future! 🌟 