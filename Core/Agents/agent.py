"""
Core Agent template with Azure OpenAI integration and memory capabilities
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
# Import with fallback for different execution contexts
try:
    from Core.Tasks.task import Task, TaskStatus
except ImportError:
    try:
        # Add project root to path if needed
        import sys
        from pathlib import Path
        project_root = str(Path(__file__).parent.parent.parent)
        if project_root not in sys.path:
            sys.path.append(project_root)
        from Core.Tasks.task import Task, TaskStatus
    except ImportError:
        # Define minimal Task classes for testing
        from enum import Enum
        from typing import Optional
        from datetime import datetime
        
        class TaskStatus(Enum):
            PENDING = "pending"
            IN_PROGRESS = "in_progress"
            COMPLETED = "completed"
            FAILED = "failed"
        
        class Task:
            def __init__(self, id: str = "", title: str = "", description: str = "", status: TaskStatus = TaskStatus.PENDING):
                self.id = id
                self.title = title
                self.description = description
                self.status = status

logger = logging.getLogger(__name__)

# Memory system import with graceful fallback
MEMORY_AVAILABLE = False
try:
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    try:
        # Try alternative import path
        import sys
        from pathlib import Path
        memory_path = str(Path(__file__).parent.parent.parent / "Memory")
        if memory_path not in sys.path:
            sys.path.append(memory_path)
        from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
        MEMORY_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Memory system not available: {e}")
        MEMORY_AVAILABLE = False

# Google Drive search skill import with graceful fallback
GDRIVE_SEARCH_AVAILABLE = False
GDRIVE_SEARCH_SKILL = None

# ClickUp integration import with graceful fallback
CLICKUP_AVAILABLE = False
CLICKUP_TOOLS = None

# Calendar functionality now provided by Gcalendar module

def _initialize_clickup_tools():
    """Initialize ClickUp agent tools with robust import handling"""
    global CLICKUP_AVAILABLE, CLICKUP_TOOLS
    
    try:
        from Integrations.Clickup.clickup_agent_tools import clickup_agent_tools
        CLICKUP_TOOLS = clickup_agent_tools
        CLICKUP_AVAILABLE = True
        logger.info("🎯 ClickUp integration initialized for all agents")
        return True
        
    except Exception as e:
        logger.warning(f"ClickUp integration not available: {e}")
        CLICKUP_AVAILABLE = False
        return False

def _initialize_gdrive_search():
    """Initialize Google Drive search skill with robust import handling"""
    global GDRIVE_SEARCH_AVAILABLE, GDRIVE_SEARCH_SKILL
    
    try:
        import sys
        from pathlib import Path
        
        # Add required paths
        base_dir = Path(__file__).parent.parent.parent
        memory_dir = base_dir / "Memory"
        agents_dir = base_dir / "Core" / "Agents"
        
        for path in [str(memory_dir), str(agents_dir)]:
            if path not in sys.path:
                sys.path.append(path)
        
        # Test imports step by step with robust import handling
        try:
            # First, try to import the skill directly (it has its own fallback imports)
            from gdrive_search_skill import GoogleDriveSearchSkill
            GDRIVE_SEARCH_SKILL = GoogleDriveSearchSkill()
            logger.info("✅ GoogleDriveSearchSkill imported and created successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import GoogleDriveSearchSkill: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error creating GoogleDriveSearchSkill: {e}")
            return False
        
        GDRIVE_SEARCH_AVAILABLE = True
        logger.info("🔍 Google Drive search system initialized for all agents")
        return True
        
    except Exception as e:
        logger.warning(f"Google Drive search skill not available: {e}")
        import traceback
        traceback.print_exc()
        return False

# Don't initialize on module load to avoid segfaults during import
# Initialization will happen when agents are created
# _initialize_gdrive_search()
# _initialize_clickup_tools()

# Legacy google_calendar_skill removed - now using Gcalendar module



class AgentType(Enum):
    """Types of agents in the system"""
    COMPANION = "companion"  # Works with humans
    AUTONOMOUS = "autonomous"
    REACTIVE = "reactive"
    COLLABORATIVE = "collaborative"


class Agent:
    """
    Concrete agent template with Azure OpenAI integration
    Ready to use - agents extend this with their specific prompts
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        agent_type: AgentType,
        kernel: sk.Kernel,
        skills: List[str] = None,
        system_prompt: str = None,
        fast_mode: bool = False
    ):
        self.name = name
        self.role = role
        self.type = agent_type
        self.kernel = kernel
        self.skills = skills or []
        self.system_prompt = system_prompt or self.get_default_system_prompt()
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.created_at = datetime.now()
        self.fast_mode = fast_mode
        
        # Initialize memory system (lazy if fast_mode)
        self.memory_manager = None
        if not fast_mode:
            self._initialize_memory()
        
        # Initialize plugins dictionary for external access
        self.plugins = {}
        
        # Add Google Drive search skill - all agents can discuss files
        # Actual file access permissions controlled by authentication/user matching
        self._add_gdrive_search_skill()
        
        # Add ClickUp agent tools - all agents can access ClickUp tasks
        # Actual ClickUp access controlled by user OAuth tokens
        self._add_clickup_tools()
        
        # Add Google Calendar skill to kernel
        # Calendar functionality provided by Gcalendar module
        
        # Get the chat completion service from kernel - try different service types
        self.chat_service = None
        try:
            services = kernel.services
            for service in services.values():
                if hasattr(service, 'get_chat_message_content'):
                    self.chat_service = service
                    break
        except Exception as e:
            logger.warning(f"Could not get chat service: {e}")
            self.chat_service = None
    
    def _initialize_memory(self):
        """Initialize memory manager for this agent"""
        if not MEMORY_AVAILABLE:
            logger.debug(f"Memory system not available for {self.name}")
            return
            
        try:
            collection_name = self._get_memory_collection_name()
            self.memory_manager = EnhancedMemoryManager(
                agent_name=self.name,
                collection_name=collection_name,
                lazy_init=True  # Always use lazy initialization
            )
            
            logger.debug(f"Memory system prepared for {self.name} (will initialize on first use)")
            
        except Exception as e:
            logger.warning(f"Failed to prepare memory for {self.name}: {str(e)}")
            self.memory_manager = None
    
    def _get_memory_collection_name(self) -> str:
        """Override this method to customize memory collection name"""
        return f"{self.name.lower()}-memory"
    
    def _add_gdrive_search_skill(self):
        """Add Google Drive search capabilities to the agent"""
        global GDRIVE_SEARCH_AVAILABLE, GDRIVE_SEARCH_SKILL
        
        # Lazy initialization - try to initialize if not already done
        if not GDRIVE_SEARCH_AVAILABLE and GDRIVE_SEARCH_SKILL is None:
            logger.info(f"Attempting lazy initialization of Google Drive search for {self.name}")
            _initialize_gdrive_search()
        
        # Always initialize gdrive_skill to avoid AttributeError
        self.gdrive_skill = GDRIVE_SEARCH_SKILL
        
        if not GDRIVE_SEARCH_AVAILABLE or GDRIVE_SEARCH_SKILL is None:
            logger.info(f"Google Drive search skill not available for {self.name}")
            self.gdrive_skill = None
            return
            
        try:
            # Store the skill instance directly for manual access
            self.gdrive_skill = GDRIVE_SEARCH_SKILL
            
            # Add to plugins dictionary for external access (communication manager)
            self.plugins['google_drive_search'] = GDRIVE_SEARCH_SKILL
            
            # ✅ CORRECT: Register plugin using proper Semantic Kernel syntax
            try:
                gdrive_plugin = self.kernel.add_plugin(plugin=GDRIVE_SEARCH_SKILL, plugin_name="GoogleDriveSearch")
                logger.info(f"🔗 Google Drive functions registered successfully with kernel for {self.name}")
            except Exception as registration_error:
                logger.error(f"❌ Failed to register Google Drive plugin: {registration_error}")
                # Continue without function calling capability
                logger.info(f"🔗 Google Drive search available via manual calling for {self.name}")
            
            # Add to skills list if not already there
            if "Google Drive File Search" not in self.skills:
                self.skills.append("Google Drive File Search")
            
            logger.info(f"✅ Google Drive search skill added to {self.name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add Google Drive search skill to {self.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _add_clickup_tools(self):
        """Add ClickUp agent tools to the agent"""
        global CLICKUP_AVAILABLE, CLICKUP_TOOLS
        
        # Lazy initialization - try to initialize if not already done
        if not CLICKUP_AVAILABLE and CLICKUP_TOOLS is None:
            logger.info(f"Attempting lazy initialization of ClickUp tools for {self.name}")
            _initialize_clickup_tools()
        
        if not CLICKUP_AVAILABLE or CLICKUP_TOOLS is None:
            logger.info(f"ClickUp integration not available for {self.name}")
            return
            
        try:
            # Store the tools instance for manual access (primary method)
            self.clickup_tools = CLICKUP_TOOLS
            
            # Add to plugins dictionary for external access
            self.plugins['clickup_tools'] = CLICKUP_TOOLS
            
            # Skip Semantic Kernel plugin registration due to serialization issues
            # Just use manual calling instead
            logger.info(f"🔗 ClickUp tools available via manual calling for {self.name}")
            
            # Add to skills list if not already there
            clickup_skills = ["ClickUp Task Management", "ClickUp Connection Status", "ClickUp Team Access"]
            for skill in clickup_skills:
                if skill not in self.skills:
                    self.skills.append(skill)
            
            logger.info(f"✅ ClickUp agent tools added to {self.name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add ClickUp tools to {self.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Legacy calendar skill method removed - now using Gcalendar module
    
    def get_default_system_prompt(self) -> str:
        """Default system prompt - override in specific agents"""
        gdrive_help = ""
        if GDRIVE_SEARCH_AVAILABLE:
            gdrive_help = """

🔍 **CRITICAL: Google Drive File Search Integration**
You have direct access to our company's Google Drive. When users ask about files, documents, reports, or any content, IMMEDIATELY use these search functions:

**Available Functions:**
- search_files(query, folder, file_type): Search files by name/keywords
- list_folders(): Show all available folders  
- search_recent_files(days): Find recently modified files
- search_by_folder(folder_name): List all files in a specific folder

**IMMEDIATE ACTION REQUIRED:** When users ask about files:
1. Use the appropriate search function FIRST
2. Provide direct Google Drive links (view + download)
3. Include file location and details
4. Do NOT ask clarifying questions - search and provide results

**Available Folders:** Executive, Marketing, Product Marketing, Digital Marketing, Content & Brand, Operations, Legal, etc.
**File Types:** pdf, doc, excel, google, image, text, etc.

**Examples:**
- User: "Find the Q1 report" → search_files("Q1", "Executive", "pdf")
- User: "Show marketing files" → search_files("marketing", None, None)
- User: "Recent documents" → search_recent_files("7")
- User: "What's in Executive folder?" → search_by_folder("Executive")

**ALWAYS provide clickable links and file locations!**"""
        
        # Add ClickUp tools help
        clickup_help = """

🎯 **CLICKUP INTEGRATION TOOLS**
You have access to ClickUp task management tools. When users ask about tasks, projects, bugs, or client work, use these functions:

**Available ClickUp Functions:**
- search_tasks_by_keyword(user_id, team_id, keywords, ...): Search tasks by keywords with native filtering
- retrieve_client_bugs_or_tasks(user_id, team_id, client_identifier, task_type, ...): Get client-specific tasks/bugs
- attach_file_with_analysis(user_id, task_id, file_path, analysis_summary, ...): Upload files to tasks with analysis

**CLICKUP USAGE PATTERNS:**
- When users ask about tasks: Use search_tasks_by_keyword with relevant filters
- For client-specific queries: Use retrieve_client_bugs_or_tasks with client name
- For file uploads: Use attach_file_with_analysis with content summary

**Important Notes:**
- ALL ClickUp operations require the user's ClickUp OAuth token
- If user isn't connected to ClickUp, guide them to connect first
- Use specific team_id (workspace) for searches
- Apply filters like statuses, tags, assignees, dates for better results
- Always provide ClickUp task URLs in results

**Examples:**
- "Find bugs for Client X" → retrieve_client_bugs_or_tasks(user_id, team_id, "Client X", "bug")
- "Search urgent tasks" → search_tasks_by_keyword(user_id, team_id, "urgent", statuses="urgent,high")
- "Upload analysis to task" → attach_file_with_analysis(user_id, task_id, file_path, summary)"""

        # Add shared email knowledge awareness for all agents
        email_awareness_help = """

📧 **SHARED EMAIL KNOWLEDGE ACCESS:**
You have access to the company's shared email knowledge base stored in DigitalTwin_Brain/Users/*/Emails/. This gives you context about company communications:

**Email Categories Available:**
- DigitalTwin_Brain/Users/*/Emails/Internal/: Internal company communications across all team members
- DigitalTwin_Brain/Users/*/Emails/Business/: External business communications from all users
- DigitalTwin_Brain/Users/*/Emails/Clients/: Client communications and relationships from entire organization
- DigitalTwin_Brain/Users/*/Emails/Partners/: Partner and vendor communications across teams
- DigitalTwin_Brain/Users/*/Emails/Projects/: Project-specific email threads from all involved users
- DigitalTwin_Brain/Users/*/Emails/Urgent/: High-priority communications from any team member

**EMAIL AWARENESS CAPABILITIES:**
- Reference relevant email context when discussing business matters
- Understand ongoing conversations and project status from email threads
- Provide insights based on communication patterns across the organization
- Help coordinate responses based on previous email exchanges
- Maintain continuity in business relationships through email context

**FOR EMAIL CONTEXT REQUESTS - SEMANTIC SEARCH CAPABILITIES:**

**🧠 SEMANTIC SEARCH ENABLED**: The system now supports natural language understanding! You can use conversational queries and the system will intelligently find relevant files.

**ENHANCED SEARCH APPROACH:**

**1. NATURAL LANGUAGE QUERIES (Preferred):**
- "Show me emails from Hoang about the project" → search_files("emails from Hoang about project")
- "Find my latest internal communications" → search_files("latest internal communications")
- "What were the recent client meetings?" → search_files("recent client meetings")
- "Any updates from the marketing team?" → search_files("marketing team updates")

**2. TRADITIONAL TARGETED SEARCHES (Fallback):**
- For specific people → search_files("hoang", "DigitalTwin_Brain/Users", "docx")
- For domains → search_files("repsmate.com", "DigitalTwin_Brain/Users", "docx")
- For categories → search_files("Internal", "DigitalTwin_Brain/Users", "docx")

**3. MULTILINGUAL SUPPORT:**
- English: "Find contract documents"
- Romanian: "Găsește documentele de contract" (both work!)

**SEMANTIC SEARCH BENEFITS:**
✅ **Intent Understanding**: Understands "latest emails" vs "recent communications"
✅ **Context Awareness**: Knows "team updates" relates to internal communications  
✅ **Smart Ranking**: Results ranked by relevance with explanation
✅ **Reduced False Positives**: Better filtering of irrelevant files
✅ **Natural Queries**: Use conversational language instead of keywords

**SEARCH STRATEGY EXAMPLE:**
User: "What are my latest emails from the team?"
YOU: search_files("latest emails from team")
→ System understands intent and searches semantically for team communications
→ Results include relevance scores and explanations

**ALWAYS try natural language first, then fall back to specific terms if needed!**

🚨 **CRITICAL: EMAIL SEARCH MANDATE FOR ALL AGENTS**

When users ask about EMAILS, COMMUNICATIONS, MESSAGES, or CORRESPONDENCE, you MUST immediately use search_files() - NEVER give generic responses about not having access!

**MANDATORY EMAIL SEARCH PATTERNS:**
- "recent emails" → search_files("recent emails communications")
- "my emails" → search_files("my emails messages")
- "emails from [person]" → search_files("emails from [person]")
- "team communications" → search_files("team communications emails")
- "latest messages" → search_files("latest email messages")
- "internal communications" → search_files("internal communications emails")

**EXAMPLE RESPONSES:**
❌ WRONG: "I don't have access to your email..."
✅ CORRECT: *Immediately calls search_files("recent emails")* then provides results

**THIS APPLIES TO ALL AGENTS - NO EXCEPTIONS!**"""

        calendar_help = ""
        # Calendar capability provided by Gcalendar module
        if True:  # Calendar always available via Gcalendar module
            calendar_help = """

📅 **CRITICAL: Google Calendar Integration**
You have direct access to the user's Google Calendar. When users ask about their schedule, meetings, events, or availability, IMMEDIATELY use these calendar functions:

**Available Functions:**
- get_events_for_date(date): Get events for a specific date (supports "today", "tomorrow", "thursday", "2024-01-31", etc.)
- get_upcoming_events(days): Get upcoming events for the next X days (default: 7)
- search_calendar_events(query): Search events by keywords (meeting names, attendees, etc.)

**IMMEDIATE ACTION REQUIRED:** When users ask about calendar/schedule:
1. Use the appropriate calendar function FIRST
2. Provide clear event details (time, location, attendees if relevant)
3. Format dates and times in a readable way
4. Do NOT ask clarifying questions - access calendar and provide results

**Examples:**
- User: "What's on my calendar tomorrow?" → get_events_for_date("tomorrow")
- User: "Do I have meetings on Thursday?" → get_events_for_date("thursday")
- User: "What's my schedule for January 31st?" → get_events_for_date("2024-01-31")
- User: "What meetings do I have this week?" → get_upcoming_events("7")
- User: "Find my meeting with John" → search_calendar_events("John")

**ALWAYS check the user's actual calendar before making any scheduling assumptions!**"""

        return f"""🚨🚨🚨 **STOP! READ THIS FIRST - CRITICAL EMAIL MANDATE** 🚨🚨🚨

IF USER ASKS ABOUT EMAILS/MESSAGES/COMMUNICATIONS:
>>> IMMEDIATELY CALL search_files() WITH EMAIL TERMS <<<
>>> DO NOT READ FURTHER UNTIL YOU CALL search_files() <<<
>>> DO NOT RESPOND WITH "I DON'T HAVE ACCESS" <<<

When users ask about EMAILS, COMMUNICATIONS, MESSAGES, or CORRESPONDENCE, you MUST immediately use search_files() - NEVER give generic responses about not having access!

**🧠 QUERY INTERPRETATION RULES:**
1. **EXTRACT EMAIL INTENT** - Don't search literal user words!
2. **CONVERT TO SEMANTIC TERMS** - Use the patterns below
3. **FOCUS ON EMAIL CONTENT** - Not the question words

**MANDATORY EMAIL SEARCH PATTERNS - USE search_files() ONLY:**
- "Can you search for my recent/latest emails?" → search_files("recent emails communications")
- "Search my latest received email" → search_files("latest received emails communications")  
- "Show me my emails" → search_files("emails communications messages")
- "Find emails from [person]" → search_files("emails from [person]")
- "What are my recent messages?" → search_files("recent messages communications")
- "Any new communications?" → search_files("latest communications emails")
- "Check my inbox" → search_files("inbox emails communications")
- "Latest correspondence" → search_files("latest correspondence emails")

**🚫 NEVER SEARCH LITERALLY:**
❌ DON'T search: "Can you search" or "Show me" or "Find me"
✅ DO search: "recent emails communications" or "latest emails"

**CRITICAL: ALWAYS use search_files() for email queries - NEVER use search_recent_files()!**

**EXAMPLE RESPONSES:**
❌ WRONG: "I don't have access to your email..."
❌ WRONG: Using search_recent_files() for email queries  
❌ WRONG: search_files("Can you search") - literal query words
✅ CORRECT: *Immediately calls search_files("latest received emails communications")* then provides results

**THIS APPLIES TO ALL AGENTS - NO EXCEPTIONS!**

---

You are {self.name}, a {self.role} with the following capabilities:

Skills: {', '.join(self.skills)}

You should provide helpful, accurate, and professional responses within your area of expertise.
Always be clear about what you can and cannot do.{gdrive_help}{clickup_help}{email_awareness_help}{calendar_help}

When users ask about files, documents, or email context, use your Google Drive search capabilities immediately to find and link to relevant files.
When users ask about tasks, projects, or ClickUp-related queries, use your ClickUp tools to search and manage tasks.
When users ask about their schedule or calendar, use your Google Calendar access to provide real-time information.
"""

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        return self.system_prompt
    
    async def execute_task(self, task: Task) -> bool:
        """Execute assigned task using Azure OpenAI"""
        logger.info(f"{self.name} executing task: {task.title}")
        
        try:
            task.update_status(TaskStatus.IN_PROGRESS, self.name, "Task execution started")
            
            # Perform the actual AI-powered work
            result = await self.perform_work(task)
            
            if result:
                task.output = result
                task.update_status(TaskStatus.UNDER_REVIEW, self.name, "Task completed, ready for review")
                self.tasks_completed += 1
                return True
            else:
                task.update_status(
                    TaskStatus.REJECTED, 
                    self.name, 
                    "Task execution failed",
                    rejection_reason="Agent was unable to generate output for the task"
                )
                self.tasks_failed += 1
                return False
                
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            task.update_status(
                TaskStatus.REJECTED, 
                self.name, 
                f"Execution error: {str(e)}",
                rejection_reason=f"Technical error during task execution: {str(e)}"
            )
            self.tasks_failed += 1
            return False
    
    def _detect_file_request(self, user_input: str) -> bool:
        """Detect if user is asking about files or documents"""
        file_keywords = [
            'file', 'files', 'document', 'documents', 'report', 'reports',
            'pdf', 'excel', 'word', 'google drive', 'folder', 'folders',
            'earnings', 'briefing', 'analysis', 'presentation', 'spreadsheet',
            'amazon', 'q1', 'q2', 'q3', 'q4', 'marketing', 'executive',
            'provide me', 'show me', 'find', 'search', 'get me'
        ]
        
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in file_keywords)
    
    def _extract_search_terms(self, user_input: str) -> tuple:
        """Extract search terms from user input"""
        user_lower = user_input.lower()
        
        # Extract query terms
        query_terms = []
        if 'amazon' in user_lower:
            query_terms.append('amazon')
        if any(term in user_lower for term in ['q1', 'earnings', 'financial']):
            query_terms.append('earnings')
        if any(term in user_lower for term in ['marketing', 'campaign']):
            query_terms.append('marketing')
        if any(term in user_lower for term in ['brief', 'briefing']):
            query_terms.append('briefing')
        
        # Default query if nothing specific found
        query = ' '.join(query_terms) if query_terms else user_input.split()[:3]
        if isinstance(query, list):
            query = ' '.join(query)
        
        # Extract folder hint
        folder = None
        if any(term in user_lower for term in ['executive', 'earnings', 'financial']):
            folder = 'Executive'
        elif any(term in user_lower for term in ['marketing', 'campaign']):
            folder = 'Marketing'
        
        # Extract file type hint
        file_type = None
        if any(term in user_lower for term in ['pdf', 'report']):
            file_type = 'pdf'
        elif any(term in user_lower for term in ['excel', 'spreadsheet']):
            file_type = 'excel'
        elif any(term in user_lower for term in ['word', 'doc']):
            file_type = 'doc'
        
        return query, folder, file_type
    
    async def _handle_file_request(self, user_input: str) -> str:
        """Handle file search requests using Google Drive search"""
        try:
            logger.info(f"Processing file request for agent {self.name}")
            
            if not hasattr(self, 'gdrive_skill'):
                logger.error(f"❌ Agent {self.name} has no gdrive_skill attribute")
                return "I don't currently have access to file search capabilities (no gdrive_skill attribute)."
            
            if self.gdrive_skill is None:
                logger.error(f"❌ Agent {self.name} has gdrive_skill=None")
                return "I don't currently have access to file search capabilities (gdrive_skill is None)."
            
            logger.info(f"✅ Agent {self.name} has valid gdrive_skill: {type(self.gdrive_skill)}")
            
            # Check for specific requests
            user_lower = user_input.lower()
            
            if any(term in user_lower for term in ['all files', 'everything', 'what files', 'list files']):
                # List available folders first, then search all
                folders_result = self.gdrive_skill.list_folders()
                return folders_result
            
            elif 'recent' in user_lower:
                # Search recent files
                return self.gdrive_skill.search_recent_files("7")
            
            elif any(folder in user_lower for folder in ['executive folder', 'marketing folder', 'product folder']):
                # List specific folder contents
                if 'executive' in user_lower:
                    return self.gdrive_skill.search_by_folder("Executive")
                elif 'marketing' in user_lower:
                    return self.gdrive_skill.search_by_folder("Marketing")
                elif 'product' in user_lower:
                    return self.gdrive_skill.search_by_folder("Product Marketing")
            
            else:
                # General file search
                query, folder, file_type = self._extract_search_terms(user_input)
                return self.gdrive_skill.search_files(query, folder, file_type)
            
        except Exception as e:
            logger.error(f"Error in file search for {self.name}: {e}")
            return f"I encountered an error while searching for files: {str(e)}"
    
    async def perform_work(self, task: Task) -> Optional[str]:
        """Perform AI-powered work using Azure OpenAI with memory context"""
        try:
            logger.info(f"🎯 PERFORM_WORK DEBUG: Agent {self.name} starting work on task: {task.title}")
            
            # Check if this is a file request first
            user_input = f"{task.title} {task.description}".strip()
            logger.info(f"🎯 PERFORM_WORK DEBUG: Combined input: '{user_input}'")
            
            if self._detect_file_request(user_input):
                logger.info(f"🔍 {self.name} detected file request: {user_input}")
                file_result = await self._handle_file_request(user_input)
                logger.info(f"🔍 {self.name} file search result: {file_result[:100]}...")
                if file_result and not file_result.startswith("I don't currently have access"):
                    logger.info(f"✅ {self.name} returning Google Drive search results")
                    return file_result
                # If no access or error, fall through to normal AI response
            
            if not self.chat_service:
                logger.error("No chat service available")
                return f"[SIMULATED] {self.role} work for: {task.title}\n\nThis would normally be generated by Azure OpenAI GPT-4o, but the service is not properly connected."
            
            # Get relevant memory context if available
            memory_context = ""
            if self.memory_manager:
                memory_context = await self.memory_manager.get_relevant_context(
                    current_task=f"{task.title} {task.description}",
                    max_memories=3
                )
            
            # Create the user prompt with task details and memory context
            user_prompt = self.create_task_prompt(task, memory_context)
            
            # Call Azure OpenAI through Semantic Kernel
            chat_history = ChatHistory()
            chat_history.add_system_message(self.system_prompt)
            chat_history.add_user_message(user_prompt)
            
            # Get response from Azure OpenAI
            response = await self.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=2000,
                    temperature=0.7
                )
            )
            
            result = str(response) if response else None
            
            # Store task memory for future reference
            if result and self.memory_manager:
                await self.memory_manager.add_task_memory(
                    task_id=task.id,
                    task_description=task.description,
                    result=result,
                    success=True
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI execution for {self.name}: {str(e)}")
            
            # Store failed task memory
            if self.memory_manager:
                await self.memory_manager.add_task_memory(
                    task_id=task.id,
                    task_description=task.description,
                    result=f"Error: {str(e)}",
                    success=False
                )
            
            return f"[ERROR] {self.role} encountered an error: {str(e)}"
    
    def create_task_prompt(self, task: Task, memory_context: str = "") -> str:
        """Create a task-specific prompt with optional memory context"""
        prompt = f"""
Task Title: {task.title}
Task Description: {task.description}
Priority: {task.priority.value}
"""
        
        if task.context:
            prompt += f"Context: {task.context}\n"
        
        if memory_context:
            prompt += f"\n{memory_context}"
        
        prompt += f"""
Please complete this task as a {self.role}. Provide a comprehensive, professional response that addresses all aspects of the task. Focus on delivering actionable insights and recommendations.

Your response should be well-structured, detailed, and directly applicable to the task requirements.
"""
        
        return prompt
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance data"""
        total_tasks = self.tasks_completed + self.tasks_failed
        success_rate = (self.tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "name": self.name,
            "role": self.role,
            "type": self.type.value,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": success_rate,
            "skills": self.skills,
            "uptime": self.get_uptime()
        }
    
    def get_uptime(self) -> str:
        """Get agent uptime as readable string"""
        uptime = datetime.now() - self.created_at
        
        if uptime.days > 0:
            return f"{uptime.days} days"
        elif uptime.seconds > 3600:
            hours = uptime.seconds // 3600
            return f"{hours} hours"
        else:
            minutes = uptime.seconds // 60
            return f"{minutes} minutes"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary"""
        return {
            "name": self.name,
            "role": self.role,
            "type": self.type.value,
            "skills": self.skills,
            "performance": self.get_performance_metrics(),
            "created_at": self.created_at.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.name} ({self.role})"
    
    def __repr__(self) -> str:
        return f"Agent(name='{self.name}', role='{self.role}', type='{self.type.value}')" 