# Digital Twin Agent Communication Infrastructure

A production-ready communication system for **digital twin agents** (CMO, CSO, CTO, etc.) built with Python, Redis, and Pydantic. This infrastructure enables seamless communication between your existing digital twin agents and dashboard interfaces.

## 🎯 Purpose

This system is designed specifically for **digital twin environments** where:
- **Human users** (CMO, CSO, etc.) need to quickly request information from their **agent counterparts**
- **Agents** need to communicate with each other across departments for decision-making
- **Dashboard interfaces** need to display real-time information from multiple agents
- **Cross-department collaboration** is essential for business operations

## 🌟 Key Use Cases

### 1. Dashboard-to-Agent Communication
- CMO clicks dashboard to request sales data from CSO agent
- Executive requests department status from all agents
- Real-time agent discovery and availability checking

### 2. Agent-to-Agent Communication
- CMO agent requests sales pipeline data from CSO agent
- CSO agent asks marketing agent about campaign performance
- Cross-department information sharing for strategic decisions

### 3. Integration with Existing Agents
- Add communication capabilities to your existing digital twin agents
- Maintain existing agent logic while enabling communication
- Minimal code changes required for integration

## 🚀 Features

- **Dashboard Interface**: Ready-to-use interface for human-agent communication
- **Agent Communication Mixin**: Easy integration with existing agents
- **Role-Based Discovery**: Find agents by role (CMO, CSO, CTO, etc.)
- **Department-Based Messaging**: Broadcast to entire departments
- **Asynchronous Communication**: Redis Pub/Sub for reliable message delivery
- **Structured Messages**: Pydantic-based schemas for type-safe messaging
- **Memory Integration**: Role-based knowledge retrieval and sharing
- **Production Ready**: Comprehensive error handling, logging, and monitoring
- **Scalable Architecture**: Modular design with clean separation of concerns

## 📋 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI/Frontend   │    │   Orchestrator  │    │  External APIs  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Message Sender       │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     Redis Pub/Sub         │
                    │    Message Broker         │
                    └─────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
│   Agent Registry│     │  Memory Interface│     │   Base Agent    │
└─────────────────┘     └─────────────────┘     └─────────┬───────┘
                                                          │
                                              ┌───────────┼───────────┐
                                              │           │           │
                                    ┌─────────▼─┐   ┌─────▼─────┐   ┌─▼─────┐
                                    │ CMO Agent │   │Marketing  │   │ SEO   │
                                    │           │   │  Agent    │   │Agent  │
                                    └───────────┘   └───────────┘   └───────┘
```

## 🛠️ Core Components

### 1. Message Schema (`schemas.py`)
Pydantic models for structured messaging:
- `AgentMessage`: Core message structure with validation
- `MessageIntent`: Predefined message types
- `MessagePayload`: Flexible data container
- `AgentInfo`: Agent registration information

### 2. Message Broker (`broker.py`)
Redis Pub/Sub implementation:
- Asynchronous message publishing and subscription
- Message persistence for offline agents
- Connection pooling and retry logic
- Health monitoring and error handling

### 3. Agent Registry (`registry.py`)
Centralized agent discovery:
- Agent registration and lifecycle management
- Role-based and capability-based discovery
- Health monitoring and status tracking
- Persistent storage with Redis backup

### 4. Memory Interface (`memory.py`)
Knowledge retrieval system:
- Role-based memory access permissions
- Integration with Google Drive and vector stores
- Contextual search and filtering
- Caching and optimization

### 5. Base Agent (`base_agent.py`)
Abstract base class for all agents:
- Message routing and intent handling
- Automatic registration and heartbeat
- Memory and discovery integration
- Lifecycle management

### 6. Message Sender (`sender.py`)
External interface for non-agent systems:
- Task assignment and knowledge requests
- Agent discovery and health checks
- Broadcast messaging
- Response handling and tracking

## 🔧 Installation

### Prerequisites
- Python 3.8+
- Redis server
- (Optional) Google Drive API credentials
- (Optional) Qdrant vector database

### Quick Start

1. **Clone and install dependencies**:
```bash
git clone <repository>
cd AgentComms
pip install -r requirements.txt
```

2. **Start Redis server**:
```bash
# Using Docker
docker run -p 6379:6379 redis:latest

