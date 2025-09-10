# Agent File Access System

## Overview
The Agent File Access System provides secure, role-based access to Google Drive files through AI agents. Each agent can access files from their own department and public files from other departments, while private folders remain restricted to department members only.

## Architecture

### Components
1. **UserAgentMatcher** (`user_agent_mapping.py`) - Handles access control and authorization
2. **GoogleDriveSearchSkill** (`Core/Agents/gdrive_search_skill.py`) - Provides file search capabilities to agents
3. **SimpleAgentManager** (`communication_manager.py`) - Manages agent communication and file requests

### Access Control Rules

#### Public Folder Access
- ✅ **Any user** can access **any agent's** public department folders
- ✅ **Any agent** can search public files across all departments

#### Private Folder Access  
- 🔒 **Only department members** can access their department's private folders
- 🚫 **Management roles** cannot override private folder restrictions
- 🚫 **Cross-department** private access is blocked

#### Department Structure
```
DigitalTwin_Brain/
├── Business Development/
│   ├── (public files)
│   └── bdm_private/          # Restricted to BDM users only
├── Operations/
│   ├── (public files)  
│   └── ops_private/          # Restricted to Operations users only
├── Marketing/
│   └── (public files)
└── Executive/
    └── (public files)
```

## Supported Agents

### Executive
- `agent.executive_cmo` → `DigitalTwin_Brain/Executive`

### Marketing  
- `agent.content_specialist` → `DigitalTwin_Brain/Marketing`
- `agent.seo_specialist` → `DigitalTwin_Brain/Marketing`
- `agent.analytics_specialist` → `DigitalTwin_Brain/Marketing`

### Business Development
- `agent.bdm_agent` → `DigitalTwin_Brain/Business Development`
- `agent.ipm_agent` → `DigitalTwin_Brain/Business Development`
- `agent.presales_engineer` → `DigitalTwin_Brain/Business Development`

### Operations
- `agent.head_of_operations` → `DigitalTwin_Brain/Operations`
- `agent.senior_csm` → `DigitalTwin_Brain/Operations`
- `agent.senior_delivery_consultant` → `DigitalTwin_Brain/Operations`
- `agent.delivery_consultant_en` → `DigitalTwin_Brain/Operations`
- `agent.delivery_consultant_bg` → `DigitalTwin_Brain/Operations`
- `agent.delivery_consultant_hu` → `DigitalTwin_Brain/Operations`
- `agent.legal_agent` → `DigitalTwin_Brain/Operations`
- `agent.reporting_manager` → `DigitalTwin_Brain/Operations`
- `agent.reporting_specialist` → `DigitalTwin_Brain/Operations`

## Query Examples

### Cross-Department Public Access
```
User: "Show me marketing files"
Agent: Searches DigitalTwin_Brain/Marketing (public only)

User: "What operations tasks are there?"
Agent: Searches DigitalTwin_Brain/Operations (public only)

User: "Executive documents about earnings"
Agent: Searches DigitalTwin_Brain/Executive (public only)
```

### Private Folder Access (Department Members Only)
```
BDM User + BDM Agent: "Show me bdm_private files" ✅ Allowed
Operations User + Operations Agent: "Show me ops_private files" ✅ Allowed
Operations User + BDM Agent: "Show me bdm_private files" 🚫 Blocked
```

## Configuration

### Adding New Agents
1. Add to `FILE_ENABLED_AGENTS` set in `user_agent_mapping.py`
2. Add department mapping in `gdrive_search_skill.py`
3. Update user department detection logic in `user_agent_mapping.py`

### Adding New Departments
1. Add folder detection in `communication_manager.py`
2. Update department mapping in both access control files
3. Create corresponding Google Drive folder structure

## Security Features
- **Department-aware access control** - Users can only access private folders from their own department
- **Automatic folder detection** - System detects department references in natural language queries
- **Comprehensive logging** - All access attempts are logged for audit purposes
- **Graceful fallback** - If file access fails, agents fall back to general AI responses
