#!/usr/bin/env python3

"""
Simple Agent Manager
===================

Direct agent communication without complex infrastructure.
Users can talk to any agent directly.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

# Add project root to path first
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import modular calendar integration with fallback
try:
    from Integrations.Google.Calendar.calendar_manager import CalendarManager
except ImportError:
    # Create a minimal fallback calendar manager
    class CalendarManager:
        def __init__(self):
            logger.warning("Calendar integration not available - using fallback")
        
        async def get_events_for_date(self, *args, **kwargs):
            return "Calendar service not available"
        
        async def get_upcoming_events(self, *args, **kwargs):
            return "Calendar service not available"
        
        async def search_calendar_events(self, *args, **kwargs):
            return "Calendar service not available"

# Import user-agent mapping with fallback
try:
    from AgentUI.Backend.user_agent_mapping import UserAgentMatcher
    from Auth.User_management.user_models import UserRole
    user_agent_mapping_available = True
    logger = logging.getLogger(__name__)
    logger.info("✅ User-agent mapping available")
except ImportError as e:
    UserAgentMatcher = None
    UserRole = None
    user_agent_mapping_available = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ User-agent mapping not available: {e}")

logger = logging.getLogger(__name__)

class SimpleAgentManager:
    """Simple agent manager for direct communication"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.agent_info: Dict[str, Dict] = {}
        self.kernel = None
        
        # Initialize modular calendar manager
        self.calendar_manager = CalendarManager()
        logger.info("📅 Calendar manager initialized")
        
        # Initialize user-agent mapping
        self._create_agent_user_mapping()
    
    def _create_agent_user_mapping(self):
        """Create reverse mapping from agent_id to assigned real users"""
        self.agent_to_user_mapping = {}
        
        if not user_agent_mapping_available or not UserAgentMatcher:
            logger.warning("User-agent mapping not available, assigned_user fields will be empty")
            return
        
        try:
            # Query real users from database to find actual user assignments
            self._load_real_user_assignments()
            logger.info(f"✅ Created agent-to-user mapping for {len(self.agent_to_user_mapping)} agents")
            
        except Exception as e:
            logger.error(f"Error creating agent-user mapping: {e}")
            self.agent_to_user_mapping = {}
    
    def _load_real_user_assignments(self):
        """Load real user assignments from database"""
        try:
            from Utils.config import Config
            
            # Get Supabase client to query user database
            supabase_client = Config.get_supabase_client()
            if not supabase_client:
                logger.warning("Supabase client not available, cannot load real user assignments")
                return
            
            # Query all active users
            result = supabase_client.table('user_profiles').select('email, role, agent_assignments, is_active').eq('is_active', True).execute()
            
            if not result.data:
                logger.info("No active users found in database")
                return
            
            # Process each user to find their agent assignments
            for user_data in result.data:
                email = user_data.get('email')
                role = user_data.get('role')
                agent_assignments = user_data.get('agent_assignments', [])
                
                if not email:
                    continue
                
                # Check if user has agent assignments
                if agent_assignments and isinstance(agent_assignments, list):
                    for assignment in agent_assignments:
                        if isinstance(assignment, dict):
                            agent_type = assignment.get('agent_type')
                            access_level = assignment.get('access_level', 'limited')
                            
                            # Only include users with full access to agents
                            if agent_type and access_level == 'full':
                                # Convert agent type to agent_id format
                                agent_id = f"agent.{agent_type}"
                                
                                # Add user to agent mapping (support multiple users per agent)
                                if agent_id not in self.agent_to_user_mapping:
                                    self.agent_to_user_mapping[agent_id] = []
                                self.agent_to_user_mapping[agent_id].append(email)
                
                # Also check role-based assignments using the companion mapping
                if role:
                    try:
                        user_role = UserRole(role)
                        companion_agent_id = UserAgentMatcher.USER_AGENT_COMPANIONS.get(user_role)
                        
                        if companion_agent_id:
                            if companion_agent_id not in self.agent_to_user_mapping:
                                self.agent_to_user_mapping[companion_agent_id] = []
                            if email not in self.agent_to_user_mapping[companion_agent_id]:
                                self.agent_to_user_mapping[companion_agent_id].append(email)
                                
                    except ValueError:
                        # Invalid role, skip
                        continue
            
            # Keep as arrays for frontend to handle multiple users
            # Frontend will decide how to display them
            
            logger.info(f"Loaded real user assignments for {len(self.agent_to_user_mapping)} agents")
            
        except Exception as e:
            logger.error(f"Error loading real user assignments: {e}")
            self.agent_to_user_mapping = {}
        
    async def initialize(self):
        """Initialize the Azure OpenAI kernel"""
        try:
            import semantic_kernel as sk
            from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
            from Utils.config import Config
            
            self.kernel = sk.Kernel()
            
            # Get Azure OpenAI configuration
            config = Config.get_azure_config()
            logger.info(f"Azure OpenAI config: endpoint={config.get('endpoint')}, deployment={config.get('deployment_name')}")
            
            # Validate configuration
            if not config.get("api_key"):
                raise ValueError("AZURE_OPENAI_API_KEY not found")
            if not config.get("endpoint"):
                raise ValueError("AZURE_OPENAI_ENDPOINT not found")
            
            # Add Azure OpenAI chat completion
            azure_chat_service = AzureChatCompletion(
                service_id="main_chat",
                deployment_name=config.get("deployment_name", "gpt-4o"),
                endpoint=config.get("endpoint"),
                api_key=config.get("api_key"),
                api_version=config.get("api_version", "2024-12-01-preview")
            )
            
            self.kernel.add_service(azure_chat_service)
            logger.info(f"Azure OpenAI service added: {type(azure_chat_service)}")
            
            print("✅ Azure OpenAI kernel initialized")
            
            # Load agents after kernel is ready
            await self.load_agents()
            
        except Exception as e:
            print(f"⚠️ Kernel initialization failed: {e}")
            print("🔄 Agents will run in mock mode")
            self.kernel = None
    
    async def load_agents(self):
        """Load real agents from departments"""
        try:
            # Import real agents - including BusinessDev and Operations
            from Departments.Executive.agents.chief_marketing_officer import ExecutiveAgent
            from Departments.Marketing.content_marketing.agents.content_agent import ContentAgent
            from Departments.Marketing.digital_marketing.agents.seo_agent import SEOAgent
            from Departments.Marketing.digital_marketing.agents.analytics_agent import AnalyticsAgent
            
            # BusinessDev agents
            from Departments.BusinessDev.Agents.ipm_agent import IPMAgent
            from Departments.BusinessDev.Agents.bdm_agent import BDMAgent
            from Departments.BusinessDev.Agents.presales_engineer_agent import PresalesEngineerAgent
            
            # Operations agents
            from Departments.Operations.ClientSuccess.Agents.head_of_operations_agent import HeadOfOperationsAgent
            from Departments.Operations.ClientSuccess.Agents.senior_csm_agent import SeniorCSMAgent
            from Departments.Operations.ClientSuccess.Agents.senior_delivery_consultant_agent import SeniorDeliveryConsultantAgent
            from Departments.Operations.ClientSuccess.Agents.delivery_consultant_en_agent import DeliveryConsultantENAgent
            from Departments.Operations.ClientSuccess.Agents.delivery_consultant_bg_agent import DeliveryConsultantBGAgent
            from Departments.Operations.ClientSuccess.Agents.delivery_consultant_hu_agent import DeliveryConsultantHUAgent
            from Departments.Operations.Legal.Agents.legal_agent import LegalAgent
            from Departments.Operations.CustomReporting.Agents.reporting_manager_agent import ReportingManagerAgent
            from Departments.Operations.CustomReporting.Agents.reporting_specialist_agent import ReportingSpecialistAgent
            
            # Agent configurations: (class, agent_id, name, role, department)
            agent_configs = [
                # Executive and Leadership
                (ExecutiveAgent, "agent.executive_cmo", "Chief Marketing Officer", "Chief Marketing Officer", "Executive"),
                
                # Marketing agents
                (ContentAgent, "agent.content_specialist", "Content Specialist", "Content Specialist", "Marketing"),
                (SEOAgent, "agent.seo_specialist", "SEO Specialist", "SEO Specialist", "Marketing"),
                (AnalyticsAgent, "agent.analytics_specialist", "Analytics Specialist", "Analytics Specialist", "Marketing"),
                
                # BusinessDev agents
                (IPMAgent, "agent.ipm_agent", "IPM Agent", "ipm_agent", "BusinessDev"),
                (BDMAgent, "agent.bdm_agent", "BDM Agent", "bdm_agent", "BusinessDev"),
                (PresalesEngineerAgent, "agent.presales_engineer", "Presales Engineer", "presales_engineer", "BusinessDev"),
                
                # Operations agents
                (HeadOfOperationsAgent, "agent.head_of_operations", "Head of Operations", "head_of_operations", "Operations"),
                (SeniorCSMAgent, "agent.senior_csm", "Senior CSM", "senior_csm", "Operations"),
                (SeniorDeliveryConsultantAgent, "agent.senior_delivery_consultant", "Senior Delivery Consultant", "senior_delivery_consultant", "Operations"),
                (DeliveryConsultantENAgent, "agent.delivery_consultant_en", "Delivery Consultant (EN)", "delivery_consultant_en", "Operations"),
                (DeliveryConsultantBGAgent, "agent.delivery_consultant_bg", "Delivery Consultant (BG)", "delivery_consultant_bg", "Operations"),
                (DeliveryConsultantHUAgent, "agent.delivery_consultant_hu", "Delivery Consultant (HU)", "delivery_consultant_hu", "Operations"),
                (LegalAgent, "agent.legal_agent", "Legal Agent", "legal_agent", "Operations"),
                (ReportingManagerAgent, "agent.reporting_manager", "Reporting Manager", "reporting_manager", "Operations"),
                (ReportingSpecialistAgent, "agent.reporting_specialist", "Reporting Specialist", "reporting_specialist", "Operations"),
            ]
            
            # Create agent instances
            for agent_class, agent_id, name, role, department in agent_configs:
                try:
                    # Create agent instance
                    if self.kernel:
                        if agent_class == ExecutiveAgent:
                            agent = agent_class(self.kernel)
                        # BusinessDev agents
                        elif agent_class == IPMAgent:
                            agent = agent_class("IPM Agent", "International Partnerships Manager", self.kernel)
                        elif agent_class == BDMAgent:
                            agent = agent_class("BDM Agent", "Business Development Manager", self.kernel)
                        elif agent_class == PresalesEngineerAgent:
                            agent = agent_class("Presales Engineer", "Technical Solution Designer", self.kernel)
                        # Operations agents
                        elif agent_class == HeadOfOperationsAgent:
                            agent = agent_class("Head of Operations", "Strategic Operations Manager", self.kernel)
                        elif agent_class == SeniorCSMAgent:
                            agent = agent_class("Senior Customer Success Manager", "Enterprise Account Manager", self.kernel)
                        elif agent_class == SeniorDeliveryConsultantAgent:
                            agent = agent_class("Senior Delivery Consultant", "Complex Project Delivery Lead", self.kernel)
                        elif agent_class == DeliveryConsultantENAgent:
                            agent = agent_class("Delivery Consultant EN", "International Market Specialist", self.kernel)
                        elif agent_class == DeliveryConsultantBGAgent:
                            agent = agent_class("Delivery Consultant BG", "Bulgarian Market Specialist", self.kernel)
                        elif agent_class == DeliveryConsultantHUAgent:
                            agent = agent_class("Delivery Consultant HU", "Hungarian Market Specialist", self.kernel)
                        elif agent_class == LegalAgent:
                            agent = agent_class("Legal Agent", "Legal Compliance Specialist", self.kernel)
                        elif agent_class == ReportingManagerAgent:
                            agent = agent_class("Reporting Manager", "BI Strategy and Management", self.kernel)
                        elif agent_class == ReportingSpecialistAgent:
                            agent = agent_class("Reporting Specialist", "Technical Report Developer", self.kernel)
                        else:
                            agent = agent_class(self.kernel)
                    else:
                        # Mock agent for testing
                        agent = MockAgent(name, role)
                    
                    # Ensure the agent has memory manager initialized
                    if not hasattr(agent, 'memory_manager') or agent.memory_manager is None:
                        try:
                            from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
                            # Get memory collection name from agent if available
                            if hasattr(agent, '_get_memory_collection_name'):
                                collection_name = agent._get_memory_collection_name()
                            else:
                                # Fallback collection name based on department
                                collection_name = f"{department.lower()}-shared-memory"
                            
                            agent.memory_manager = EnhancedMemoryManager(
                                agent_name=name,
                                collection_name=collection_name,
                                lazy_init=True
                            )
                            
                            # For CMO/Executive agents, add multi-collection access
                            if "cmo" in role.lower() or "executive" in department.lower():
                                agent.memory_manager.accessible_collections = [
                                    "executive-shared-memory",
                                    "marketing-shared-memory", 
                                    "product-shared-memory",
                                    "content-shared-memory"
                                ]
                                logger.info(f"CMO multi-collection access enabled: {len(agent.memory_manager.accessible_collections)} collections")
                            
                            logger.info(f"Memory manager initialized for {name} with collection: {collection_name}")
                        except Exception as e:
                            logger.warning(f"Failed to initialize memory for {name}: {e}")
                    
                    # Add calendar skills to kernel (role-specific)
                    if self._should_have_calendar_access(role):
                        self._add_calendar_skills_to_kernel(agent)
                    
                    # Store agent
                    self.agents[agent_id] = agent
                    
                    # Get assigned user from mapping
                    assigned_user = self.agent_to_user_mapping.get(agent_id)
                    
                    self.agent_info[agent_id] = {
                        "id": agent_id,
                        "name": name,
                        "role": role,
                        "department": department,
                        "status": "online",
                        "capabilities": getattr(agent, 'capabilities', []),
                        "specialization": getattr(agent, 'specialization', role.lower().replace(' ', '_')),
                        "assigned_user": assigned_user
                    }
                    
                    print(f"✅ {name} ({agent_id}) loaded successfully")
                    
                except Exception as e:
                    print(f"⚠️ Failed to load {name}: {e}")
                    continue
                    
            print(f"🎉 {len(self.agents)} agents loaded successfully!")
            
        except Exception as e:
            print(f"❌ Failed to load agents: {e}")
    
    def _should_have_calendar_access(self, role: str) -> bool:
        """
        Determine if this agent should have calendar access based on user-agent companion matching
        All agents can DISCUSS calendar events, but only user's companion agent gets direct access
        """
        # For now, give all agents calendar access since they should be able to discuss calendar
        # The actual calendar access should be controlled by user authentication and permissions
        # when the calendar functionality is called, not by restricting the skill itself
        
        logger.info(f"✅ {role} gets calendar discussion capability")
        return True
    
    def _add_calendar_skills_to_kernel(self, agent):
        """Calendar functionality provided by CalendarManager in Gcalendar module"""
        # Legacy google_calendar_skill removed - now using Gcalendar module
        print(f"✅ Calendar plugin registered for {getattr(agent, 'name', 'unknown agent')}")
        logger.info(f"📅 Calendar plugin registered for {getattr(agent, 'name', 'unknown agent')}")
    
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
    
    def _detect_calendar_request(self, user_input: str) -> bool:
        """Detect if user is asking about calendar or scheduling"""
        calendar_keywords = [
            'calendar', 'schedule', 'meeting', 'meetings', 'appointment', 'appointments',
            'event', 'events', 'book', 'booking', 'available', 'availability',
            'free time', 'busy', 'when', 'time', 'date', 'today', 'tomorrow',
            'next week', 'this week', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday', 'reschedule', 'cancel', 'move meeting'
        ]
        
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in calendar_keywords)
    

    

    
    def _extract_search_terms(self, user_input: str, user_id: str = None) -> tuple:
        """Extract search terms from user input"""
        user_lower = user_input.lower()
        
        # Check for generic listing queries
        generic_queries = [
            'do you see', 'see any', 'any files', 'what files', 'list files', 'show files',
            'show me files', 'are there files', 'what to do', 'todo', 'tasks', 'available files',
            'whats the story', 'what is the story', 'story from', 'whats in', 'what is in'
        ]
        is_generic = any(phrase in user_lower for phrase in generic_queries)
        
        # Also treat as generic if asking about specific folder contents
        if any(folder_ref in user_lower for folder_ref in ['private folder', 'bdm_private', 'from the private']):
            is_generic = True
        
        if is_generic:
            # For generic queries, use empty query to get folder listings
            query = ""
        else:
            # Extract specific query terms
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
            if query_terms:
                query = ' '.join(query_terms)
            else:
                # For non-generic queries, use meaningful words, excluding stop words
                stop_words = {'do', 'you', 'see', 'any', 'can', 'find', 'me', 'the', 'a', 'an', 'is', 'are', 'what', 'where', 'how'}
                words = [word for word in user_input.split() if word.lower() not in stop_words]
                query = ' '.join(words[:5]) if words else user_input
        
        # Extract folder hint
        folder = None
        # Check for email searches first - they should use user-specific folders
        if any(term in user_lower for term in ['email', 'emails', 'from', 'message', 'mail']):
            if user_id:
                # Convert user_id to username for folder path
                username = user_id
                if '@' in username:
                    username = username.split('@')[0]
                folder = f'DigitalTwin_Brain/Users/{username}'
        elif any(term in user_lower for term in ['bdm_private', 'private folder', 'private']):
            folder = 'DigitalTwin_Brain/Business Development/bdm_private'
        # For file searches, only set specific folders if explicitly mentioned
        elif any(term in user_lower for term in ['operations folder', 'in operations', 'operations department only']):
            folder = 'DigitalTwin_Brain/Operations'
        elif any(term in user_lower for term in ['executive folder', 'in executive', 'executive department only']):
            folder = 'DigitalTwin_Brain/Executive'
        elif any(term in user_lower for term in ['marketing folder', 'in marketing', 'marketing department only']):
            folder = 'DigitalTwin_Brain/Marketing'
        elif any(term in user_lower for term in ['business development folder', 'in business dev', 'business dev only']):
            folder = 'DigitalTwin_Brain/Business Development'
        # For general file searches, don't set folder to search broadly across all DigitalTwin_Brain
        # This includes user folders since they may contain relevant files
        
        # Extract file type hint
        file_type = None
        if any(term in user_lower for term in ['pdf', 'report']):
            file_type = 'pdf'
        elif any(term in user_lower for term in ['excel', 'spreadsheet']):
            file_type = 'excel'
        elif any(term in user_lower for term in ['word', 'doc']):
            file_type = 'doc'
        
        return query, folder, file_type
    
    async def _handle_file_request(self, agent, user_input: str, user_id: str = None) -> str:
        """Handle file search requests using Google Drive search"""
        import time
        start_time = time.time()
        
        logger.info(f"Processing file request for agent: {agent.name}")
        logger.info(f"   - user_input: '{user_input}'")
        logger.info(f"   - user_id: '{user_id}'")
        try:
            if not hasattr(agent, 'gdrive_skill') or agent.gdrive_skill is None:
                return None  # Return None to fall back to AI response
            
            # Check for specific requests
            user_lower = user_input.lower()
            
            if any(term in user_lower for term in ['all files', 'everything', 'what files', 'list files']):
                # List available folders first, then search all
                folders_result = agent.gdrive_skill.list_folders()
                return folders_result
            
            elif 'recent' in user_lower:
                # Search recent files
                return agent.gdrive_skill.search_recent_files("7")
            
            elif any(folder in user_lower for folder in ['executive folder', 'marketing folder', 'product folder']):
                # List specific folder contents
                if 'executive' in user_lower:
                    return agent.gdrive_skill.search_by_folder("Executive")
                elif 'marketing' in user_lower:
                    return agent.gdrive_skill.search_by_folder("Marketing")
                elif 'product' in user_lower:
                    return agent.gdrive_skill.search_by_folder("Product Marketing")
            
            else:
                # General file search
                extraction_start = time.time()
                query, folder, file_type = self._extract_search_terms(user_input, user_id)
                extraction_end = time.time()
                
                logger.info(f"File request extraction results:")
                logger.info(f"   - Input: '{user_input}'")
                logger.info(f"   - Extracted query: '{query}'")
                logger.info(f"   - Extracted folder: '{folder}'")
                logger.info(f"   - Extracted file_type: '{file_type}'")
                logger.info(f"   - Extraction took: {extraction_end - extraction_start:.3f}s")
                
                # REMOVED: Department folder defaulting logic - let gdrive_skill handle folder logic
                logger.info(f"Using gdrive_skill default folder logic")
                # Attempt to collect knowledge and synthesize an answer first
                try:
                    # Safe import with fallback
                    import sys
                    from pathlib import Path
                    project_root = str(Path(__file__).parent.parent.parent)
                    if project_root not in sys.path:
                        sys.path.append(project_root)
                    
                    try:
                        # Use new hybrid search system
                        from Integrations.Google.Search.adapters import get_search_adapter
                        hybrid_search = get_search_adapter()
                    except ImportError as e:
                        logger.error(f"Failed to import hybrid search system: {e}")
                        return None
                    user_id = getattr(agent.gdrive_skill, '_current_user_id', None)
                    
                    # Auto-derive department folder if none explicitly detected
                    derived_folder = folder
                    if not derived_folder and hasattr(agent, 'gdrive_skill'):
                        try:
                            agent_name_ctx = getattr(agent.gdrive_skill, '_current_agent_name', None)
                            if agent_name_ctx and hasattr(agent.gdrive_skill, 'get_agent_department_folder'):
                                derived_folder = agent.gdrive_skill.get_agent_department_folder(agent_name_ctx)
                                logger.info(f"🎯 AUTO-DERIVED DEPARTMENT: {agent_name_ctx} → {derived_folder}")
                        except Exception:
                            pass
                    
                    logger.info(f"🔍 CALLING hybrid search: query='{query}', folder='{derived_folder}', user_id='{user_id}'")
                    
                    # Use hybrid search system
                    search_results = hybrid_search.unified_search(
                        query=query,
                        max_results=5,
                        user_id=user_id,
                        include_emails=True,
                        include_files=True
                    )
                    
                    # Extract knowledge and sources from hybrid search results
                    knowledge = ""
                    sources = []
                    
                    if search_results.get('success') and search_results.get('results'):
                        for result in search_results['results']:
                            # Extract content/snippet for knowledge
                            content = result.get('content', result.get('snippet', ''))
                            if content:
                                knowledge += content + "\n\n"
                            
                            # Add to sources
                            source_info = {
                                'name': result.get('name', result.get('subject', 'Unknown')),
                                'url': result.get('web_view_link', result.get('url', '')),
                                'type': result.get('source', 'file')
                            }
                            sources.append(source_info)
                    
                    # Limit knowledge length (equivalent to max_chars=9000)
                    if len(knowledge) > 9000:
                        knowledge = knowledge[:9000] + "..."
                    logger.info(f"📚 KNOWLEDGE RECEIVED: {len(knowledge)} chars, {len(sources)} sources")
                    
                    if knowledge and hasattr(self, 'kernel') and self.kernel:
                        from semantic_kernel.contents import ChatHistory
                        from semantic_kernel.contents.chat_message_content import ChatMessageContent
                        from semantic_kernel.contents.utils.author_role import AuthorRole
                        chat_history = ChatHistory()
                        system_prompt = (
                            "You are a helpful assistant. Use ONLY the provided knowledge snippets from Google "
                            "Drive to answer the user's question. Synthesize the information and cite specific file names when referencing content."
                        )
                        chat_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=system_prompt))
                        chat_history.add_message(ChatMessageContent(role=AuthorRole.USER, content=f"Question: {user_input}\n\nKnowledge from files:\n{knowledge}"))
                        chat_completion = self.kernel.get_service("main_chat")
                        answer = await chat_completion.get_chat_message_content(
                            chat_history=chat_history,
                            settings=chat_completion.get_prompt_execution_settings_class()(max_tokens=500, temperature=0.4)
                        )
                        answer_text = str(answer.content)
                        
                        # Add source file references at the end if available
                        if sources:
                            source_links = []
                            for source in sources:
                                if isinstance(source, dict):
                                    # Format with clickable links
                                    name = source.get('name', 'Unknown File')
                                    view_link = source.get('web_view_link', '')
                                    download_link = source.get('download_link', '')
                                    if view_link and download_link:
                                        source_links.append(f"**{name}** ([View]({view_link}) | [Download]({download_link}))")
                                    elif view_link:
                                        source_links.append(f"**{name}** ([View]({view_link}))")
                                    else:
                                        source_links.append(f"**{name}**")
                                else:
                                    # Fallback for string sources
                                    source_links.append(f"**{source}**")
                            
                            if source_links:
                                answer_text += f"\n\n*Sources: {', '.join(source_links)}*"
                        
                        logger.info(f"✅ KNOWLEDGE SYNTHESIS SUCCESS: Generated {len(answer_text)} char response")
                        return answer_text
                    else:
                        logger.debug(f"❌ Synthesis skipped: knowledge={len(knowledge)} chars, kernel={hasattr(self, 'kernel')}")
                except Exception as e:
                    logger.error(f"❌ Knowledge synthesis failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Fallback to file listing if knowledge synthesis fails
                logger.info(f"Executing file search with gdrive_skill")
                logger.info(f"   - Final query: '{query}'")
                logger.info(f"   - Final folder: '{folder}'")
                logger.info(f"   - Final file_type: '{file_type}'")
                
                search_start = time.time()
                file_list = agent.gdrive_skill.search_files(query, folder, file_type)
                search_end = time.time()
                
                total_time = time.time() - start_time
                logger.info(f"⏱️ COMM MANAGER TIMING:")
                logger.info(f"   - gdrive_skill.search_files took: {search_end - search_start:.3f}s")
                logger.info(f"   - Total _handle_file_request took: {total_time:.3f}s")
                
                return file_list
            
        except Exception as e:
            logger.error(f"Error in file search: {e}")
            return None  # Return None to fall back to AI response
    

    

    
    async def send_message_to_agent(self, agent_id: str, message: str, sender_name: str = "User", conversation_context: str = "", user_role: str = "team_member", permissions_summary: dict = None, user_id: str = None) -> str:
        """Send a message directly to an agent and get response using Azure OpenAI with memory integration and conversation context"""
        if agent_id not in self.agents:
            return f"Error: Agent {agent_id} not found"
        
        agent = self.agents[agent_id]
        agent_info = self.agent_info[agent_id]
        
        # Set user context for agent skills (especially Google Drive search)
        if user_id and hasattr(agent, 'plugins'):
            try:
                
                # Extract agent name from agent_id (e.g., "agent.bdm_agent" → "bdm_agent")
                agent_name = agent_id.split('.')[-1] if '.' in agent_id else agent_id
                
                # Find Google Drive search skill and set user context
                for plugin_name, plugin in agent.plugins.items():
                    if hasattr(plugin, 'search_files'):  # Google Drive search skill
                        setattr(plugin, '_current_user_id', user_id)
                        setattr(plugin, '_current_agent_name', agent_name)
                        logger.info(f"✅ Set user_id {user_id} and agent_name {agent_name} context for {plugin_name}")
                    else:
                        logger.info(f"ℹ️ Plugin {plugin_name} doesn't have search_files method")
            except Exception as e:
                logger.warning(f"❌ Could not set user context on agent skills: {e}")
        else:
            if not user_id:
                logger.warning(f"⚠️ No user_id provided for agent {agent_id}")
            if not hasattr(agent, 'plugins'):
                logger.warning(f"⚠️ Agent {agent_id} has no plugins attribute")

        # Check for calendar requests with companion matching
        if self._detect_calendar_request(message):
            # Import here to avoid circular imports with fallback
            try:
                from user_agent_mapping import user_agent_matcher
            except ImportError:
                # Fallback to allow all interactions
                def user_agent_matcher(user_id: str, agent_id: str, message: str):
                    return True
            
            # Check if user can access calendar through this agent
            if user_agent_matcher.can_user_access_calendar_via_agent(user_role, agent_id):
                logger.info(f"🗓️ {agent_info['name']} processing calendar request for authorized user '{user_role}'")
                
                # PRODUCTION FIX: Use real user ID for calendar integration
                if user_id:
                    try:
                        # Process calendar request with real authenticated user ID
                        calendar_response = await self.calendar_manager.process_request(message, user_id)
                        if calendar_response:
                            logger.info(f"✅ Calendar request processed successfully for user {user_id}")
                            return calendar_response
                        else:
                            logger.warning(f"⚠️ Calendar request not recognized or failed for user {user_id}")
                            # Fall through to normal AI response
                    except Exception as e:
                        logger.error(f"❌ Error processing calendar request for user {user_id}: {e}")
                        return f"❌ I'm having trouble accessing your calendar right now. Error: {str(e)}"
                else:
                    logger.warning(f"⚠️ Calendar request detected but no user_id provided")
                    return f"❌ I need your user authentication to access your calendar. Please make sure you're properly logged in."
            else:
                logger.info(f"🚫 Calendar access denied for user '{user_role}' via agent '{agent_id}' - not authorized companion")
                return f"I can discuss calendar topics with you, but I don't have direct access to your calendar. For calendar management, please use your designated companion agent."
        
        # Check if this is a file request with companion matching
        if self._detect_file_request(message):
            logger.info(f"🔍 {agent_info['name']} detected file request: {message}")
            
            # Import here to avoid circular imports with fallback
            try:
                from user_agent_mapping import user_agent_matcher
            except ImportError:
                # Fallback to allow all interactions
                def user_agent_matcher(user_id: str, agent_id: str, message: str):
                    return True
            
            # Extract folder information from the message to check for private folder access
            query, folder, file_type = self._extract_search_terms(message, user_id)
            logger.info(f"🔍 Extracted search terms: query='{query}', folder='{folder}', file_type='{file_type}'")
            
            # Check if user can access files through this agent (with folder-specific authorization)
            file_access_allowed = user_agent_matcher.can_user_access_files_via_agent(user_role, agent_id, folder)
            logger.info(f"🔐 File access check: user_role='{user_role}', agent_id='{agent_id}', folder='{folder}', allowed={file_access_allowed}")
            
            if file_access_allowed:
                logger.info(f"📁 {agent_info['name']} processing file request for authorized user '{user_role}'")
                file_result = await self._handle_file_request(agent, message)
                if file_result and not file_result.startswith("I don't currently have access"):
                    logger.info(f"✅ {agent_info['name']} returning Google Drive search results")
                    return file_result
                else:
                    logger.warning(f"⚠️ File request handled but returned: {file_result[:100] if file_result else 'None'}...")
            else:
                logger.info(f"🚫 File access denied for user '{user_role}' via agent '{agent_id}' - not authorized for folder '{folder}'")
                if folder and ("private" in folder.lower() or "_private" in folder.lower()):
                    return f"I cannot access private folders. Private folders are strictly restricted to the designated department member only. For private {agent_info['name']} files, please use your designated companion agent if you are authorized."
                else:
                    return f"I can discuss files and documents with you, but I don't have direct access to your Google Drive. For file management, please use your designated companion agent."
            
            # If no access or error, fall through to normal AI response
        
        # Handle ClickUp queries directly (before AI response)
        clickup_keywords = ['clickup', 'task', 'tasks', 'project', 'projects', 'deadline', 'assignee']
        if any(keyword in message.lower() for keyword in clickup_keywords) and hasattr(agent, 'clickup_tools') and agent.clickup_tools:
            try:
                logger.info(f"Detected ClickUp query for {agent_id}, attempting direct ClickUp access")
                
                # Check ClickUp connection status first
                connection_status = agent.clickup_tools.get_connection_status(user_id)
                connection_data = json.loads(connection_status) if connection_status else {"connected": False}
                
                if connection_data.get("connected"):
                    # Check if asking for specific project
                    project_search = None
                    message_lower = message.lower()
                    
                    # Look for project mentions
                    project_patterns = ['project 1', 'project1', 'project 2', 'project2', 'from project']
                    for pattern in project_patterns:
                        if pattern in message_lower:
                            if 'project 1' in message_lower or 'project1' in message_lower:
                                project_search = 'project 1'
                            elif 'project 2' in message_lower or 'project2' in message_lower:
                                project_search = 'project 2'
                            break
                    
                    # Get tasks (either all tasks or project-specific)
                    if project_search:
                        tasks_result = agent.clickup_tools.search_tasks_in_project(user_id, project_search)
                        tasks_data = json.loads(tasks_result) if tasks_result else {"success": False, "tasks": []}
                        header = f'Here are the ClickUp tasks associated with "{project_search.title()}":'
                    else:
                        tasks_result = agent.clickup_tools.get_my_tasks(user_id)
                        tasks_data = json.loads(tasks_result) if tasks_result else {"success": False, "tasks": []}
                        header = "Here are your ClickUp tasks:"
                    
                    if tasks_data.get("success") and tasks_data.get("tasks"):
                        tasks = tasks_data["tasks"]
                        
                        # Sort tasks by extracting numbers from task names (Task 1, Task 2, Task 3)
                        def sort_key(task):
                            name = task.get('name', '').lower()
                            # Try to extract number from task name (e.g., "task 1" -> 1)
                            import re
                            match = re.search(r'task\s*(\d+)', name)
                            if match:
                                return int(match.group(1))
                            
                            # Fallback to alphabetical sort
                            return name
                        
                        tasks.sort(key=sort_key)
                        
                        # Create formatted response like user's example
                        task_summary = f"{header}\n\n"
                        
                        for i, task in enumerate(tasks[:10]):  # Limit to first 10 tasks
                            task_name = task.get('name', 'Untitled Task')
                            status = task.get('status', 'To Do')
                            assignees = task.get('assignees', [])
                            created_date = task.get('created', '')
                            task_url = task.get('url', '')
                            
                            # Convert timestamp to readable date
                            if created_date:
                                try:
                                    from datetime import datetime
                                    created_dt = datetime.fromtimestamp(int(created_date) / 1000)
                                    created_formatted = created_dt.strftime('%Y-%m-%d')
                                except:
                                    created_formatted = created_date
                            else:
                                created_formatted = 'Unknown'
                            
                            # Format assignees
                            assigned_to = ', '.join(assignees) if assignees else 'Unassigned'
                            
                            # Get subtasks info (now included in main task data)
                            subtasks_count = task.get('subtasks_count', 0)
                            subtasks_list = task.get('subtasks', [])
                            subtasks_info = "None" if subtasks_count == 0 else f"{subtasks_count} subtask(s)"
                            
                            task_summary += f"**{i+1}. {task_name}**\n"
                            task_summary += f"   - **Status:** {status}\n"
                            task_summary += f"   - **Assigned To:** {assigned_to}\n"
                            task_summary += f"   - **Created On:** {created_formatted}\n"
                            task_summary += f"   - **Subtasks:** {subtasks_info}\n"
                            
                            if task_url:
                                task_summary += f"   - [View Task]({task_url})\n"
                            else:
                                task_summary += f"   - View Task (URL not available)\n"
                            
                            # Add subtask links if available (using pre-loaded subtask data)
                            if subtasks_count > 0 and subtasks_list:
                                for subtask in subtasks_list[:3]:  # Show first 3 subtasks
                                    subtask_name = subtask.get('name', 'Unnamed subtask')
                                    subtask_status = subtask.get('status', 'To Do')
                                    subtask_url = subtask.get('url', '')
                                    task_summary += f"      - **{subtask_name}** (Status: {subtask_status})\n"
                                    if subtask_url:
                                        task_summary += f"        - [View Subtask]({subtask_url})\n"
                            
                            task_summary += "\n"
                        
                        if len(tasks) > 10:
                            task_summary += f"... and {len(tasks) - 10} more tasks.\n\n"
                        
                        task_summary += "Let me know if you'd like help updating these tasks, assigning team members, or setting priorities!"
                        
                        logger.info(f"Successfully retrieved {len(tasks)} ClickUp tasks for user {user_id}")
                        return task_summary
                    else:
                        return f"I have access to your ClickUp account, but I didn't find any tasks{f' for {project_search}' if project_search else ''}. This could mean you don't have any tasks assigned to you, or they might be in spaces I don't have access to. Would you like me to help you create a new task?"
                else:
                    return "I can see you're asking about ClickUp tasks, but I don't have access to your ClickUp account yet. Please connect your ClickUp account in the settings to enable task management features."
                    
            except Exception as e:
                logger.error(f"Error handling ClickUp query: {e}")
                # Fall through to normal AI response
        
        try:
            # Use Azure OpenAI kernel to generate intelligent responses
            if self.kernel:
                logger.info(f"Processing message for {agent_id} using Azure OpenAI with memory integration")
                
                # Get relevant knowledge from agent's memory first
                relevant_knowledge = ""
                if hasattr(agent, 'memory_manager') and agent.memory_manager:
                    try:
                        logger.info(f"Searching {agent_info['name']}'s knowledge base...")
                        relevant_knowledge = await agent.memory_manager.get_relevant_context(message, max_memories=5)
                        if relevant_knowledge:
                            logger.info(f"Found relevant knowledge for {agent_info['name']}: {len(relevant_knowledge)} characters")
                        else:
                            logger.info(f"No relevant knowledge found for {agent_info['name']}")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve knowledge for {agent_info['name']}: {e}")
                        relevant_knowledge = ""
                
                # Create agent-specific system prompt with knowledge
                agent_name = agent_info['name']
                agent_role = agent_info['role']
                agent_department = agent_info['department']
                agent_specialization = agent_info['specialization']
                
                # Define newline for use in f-string
                nl = '\n'
                
                # Base system prompt with inter-agent communication
                system_prompt = f"""You are {agent_name}, a {agent_role} in the {agent_department} department.
Your specialization is {agent_specialization}.

You are an expert professional who provides helpful, accurate, and insightful responses in a warm, conversational manner.
Stay in character as {agent_name} and provide responses that align with your role and expertise.
Be natural, knowledgeable, and genuinely helpful in your communication style.

Current conversation context:
- User: {sender_name}
- Your role: {agent_role}
- Your department: {agent_department}

{f"Previous conversation context:{nl}{conversation_context}{nl}" if conversation_context else ""}

INTER-AGENT COMMUNICATION:
When users ask you to get information from other agents or departments, you can communicate with:
- Chief Marketing Officer (CMO): Marketing strategy, campaigns, brand management
- Content Specialist: Content creation, marketing materials
- SEO Specialist: Search optimization, website performance
- Analytics Specialist: Data analysis, metrics, performance

If asked to get information from another agent, respond naturally by saying something like:
"I'll need to check with [Agent Name] about this. Let me reach out to them for you..."

Then provide the information you would expect that agent to have.

IMPORTANT: When relevant knowledge is available, use specific data, numbers, and facts from your knowledge base. 
Always reference actual metrics, financial data, and concrete information when available.

COMMUNICATION STYLE:
- Write in natural, flowing paragraphs
- Use a warm but professional tone
- Avoid bullet points, emojis, or special formatting symbols
- Be conversational and personable
- Show genuine interest in helping
- Use transitions between thoughts naturally
"""

                # Add knowledge context if available
                if relevant_knowledge:
                    system_prompt += f"""

{relevant_knowledge}

CRITICAL: Use the above knowledge context to provide accurate, data-driven responses. 
When discussing financials, metrics, or strategies, reference the specific information from your knowledge base.
Provide concrete numbers, percentages, and facts rather than generic responses.
"""
                
                # Create chat completion using Azure OpenAI
                from semantic_kernel.contents import ChatHistory
                from semantic_kernel.contents.chat_message_content import ChatMessageContent
                from semantic_kernel.contents.utils.author_role import AuthorRole
                
                chat_history = ChatHistory()
                chat_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=system_prompt))
                chat_history.add_message(ChatMessageContent(role=AuthorRole.USER, content=message))
                
                # Get chat completion service
                chat_completion = self.kernel.get_service("main_chat")
                logger.info(f"Got chat completion service: {type(chat_completion)}")
                
                # Set user_id in agent plugins for ClickUp access with fallback formats
                if user_id and hasattr(agent, 'plugins'):
                    for plugin_name, plugin in agent.plugins.items():
                        if hasattr(plugin, 'search_tasks_by_keyword'):  # ClickUp tools
                            setattr(plugin, '_current_user_id', user_id)
                            # Also set fallback user ID formats for compatibility
                            if '@' in str(user_id):
                                setattr(plugin, '_fallback_user_id', user_id.split('@')[0])
                            else:
                                setattr(plugin, '_fallback_user_id', f"{user_id}@gmail.com")
                            logger.info(f"✅ Set user_id {user_id} for ClickUp plugin {plugin_name}")
                
                # Also set user_id in the agent's kernel plugins for function calling
                if user_id and hasattr(agent, 'kernel') and hasattr(agent.kernel, 'plugins'):
                    for plugin_name, plugin_instance in agent.kernel.plugins.items():
                        if hasattr(plugin_instance, 'search_tasks_by_keyword'):
                            setattr(plugin_instance, '_current_user_id', user_id)
                            logger.info(f"✅ Set user_id {user_id} for kernel ClickUp plugin {plugin_name}")
                
                # Generate response with function calling enabled
                try:
                    from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
                    
                    # Create execution settings with function calling enabled
                    execution_settings = chat_completion.get_prompt_execution_settings_class()(
                        max_tokens=500,
                        temperature=0.7,
                        function_choice_behavior=FunctionChoiceBehavior.Auto()
                    )
                    
                    # Use the agent's kernel for function calling if available
                    agent_kernel = agent.kernel if hasattr(agent, 'kernel') else self.kernel
                    
                    response = await chat_completion.get_chat_message_content(
                        chat_history=chat_history,
                        settings=execution_settings,
                        kernel=agent_kernel
                    )
                    response_text = str(response.content)
                    logger.info(f"Generated response for {agent_id} with function calling: {response_text[:100]}...")
                    
                except Exception as function_error:
                    logger.warning(f"Function calling failed for {agent_id}: {function_error}, falling back to regular chat")
                    
                    # Fallback to regular chat completion
                    execution_settings = chat_completion.get_prompt_execution_settings_class()(
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    response = await chat_completion.get_chat_message_content(
                        chat_history=chat_history,
                        settings=execution_settings
                    )
                    response_text = str(response.content)
                    logger.info(f"Generated fallback response for {agent_id}: {response_text[:100]}...")
                
                # Check if the response indicates inter-agent communication
                if "I'll need to check with" in response_text or "Let me reach out to them" in response_text:
                    
                    # Parse which agent they want to consult
                    consultation_response = await self._handle_inter_agent_consultation(
                        agent_id, agent_info, message, response_text, sender_name
                    )
                    
                    return consultation_response
                
                return response_text
            else:
                logger.warning(f"Kernel not available for {agent_id}")
                return f"Hello! I'm {agent_info['name']}, your {agent_info['role']}. I received your message: '{message}'. However, my AI capabilities are currently unavailable. Please try again later."
            
        except Exception as e:
            logger.error(f"Error processing message for {agent_id}: {e}")
            import traceback
            traceback.print_exc()
            return f"I'm sorry, I encountered an error processing your request: {str(e)}. Please try again."
    
    def get_available_agents(self) -> List[Dict]:
        """Get list of all available agents"""
        return list(self.agent_info.values())
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """Get information about a specific agent"""
        return self.agent_info.get(agent_id)
    
    async def _handle_inter_agent_consultation(self, requesting_agent_id: str, requesting_agent_info: Dict, 
                                             original_message: str, initial_response: str, sender_name: str) -> str:
        """Handle inter-agent consultation with full debug tracking"""
        
        print(f"\nStarting consultation process for {requesting_agent_info['name']}")
        print(f"Original message: {original_message}")
        
        # Parse which agent to consult
        target_agent_name = None
        target_agent_id = None
        
        # Map agent names to IDs
        agent_name_mapping = {
            "Chief Marketing Officer": "agent.executive_cmo",
            "CMO": "agent.executive_cmo", 
            "Content Specialist": "agent.content_specialist",
            "SEO Specialist": "agent.seo_specialist",
            "Analytics Specialist": "agent.analytics_specialist"
        }
        
        # Find which agent to consult
        for name, agent_id in agent_name_mapping.items():
            if name.lower() in initial_response.lower():
                target_agent_name = name
                target_agent_id = agent_id
                break
        
        if not target_agent_id or target_agent_id not in self.agents:
            print(f"Target agent not found or not available")
            return f"{initial_response}\n\nI apologize, but I wasn't able to connect with the right person for this request. They might be unavailable at the moment."
        
        target_agent_info = self.agent_info[target_agent_id]
        print(f"Target agent: {target_agent_info['name']}")
        
        # Create consultation message
        consultation_message = f"Hi {target_agent_info['name']}, I'm {requesting_agent_info['name']}. A user asked me: '{original_message}'. Can you help with this?"
        
        print(f"Sending consultation message to {target_agent_info['name']}")
        
        # Get response from target agent
        try:
            target_response = await self.send_message_to_agent(
                target_agent_id, 
                consultation_message, 
                f"{requesting_agent_info['name']} (on behalf of {sender_name})"
            )
            
            print(f"Received response from {target_agent_info['name']}")
            
            # Combine responses naturally
            combined_response = f"""{initial_response}

I connected with {target_agent_info['name']} about your question. Here's what they shared with me:

{target_response}

I hope this gives you the comprehensive information you were looking for. Please let me know if you need any clarification or have additional questions about this topic."""
            
            print(f"Consultation completed successfully")
            
            return combined_response
            
        except Exception as e:
            print(f"Error during consultation: {e}")
            
            return f"{initial_response}\n\nI apologize, but I encountered a technical issue while trying to reach out to {target_agent_name}. Please try your request again in a moment."


class MockAgent:
    """Mock agent for testing when kernel fails"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.capabilities = ["demo_mode"]
        self.specialization = role.lower().replace(' ', '_')
    
    def work_on_task(self, task):
        return f"Hello! I'm {self.name}, your {self.role}. I received your task: '{task.description}'. In demo mode, I would help you with this request using my expertise in {self.specialization}."
    
    def respond(self, message):
        return f"Hello! I'm {self.name}, your {self.role}. You said: '{message}'. How can I assist you today?"


# Global instance
agent_manager = SimpleAgentManager() 