# Or install locally
redis-server
```

3. **Run the demo**:
```bash
python demo.py
```

## 📚 Usage Examples

### 1. Dashboard Interface (Human-to-Agent Communication)

```python
from AgentComms.examples import DashboardInterface

# Initialize dashboard interface
dashboard = DashboardInterface()
await dashboard.initialize()

# CMO requests sales data from CSO agent
response = await dashboard.request_sales_data(
    requester_role="cmo",
    query="What's our current sales pipeline and Q4 forecast?",
    context={"priority": "high", "dashboard_request": True}
)

if response and response.get("success"):
    sales_data = response["data"]
    print(f"Sales data: {sales_data}")

# Executive requests department status
marketing_status = await dashboard.exec_request_department_status("marketing")
print(f"Marketing department status: {marketing_status}")
```

### 2. Adding Communication to Existing Agents

```python
from AgentComms.examples import AgentCommunicationMixin

# Add communication to your existing CMO agent
class CMOAgent(AgentCommunicationMixin):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.campaigns = []
    
    async def initialize(self):
        # Initialize your existing agent logic
        await self.setup_campaigns()
        
        # Add communication capabilities
        await self.initialize_communication(
            agent_id=f"agent.cmo.{self.name.lower()}",
            role="cmo",
            department="marketing",
            capabilities=["campaign_management", "brand_strategy"],
            user_name=self.name
        )
    
    async def setup_campaigns(self):
        # Your existing agent logic
        self.campaigns = ["Q4 Holiday Campaign", "Brand Awareness Drive"]
    
    # Override handlers with real business logic
    async def _handle_knowledge_request(self, message):
        query = message.payload.data.get("query", "")
        
        if "campaign" in query.lower():
            return {
                "status": "success",
                "campaigns": self.campaigns,
                "performance": {"leads": 1250, "conversion_rate": 0.045}
            }
        
        return {"status": "success", "response": "General CMO information"}
    
    # Use communication in your existing methods
    async def collaborate_with_sales(self, question: str):
        response = await self.request_info_from_agent("cso", question)
        
        if response and response.get("success"):
            sales_data = response["data"]
            # Use sales data to adjust marketing strategy
            return f"Strategy adjusted based on: {sales_data}"
        
        return "Could not get sales data"

# Initialize and use
cmo_agent = CMOAgent("John Smith")
await cmo_agent.initialize()

# Now your CMO agent can communicate with other agents
sales_info = await cmo_agent.collaborate_with_sales("What's the Q4 pipeline?")
```

### 3. Agent-to-Agent Communication

```python
# Your existing CSO agent can now communicate with CMO
class CSOAgent(AgentCommunicationMixin):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.pipeline_data = {}
    
    async def initialize(self):
        await self.setup_sales_data()
        
        await self.initialize_communication(
            agent_id=f"agent.cso.{self.name.lower()}",
            role="cso",
            department="sales",
            capabilities=["sales_forecasting", "pipeline_management"],
            user_name=self.name
        )
    
    async def request_marketing_support(self, campaign_type: str):
        response = await self.request_info_from_agent(
            "cmo", 
            f"Can you create a {campaign_type} campaign for Q4 sales push?"
        )
        
        if response and response.get("success"):
            return f"Marketing support secured: {response['data']}"
        
        return "Could not get marketing support"
```

### 4. Creating a New Agent from Scratch

```python
from AgentComms import BaseAgent, MessageIntent, MessagePayload
from AgentComms.examples import create_agent_config

# Create configuration
config = create_agent_config(
    agent_id="agent.sarah",
    user_name="sarah",
    role="content_agent",
    department="marketing",
    capabilities=["content_creation", "seo_optimization"]
)

# Create custom agent
class MyAgent(BaseAgent):
    async def handle_get_roadmap(self, message):
        # Implementation here
        pass
    
    async def handle_assign_task(self, message):
        # Implementation here
        pass
    
    async def handle_request_knowledge(self, message):
        # Implementation here
        pass
    
    async def get_supported_intents(self):
        return [MessageIntent.GET_ROADMAP, MessageIntent.ASSIGN_TASK]
    
    async def get_agent_capabilities(self):
        return ["content_creation", "seo_optimization"]

# Initialize and run
agent = MyAgent(config)
await agent.initialize()
```

### Sending Messages

```python
from AgentComms import MessageSender, MessageIntent

# Create message sender
sender = MessageSender(redis_url="redis://localhost:6379")
await sender.initialize()

# Assign a task
response = await sender.assign_task(
    agent_id="agent.sarah",
    task_id="TASK_001",
    task_description="Create Q4 marketing content",
    priority="high",
    wait_for_response=True
)

# Request knowledge
knowledge = await sender.request_knowledge(
    agent_id="agent.alex",
    query="SEO best practices for startup content",
    context={"industry": "startup"},
    wait_for_response=True
)

# Discover agents
marketing_agents = await sender.discover_agents(
    department="marketing",
    capability="content_creation"
)
```

### Broadcasting Messages

```python
# Broadcast to all agents in marketing department
results = await sender.broadcast_message(
    intent=MessageIntent.AGENT_STATUS,
    data={"message": "Team meeting at 3 PM"},
    department="marketing",
    priority="normal"
)
```

## 🔍 Message Types

### Core Message Schema
```python
{
    "message_id": "uuid4",
    "conversation_id": "uuid4", 
    "sender_id": "agent.user1",
    "recipient_id": "agent.sarah",
    "intent": "assign_task",
    "payload": {
        "data": {"task_id": "TASK_001", "description": "..."},
        "priority": "high",
        "requires_response": true,
        "response_timeout": 300
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### Supported Intents
- `GET_ROADMAP`: Request strategic roadmap
- `ASSIGN_TASK`: Assign work to an agent
- `REQUEST_KNOWLEDGE`: Request information/expertise
- `SHARE_INSIGHTS`: Share findings with other agents
- `REQUEST_REVIEW`: Request content/work review
- `PROVIDE_FEEDBACK`: Provide feedback on work
- `HEALTH_CHECK`: Check agent health status
- `CAPABILITY_QUERY`: Query agent capabilities

## 🎯 Agent Discovery

### Role-Based Discovery
```python
# Find all CMO agents
cmo_agents = await sender.discover_agents(role="cmo")

# Find all marketing department agents
marketing_agents = await sender.discover_agents(department="marketing")

# Find agents with specific capability
content_agents = await sender.discover_agents(capability="content_creation")

# Find agents supporting specific intent
task_agents = await sender.discover_agents(intent=MessageIntent.ASSIGN_TASK)
```

### Complex Discovery
```python
# Find online marketing agents with content creation capability
agents = await sender.discover_agents(
    department="marketing",
    capability="content_creation",
    online_only=True
)
```

## 💾 Memory Integration

### Role-Based Memory Access
```python
# Each agent has role-based memory permissions
memory_interface = AgentMemoryInterface()
await memory_interface.initialize()

# Search knowledge based on role
knowledge = await memory_interface.search_knowledge(
    agent_id="agent.sarah",
    role="content_agent", 
    query="content strategy best practices",
    intent=MessageIntent.REQUEST_KNOWLEDGE
)
```

### Memory Permissions
- **CMO**: Access to executive, marketing, sales, product knowledge
- **Marketing Manager**: Access to marketing and product knowledge
- **Content Agent**: Access to marketing and content knowledge
- **SEO Agent**: Access to marketing and SEO knowledge

## 🔧 Configuration

### Environment Variables
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_password
REDIS_DB=0

# Memory Configuration
GDRIVE_CONFIG_PATH=./config/gdrive_config.json
VECTOR_STORE_URL=http://localhost:6333

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agent_comms.log

# Communication
HEARTBEAT_INTERVAL=30
MESSAGE_TIMEOUT=60
```

### Configuration Files
```json
{
  "agents": [
    {
      "agent_id": "agent.user1",
      "user_name": "user1",
      "role": "cmo",
      "department": "executive",
      "capabilities": ["strategic_planning", "team_management"],
      "redis_url": "redis://localhost:6379"
    }
  ]
}
```

## 🚀 Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}
  
  agent-cmo:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - AGENT_CONFIG_FILE=/app/config/cmo_config.json
    depends_on:
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-cmo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agent-cmo
  template:
    metadata:
      labels:
        app: agent-cmo
    spec:
      containers:
      - name: agent-cmo
        image: agent-comms:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: AGENT_CONFIG_FILE
          value: "/app/config/cmo_config.json"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: config
        configMap:
          name: agent-configs
      - name: logs
        emptyDir: {}
```

## 🔍 Monitoring & Debugging

### Health Checks
```python
# Check individual agent health
status = await sender.get_agent_status("agent.user1")

# Check message sender statistics
stats = await sender.get_sender_stats()

# Check agent registry statistics
registry_stats = await agent_registry.get_registry_stats()
```

### Logging
The system uses structured logging with agent-specific loggers:
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Agent-specific logger
logger = logging.getLogger("agent.user1")
```

### Error Handling
All components include comprehensive error handling:
- Connection failures with retry logic
- Message validation and sanitization
- Graceful degradation for offline components
- Detailed error logging and reporting

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_message_broker.py

# Run with coverage
pytest --cov=AgentComms tests/
```

### Integration Tests
```bash
# Test with real Redis instance
pytest tests/integration/ --redis-url redis://localhost:6379

# Test agent communication
pytest tests/integration/test_agent_communication.py
```

## 📝 Examples

### Startup Team Configuration
```python
from AgentComms.examples import create_startup_config, save_startup_config

# Create default startup team configuration
configs = create_startup_config()

# Save to file
save_startup_config("startup_agents.json")
```

### Custom Agent Implementation
See `examples/marketing_agent.py` for a complete implementation example.

## 🔄 Roadmap

- [ ] Web UI for agent management
- [ ] REST API interface
- [ ] Prometheus metrics integration
- [ ] Advanced message routing
- [ ] Message encryption
- [ ] Agent clusters and load balancing
- [ ] GraphQL API
- [ ] Real-time dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Run the demo script for examples

## 📖 API Reference

### Core Classes

#### `BaseAgent`
Abstract base class for all agents.

**Methods:**
- `initialize()`: Initialize agent and infrastructure
- `shutdown()`: Graceful shutdown
- `send_message(message)`: Send message to another agent
- `discover_agents(**filters)`: Find other agents
- `search_knowledge(query, **options)`: Search knowledge base

#### `MessageSender`
External interface for sending messages to agents.

**Methods:**
- `send_message(recipient_id, intent, data, **options)`: Send message
- `assign_task(agent_id, task_id, description, **options)`: Assign task
- `request_knowledge(agent_id, query, **options)`: Request knowledge
- `discover_agents(**filters)`: Find agents
- `broadcast_message(intent, data, **filters)`: Broadcast message

#### `AgentRegistry`
Centralized agent discovery and management.

**Methods:**
- `register_agent(agent_info)`: Register agent
- `discover_agents(**filters)`: Find agents
- `get_agent(agent_id)`: Get agent information
- `get_online_agents()`: Get all online agents

#### `MessageBroker`
Redis Pub/Sub message broker.

**Methods:**
- `publish_message(message)`: Publish message
- `subscribe_to_agent(agent_id, handler)`: Subscribe to messages
- `health_check()`: Check broker health

---

*Built with ❤️ for scalable agent communication* 