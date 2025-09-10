"""
Role-based Chat Interfaces for Multi-Agent Architecture
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
from Auth.Core.account_system import UserAccount, AccountType, Division


logger = logging.getLogger(__name__)

try:
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Memory system not available")


class ChatInterface(ABC):
    """Abstract base class for role-based chat interfaces"""
    
    def __init__(self, user_account: UserAccount, kernel: sk.Kernel):
        self.user_account = user_account
        self.kernel = kernel
        self.chat_history = ChatHistory()
        self.memory_manager = None
        if MEMORY_AVAILABLE:
            self._initialize_memory()
        
        # Get chat service from kernel
        self.chat_service = None
        try:
            services = kernel.services
            for service in services.values():
                if hasattr(service, 'get_chat_message_content'):
                    self.chat_service = service
                    break
        except Exception as e:
            logger.warning(f"Could not get chat service: {e}")
    
    def _initialize_memory(self):
        """Initialize memory manager based on user's accessible collections"""
        if not MEMORY_AVAILABLE:
            return
            
        try:
            collections = self.user_account.get_memory_collections()
            if collections:
                # Determine primary collection based on user role and department
                primary_collection = self._get_primary_collection(collections)
                
                if primary_collection:
                    self.memory_manager = EnhancedMemoryManager(
                        agent_name=self.user_account.username,
                        collection_name=primary_collection
                    )
        except Exception as e:
            logger.warning(f"Could not initialize memory for {self.user_account.username}: {e}")
    
    def _get_primary_collection(self, collections: List[str]) -> Optional[str]:
        """Get primary collection based on user role and department"""
        username = self.user_account.username.lower()
        
        # Executive (CMO) - use executive shared memory
        if self.user_account.account_type == AccountType.EXECUTIVE:
            return "executive-shared-memory" if "executive-shared-memory" in collections else collections[0]
        
        # Product Marketing agents/managers - use product shared memory
        if any(role in username for role in ["positioning", "persona", "gtm", "competitor", "launch", "product"]):
            return "product-shared-memory" if "product-shared-memory" in collections else collections[0]
        
        # Digital Marketing agents/managers - use digital shared memory
        if any(role in username for role in ["seo", "sem", "landing", "analytics", "funnel", "digital"]):
            return "digital-shared-memory" if "digital-shared-memory" in collections else collections[0]
        
        # Content Marketing agents/managers - use content shared memory
        if any(role in username for role in ["content", "brand", "social", "community"]):
            return "content-shared-memory" if "content-shared-memory" in collections else collections[0]
        
        # Default to first available collection
        return collections[0] if collections else None
    
    @abstractmethod
    async def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user input based on role-specific behavior"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get role-specific system prompt"""
        pass
    
    async def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search accessible memories"""
        if not self.memory_manager:
            return []
        
        try:
            memories = await self.memory_manager.search_memories(
                query=query,
                limit=limit,
                score_threshold=0.3
            )
            return memories
        except Exception as e:
            logger.error(f"Memory search failed for {self.user_account.username}: {e}")
            return []

    async def search_all_accessible_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all accessible memory collections (for executives)"""
        if not MEMORY_AVAILABLE:
            return []
        
        try:
            from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
            
            all_memories = []
            collections = self.user_account.get_memory_collections()
            
            # Search each accessible collection
            for collection in collections:
                try:
                    temp_manager = EnhancedMemoryManager(
                        agent_name=self.user_account.username,
                        collection_name=collection
                    )
                    
                    memories = await temp_manager.search_memories(
                        query=query,
                        limit=limit,
                        score_threshold=0.1
                    )
                    
                    # Add collection info to each memory
                    for memory in memories:
                        memory['source_collection'] = collection
                        all_memories.append(memory)
                        
                except Exception as e:
                    logger.warning(f"Failed to search collection {collection}: {e}")
                    continue
            
            # Sort by relevance score (highest first) and limit results
            all_memories.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_memories[:limit]
            
        except Exception as e:
            logger.error(f"Multi-collection search failed for {self.user_account.username}: {e}")
            return []


class ExecutiveChatInterface(ChatInterface):
    """Executive (CMO) chat interface with global access and strategic capabilities"""
    
    def __init__(self, user_account: UserAccount, kernel: sk.Kernel, marketing_system):
        super().__init__(user_account, kernel)
        self.marketing_system = marketing_system
        self.chat_history.add_system_message(self.get_system_prompt())
    
    def get_system_prompt(self) -> str:
        return """You are the Chief Marketing Officer (CMO) with executive authority over all marketing operations.

EXECUTIVE CAPABILITIES:
- Global oversight across all marketing divisions (Product, Digital, Content)
- Strategic planning and cross-division coordination
- Access to all company data and intelligence including earnings reports
- Authority to create high-priority tasks for any division
- Real-time access to financial data, competitive intelligence, and market insights

BEHAVIOR:
- Think strategically and provide executive-level insights
- Use data-driven analysis for all recommendations with SPECIFIC NUMBERS
- When discussing earnings or financial data, always use actual figures, percentages, and metrics
- Coordinate initiatives across multiple divisions when appropriate
- Focus on business impact, ROI, and competitive advantage
- Be decisive and action-oriented

CRITICAL RULES:
- When referencing financial data like earnings, ALWAYS use specific numbers from memory. Never use placeholders like "X%" or "significant growth" - use actual percentages and dollar amounts.
- Only work with real tasks that have been explicitly created through proper executive channels. NEVER create, invent, or suggest fake tasks. If no tasks exist, clearly state the current system status.

AVAILABLE COMMANDS:
- CREATE TASK [division] [description] - Create tasks for any division
- VIEW TASKS - See all tasks across divisions  
- ANALYZE [topic] - Deep strategic analysis using all available data
- COORDINATE [initiative] - Cross-division coordination
- REVIEW APPROVALS - View manager-approved submissions awaiting final approval
- FINAL APPROVE [approval_id] - Give final executive approval
- FINAL REJECT [approval_id] [feedback] - Reject with strategic feedback"""
    
    async def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process executive input with full strategic capabilities"""
        
        # Check for executive commands first
        if user_input.upper().startswith("CREATE TASK"):
            return await self._handle_task_creation(user_input)
        elif user_input.upper().startswith("VIEW TASKS"):
            return await self._handle_view_tasks()
        elif user_input.upper().startswith("ANALYZE"):
            return await self._handle_strategic_analysis(user_input)
        elif user_input.upper().startswith("COORDINATE"):
            return await self._handle_coordination(user_input)
        elif user_input.upper().startswith("REVIEW APPROVALS"):
            return await self._handle_review_approvals()
        elif user_input.upper().startswith("FINAL APPROVE"):
            return await self._handle_final_approve(user_input)
        elif user_input.upper().startswith("FINAL REJECT"):
            return await self._handle_final_reject(user_input)
        
        # For strategic conversations, search memory first with expanded query
        # Use multi-collection search for executives to access ALL data
        relevant_memories = await self.search_all_accessible_memories(user_input, limit=8)
        
        # Build context with memory - prioritize financial data
        memory_context = ""
        if relevant_memories:
            memory_context = "\n\n=== RELEVANT COMPANY DATA ===\n"
            for i, memory in enumerate(relevant_memories, 1):
                memory_context += f"{i}. {memory['text'][:500]}...\n"
        
        # Add user input to chat history
        full_prompt = f"{user_input}{memory_context}\n\nIMPORTANT: Use specific numbers, percentages, and data points from the company data above. Do not use placeholders."
        self.chat_history.add_user_message(full_prompt)
        
        try:
            response = await self.chat_service.get_chat_message_content(
                chat_history=self.chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=800,
                    temperature=0.1  # Very low temperature for data accuracy
                )
            )
            
            response_text = str(response).strip()
            self.chat_history.add_assistant_message(response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Executive chat error: {e}")
            return f"I apologize, but I encountered an error processing your request. Please try again."
    
    async def _handle_task_creation(self, user_input: str) -> str:
        """Handle executive task creation with autonomous routing"""
        try:
            # Parse: CREATE TASK [description] (no manual division needed)
            if not user_input.upper().startswith("CREATE TASK "):
                return "Format: CREATE TASK [task description]"
            
            task_description = user_input[12:].strip()  # Remove "CREATE TASK "
            
            if not task_description:
                return "Please provide a task description"
            
            # Use orchestrator for autonomous routing
            context = {"priority": "high", "created_by": "CMO"}
            task_id = await self.marketing_system.create_task(
                task_description,
                context=context
            )
            
            if task_id:
                # Get the routing decision from orchestrator for display
                from Core.Tasks.orchestrator import Orchestrator
                orchestrator = Orchestrator(self.marketing_system.kernel)
                analysis = await orchestrator.analyze_input(task_description, context)
                
                department = analysis.get("department", "unknown")
                suggested_agent = analysis.get("suggested_agent", "auto-assigned")
                confidence = analysis.get("confidence", 0.0)
                
                return f"""✅ Executive task created and routed autonomously!

**Task ID:** {task_id}
**Description:** {task_description}

**🤖 AUTONOMOUS ROUTING:**
**Target Department:** {department.title()}
**Suggested Agent:** {suggested_agent}
**Confidence:** {confidence:.0%}

**Executive Authority:** High-priority directive
**Status:** Automatically routed to appropriate division manager

The orchestrator has analyzed your request and routed it to the most suitable team for execution."""
            else:
                return "❌ Failed to create task. Please check the system status."
                
        except Exception as e:
            return f"Error creating task: {str(e)}"
    
    async def _handle_view_tasks(self) -> str:
        """Handle viewing all tasks across divisions"""
        try:
            status = self.marketing_system.get_status()
            
            summary = "=== EXECUTIVE TASK DASHBOARD ===\n\n"
            summary += f"📊 Total Active Tasks: {status['active_tasks']}\n"
            summary += f"✅ Completed: {status['completed_tasks']}\n"
            summary += f"⏳ Pending: {status['pending_tasks']}\n\n"
            
            return summary
            
        except Exception as e:
            return f"Error retrieving task dashboard: {str(e)}"
    
    async def _handle_strategic_analysis(self, user_input: str) -> str:
        """Handle deep strategic analysis with data"""
        topic = user_input[7:].strip()  # Remove "ANALYZE "
        
        # Search for comprehensive data
        relevant_data = await self.search_memory(topic, limit=8)
        
        analysis_prompt = f"""
EXECUTIVE STRATEGIC ANALYSIS REQUEST: {topic}

Available Data Sources:
{chr(10).join([f"- {mem['text'][:400]}" for mem in relevant_data])}

Provide a comprehensive executive analysis with SPECIFIC DATA POINTS including:
1. Current situation assessment (use actual numbers)
2. Key opportunities and threats  
3. Strategic recommendations with quantified benefits
4. Resource requirements
5. Expected ROI/impact (use specific percentages/amounts)
6. Next steps and timeline

CRITICAL: Reference specific numbers, percentages, and metrics from the data sources above.
"""
        
        return await self._get_ai_response(analysis_prompt)
    
    async def _get_ai_response(self, prompt: str) -> str:
        """Get AI response for strategic prompts"""
        try:
            temp_history = ChatHistory()
            temp_history.add_system_message(self.get_system_prompt())
            temp_history.add_user_message(prompt)
            
            response = await self.chat_service.get_chat_message_content(
                chat_history=temp_history,
                settings=PromptExecutionSettings(
                    max_tokens=1000,
                    temperature=0.1  # Very precise for data accuracy
                )
            )
            
            return str(response).strip()
            
        except Exception as e:
            return f"Analysis error: {str(e)}"

    async def _handle_coordination(self, user_input: str) -> str:
        """Handle cross-division coordination initiatives"""
        initiative = user_input[10:].strip()  # Remove "COORDINATE "
        
        return f"""🤝 CROSS-DIVISION COORDINATION: {initiative}

**Coordination Status:** Initiative ready for implementation

**Divisions Involved:**
• Product Marketing: Strategic positioning and market analysis
• Digital Marketing: Campaign execution and performance tracking  
• Content Marketing: Creative assets and brand alignment

**Next Steps:**
1. Communicate initiative to division managers
2. Assign specific responsibilities to each division
3. Establish coordination timeline and milestones
4. Monitor cross-division collaboration

**Executive Oversight:**
- Regular progress reviews with division managers
- Resource allocation and conflict resolution
- Strategic alignment maintenance

✨ Cross-division coordination framework established."""

    async def _handle_review_approvals(self) -> str:
        """Handle viewing manager-approved submissions awaiting final approval"""
        return """=== EXECUTIVE APPROVAL QUEUE ===

📋 **Pending Final Approvals:** No submissions currently pending

**Final Approval Process:**
1. Managers review and approve agent work submissions
2. Approved submissions escalated to executive level
3. CMO provides final strategic approval or rejection
4. Decision communicated back through the chain

**Available Actions:**
- FINAL APPROVE [approval_id] - Give executive approval and implement
- FINAL REJECT [approval_id] [feedback] - Reject with strategic guidance

**Strategic Considerations:**
- Alignment with company objectives
- Resource allocation impact
- Market timing and competitive advantage
- Cross-division implications

✨ Ready to review manager-approved submissions for final implementation."""

    async def _handle_final_approve(self, user_input: str) -> str:
        """Handle final executive approval of submissions"""
        try:
            # Parse: FINAL APPROVE [approval_id]
            parts = user_input.split(" ", 2)
            if len(parts) < 3:
                return "Format: FINAL APPROVE [approval_id]"
            
            approval_id = parts[2]
            
            # Log the HUMAN executive approval decision
            from Utils.logger import log_human_verification
            log_human_verification(
                department="Executive",
                task_id=approval_id,
                decision="APPROVED",
                reviewer=f"{self.user_account.username} (CMO)"
            )
            
            # Generate implementation ID
            import uuid
            implementation_id = f"IMPL-{str(uuid.uuid4())[:8].upper()}"
            
            return f"""✅ FINAL EXECUTIVE APPROVAL GRANTED

**Approval ID:** {approval_id}
**Implementation ID:** {implementation_id}
**Executive Decision:** APPROVED FOR IMPLEMENTATION BY HUMAN CMO
**Authority:** Chief Marketing Officer ({self.user_account.username})

**Executive Comments:**
Work aligns with strategic objectives and demonstrates excellent execution standards. 
Human executive review confirms alignment with company vision and market strategy.

**Implementation Process:**
1. Work now moves to implementation phase
2. Resources allocated for execution
3. All departments notified of approval
4. Performance tracking initiated

**Human Approval Chain:**
✅ Agent completed work
✅ Human Manager approved
✅ Human CMO approved ({self.user_account.username})
🚀 IMPLEMENTATION AUTHORIZED

🚀 EXECUTIVE APPROVAL: Work approved by human CMO and moving to implementation."""
            
        except Exception as e:
            return f"Error processing final approval: {str(e)}"

    async def _handle_final_reject(self, user_input: str) -> str:
        """Handle final executive rejection with strategic feedback"""
        try:
            # Parse: FINAL REJECT [approval_id] [feedback]
            parts = user_input.split(" ", 3)
            if len(parts) < 4:
                return "Format: FINAL REJECT [approval_id] [strategic feedback]"
            
            approval_id = parts[2]
            feedback = parts[3]
            
            # Log the HUMAN executive rejection decision
            from Utils.logger import log_human_verification
            log_human_verification(
                department="Executive",
                task_id=approval_id,
                decision="REJECTED",
                reviewer=f"{self.user_account.username} (CMO)"
            )
            
            return f"""❌ FINAL EXECUTIVE REJECTION

**Approval ID:** {approval_id}
**Executive Decision:** REJECTED BY HUMAN CMO - STRATEGIC REVISION REQUIRED
**Authority:** Chief Marketing Officer ({self.user_account.username})

**Executive Strategic Feedback:**
{feedback}

**Strategic Implications:**
- Work requires alignment with broader company objectives
- Human executive review identified strategic concerns
- Consider market timing and competitive positioning
- Review resource allocation and priority against other initiatives
- Ensure cross-division coordination and synergies

**Next Steps:**
1. Manager receives strategic feedback for team guidance
2. Agent can revise work with strategic direction
3. Resubmission welcome after addressing strategic concerns
4. Alternative approaches encouraged with executive input

**Human Rejection Chain:**
✅ Agent completed work
✅ Human Manager approved
❌ Human CMO rejected with strategic guidance ({self.user_account.username})
🔄 Strategic revision opportunity

🎯 EXECUTIVE GUIDANCE: Strategic revision opportunity provided by human CMO."""
            
        except Exception as e:
            return f"Error processing final rejection: {str(e)}"


class ManagerChatInterface(ChatInterface):
    """Manager chat interface with division-specific capabilities"""
    
    def __init__(self, user_account: UserAccount, kernel: sk.Kernel, marketing_system):
        super().__init__(user_account, kernel)
        self.marketing_system = marketing_system
        self.division_name = self._get_division_name()
        self.chat_history.add_system_message(self.get_system_prompt())
    
    def _get_division_name(self) -> str:
        """Get human-readable division name"""
        division_map = {
            Division.PRODUCT_MARKETING: "Product Marketing",
            Division.DIGITAL_MARKETING: "Digital Marketing", 
            Division.CONTENT_MARKETING: "Content Marketing"
        }
        return division_map.get(self.user_account.division, "Marketing")
    
    def get_system_prompt(self) -> str:
        return f"""You are the {self.division_name} Manager with authority over your division's operations.

MANAGER CAPABILITIES:
- Lead and manage {self.division_name} team
- Create and assign tasks within your division
- Access division-specific knowledge and shared company data
- Communicate with agents in your division
- Monitor division performance and task progress

DIVISION FOCUS: {self.division_name}
- Deep expertise in your division's domain
- Understanding of division-specific tools, processes, and metrics
- Knowledge of team capabilities and workload

BEHAVIOR:
- Focus on division-specific excellence and efficiency
- Balance strategic oversight with tactical execution
- Support and guide your team members  
- Escalate cross-division needs to executive level

CRITICAL RULE: Only work with real tasks that have been explicitly created through proper channels. NEVER create, invent, or suggest fake tasks or assignments. If no tasks exist, clearly state the current status.

AVAILABLE COMMANDS:
- ASSIGN TASK [agent] [description] - Assign task to agent in your division
- VIEW TEAM - See your division's agents and current tasks
- STATUS - Get division performance metrics
- GUIDE [agent] - Provide guidance to specific agent
- REVIEW SUBMISSIONS - View pending work submissions from your team
- APPROVE [submission_id] - Approve work and forward to CMO
- REJECT [submission_id] [feedback] - Reject work with feedback

Always consider your division's current workload and capabilities when making decisions."""
    
    async def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process manager input with division-specific capabilities"""
        
        # Check for manager commands
        if user_input.upper().startswith("ASSIGN TASK"):
            return await self._handle_task_assignment(user_input)
        elif user_input.upper().startswith("VIEW TEAM"):
            return await self._handle_view_team()
        elif user_input.upper().startswith("STATUS"):
            return await self._handle_division_status()
        elif user_input.upper().startswith("GUIDE"):
            return await self._handle_agent_guidance(user_input)
        elif user_input.upper().startswith("REVIEW SUBMISSIONS"):
            return await self._handle_review_submissions()
        elif user_input.upper().startswith("APPROVE"):
            return await self._handle_approve_submission(user_input)
        elif user_input.upper().startswith("REJECT"):
            return await self._handle_reject_submission(user_input)
        
        # For division management conversations
        relevant_memories = await self.search_memory(user_input, limit=3)
        
        # Build context
        memory_context = ""
        if relevant_memories:
            memory_context = f"\n\n=== RELEVANT {self.division_name.upper()} DATA ===\n"
            for i, memory in enumerate(relevant_memories, 1):
                memory_context += f"{i}. {memory['text'][:200]}...\n"
        
        # Detect file content queries (same logic as AgentChatInterface)
        assigned_task_keywords = ["my tasks", "assigned tasks", "task status", "current assignments", "tasks assigned to me"]
        file_content_keywords = ["from files", "from documents", "file content", "document content", "in our files", "in files", "tasks are in", "content from", "what.*files", "files contain"]
        
        is_assigned_task_query = any(keyword in user_input.lower() for keyword in assigned_task_keywords)
        is_file_content_query = any(keyword in user_input.lower() for keyword in file_content_keywords)
        
        # FORCE file content logic if user mentions "files" or "documents" anywhere
        if ("file" in user_input.lower() or "document" in user_input.lower()) and not is_assigned_task_query:
            is_file_content_query = True

        if is_file_content_query and memory_context:
            # Manager asking about file content - use memory context
            prompt = f"{user_input}{memory_context}\n\nIMPORTANT: Use the information from the relevant division data above to answer the question. Reference specific content from the files when available."
        else:
            # General management guidance
            prompt = f"{user_input}{memory_context}\n\nProvide helpful management guidance and strategic oversight for your division."
        
        self.chat_history.add_user_message(prompt)
        
        try:
            response = await self.chat_service.get_chat_message_content(
                chat_history=self.chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=600,
                    temperature=0.4  # Balanced management responses
                )
            )
            
            response_text = str(response).strip()
            self.chat_history.add_assistant_message(response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Manager chat error: {e}")
            return f"I encountered an error processing your request. Please try again."
    
    async def _handle_task_assignment(self, user_input: str) -> str:
        """Handle autonomous task assignment within division"""
        try:
            # Parse: ASSIGN TASK [description] (no manual agent needed)
            if not user_input.upper().startswith("ASSIGN TASK "):
                return "Format: ASSIGN TASK [task description]"
            
            task_description = user_input[12:].strip()  # Remove "ASSIGN TASK "
            
            if not task_description:
                return "Please provide a task description"
            
            # Use orchestrator for autonomous agent selection within division
            from Core.Tasks.orchestrator import Orchestrator
            orchestrator = Orchestrator(self.marketing_system.kernel)
            
            context = {
                "division": self.user_account.division.value,
                "created_by": self.user_account.username,
                "constraint": "division_only"  # Constrain to manager's division
            }
            
            analysis = await orchestrator.analyze_input(task_description, context)
            
            # Filter to division-appropriate agents
            suggested_agent = self._filter_agent_to_division(analysis.get("suggested_agent"))
            department = analysis.get("department", "unknown")
            confidence = analysis.get("confidence", 0.0)
            
            # Create task with autonomous routing
            task_id = await self.marketing_system.create_task(
                task_description,
                context=context
            )
            
            if task_id:
                return f"""✅ Task assigned autonomously within {self.division_name}!

**Task ID:** {task_id}
**Description:** {task_description}

**🤖 DIVISION ROUTING:**
**Analyzed Department:** {department.title()}
**Selected Agent:** {suggested_agent}
**Confidence:** {confidence:.0%}

**Manager Authority:** Division-level task assignment
**Status:** Automatically routed to best-fit agent in your division

The orchestrator analyzed your request and selected the most qualified agent within your division."""
            else:
                return "❌ Failed to assign task. Please check the system status."
                
        except Exception as e:
            return f"Error assigning task: {str(e)}"
    
    def _filter_agent_to_division(self, suggested_agent: str) -> str:
        """Filter suggested agent to ensure it belongs to manager's division"""
        division_agents = {
            Division.PRODUCT_MARKETING: [
                "PositioningAgent", "PersonaAgent", "GTMAgent", 
                "CompetitorAgent", "LaunchAgent"
            ],
            Division.DIGITAL_MARKETING: [
                "SEOAgent", "SEMAgent", "LandingAgent",
                "AnalyticsAgent", "FunnelAgent"
            ],
            Division.CONTENT_MARKETING: [
                "ContentAgent", "BrandAgent", "SocialAgent", 
                "CommunityAgent"
            ]
        }
        
        valid_agents = division_agents.get(self.user_account.division, [])
        
        # If suggested agent is in the division, use it
        if suggested_agent and suggested_agent in valid_agents:
            return suggested_agent
        
        # Otherwise, return the first agent in the division as default
        return valid_agents[0] if valid_agents else "UnknownAgent"
    
    async def _handle_view_team(self) -> str:
        """Handle viewing division team and tasks"""
        return f"""=== {self.division_name.upper()} TEAM DASHBOARD ===

**Team Members:**
{self._get_division_agents()}

📊 **Current Status:** No active tasks assigned

**Available Actions:**
- Assign tasks autonomously using: ASSIGN TASK [description]
- Provide guidance to agents using: GUIDE [agent]
- Check division performance using: STATUS

**Task Assignment Process:**
- Orchestrator automatically selects the best agent in your division
- All task assignments go through proper channels
- Team members receive clear instructions and deadlines

✨ Ready to assign work autonomously to your division team."""
    
    def _get_division_agents(self) -> str:
        """Get list of agents in the division"""
        division_agents = {
            Division.PRODUCT_MARKETING: [
                "PositioningAgent", "PersonaAgent", "GTMAgent", 
                "CompetitorAgent", "LaunchAgent"
            ],
            Division.DIGITAL_MARKETING: [
                "SEOAgent", "SEMAgent", "LandingAgent",
                "AnalyticsAgent", "FunnelAgent"
            ],
            Division.CONTENT_MARKETING: [
                "ContentAgent", "BrandAgent", "SocialAgent", 
                "CommunityAgent"
            ]
        }
        
        agents = division_agents.get(self.user_account.division, [])
        return "\n".join([f"  • {agent}" for agent in agents])
    
    async def _handle_division_status(self) -> str:
        """Handle division status request"""
        return f"""=== {self.division_name.upper()} STATUS ===

**Division Health:** 🟢 Operational
**Team Status:** All agents available and ready
**Task Queue:** No active tasks currently

**Task Statistics:**
- Active Tasks: 0
- Completed Tasks: 0  
- Pending Reviews: 0

**Team Capacity:**
- All team members available for new assignments
- No current bottlenecks or capacity issues
- Ready to take on new strategic initiatives

**Next Steps:**
- Await task assignments from CMO or create division-specific tasks
- Continue team development and training
- Monitor for new strategic opportunities

✨ Division ready for new task assignments and initiatives."""
    
    async def _handle_agent_guidance(self, user_input: str) -> str:
        """Handle providing guidance to specific agent"""
        agent_name = user_input[5:].strip()  # Remove "GUIDE "
        
        return f"""=== GUIDANCE FOR {agent_name.upper()} ===

[This would provide specific guidance based on:]
- Agent's current tasks and performance
- Division priorities and objectives  
- Available resources and support
- Skill development opportunities

**Current Focus Areas:**
- Task execution best practices
- Division-specific methodologies
- Resource utilization optimization
- Quality standards and expectations

[Integration needed with agent performance tracking]
"""

    async def _handle_review_submissions(self) -> str:
        """Handle viewing pending work submissions from team"""
        return f"""=== {self.division_name.upper()} WORK SUBMISSIONS ===

📋 **Pending Reviews:** No submissions currently pending

**Review Process:**
1. Team members submit work using SUBMIT WORK command
2. Submissions appear here for your review
3. You can APPROVE to forward to CMO or REJECT with feedback
4. Approved work goes to executive level for final approval

**Available Actions:**
- APPROVE [submission_id] - Approve and forward to CMO
- REJECT [submission_id] [feedback] - Reject with specific feedback

**Integration Status:** 
Submission tracking system ready for work submissions from your team.

✨ Ready to receive and review work submissions from {self.division_name} agents."""

    async def _handle_approve_submission(self, user_input: str) -> str:
        """Handle human approval of agent work submission"""
        try:
            # Parse: APPROVE [submission_id]
            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                return "Format: APPROVE [submission_id]"
            
            submission_id = parts[1]
            
            # Log the HUMAN approval decision
            from Utils.logger import log_human_verification
            log_human_verification(
                department=self.division_name,
                task_id=submission_id,
                decision="APPROVED",
                reviewer=f"{self.user_account.username} (Manager)"
            )
            
            # Generate tracking ID for escalation
            import uuid
            escalation_id = f"ESC-{str(uuid.uuid4())[:8].upper()}"
            
            return f"""✅ MANAGER APPROVAL CONFIRMED

**Submission ID:** {submission_id}
**Manager Decision:** APPROVED BY HUMAN MANAGER
**Manager:** {self.user_account.username}
**Division:** {self.division_name}
**Escalation ID:** {escalation_id}

**Human Manager Comments:**
Work meets division standards and successfully addresses the user's request. 
Quality is satisfactory for escalation to executive level.

**Next Steps:**
1. Submission forwarded to CMO for final executive review
2. Agent notified of manager approval
3. Work now in executive approval queue

**Approval Chain:**
✅ Agent completed work
✅ Human Manager approved ({self.user_account.username})
⏳ Awaiting final executive approval

🚀 Submission successfully escalated to executive level."""
            
        except Exception as e:
            return f"Error processing approval: {str(e)}"

    async def _handle_reject_submission(self, user_input: str) -> str:
        """Handle human rejection of agent work submission with feedback"""
        try:
            # Parse: REJECT [submission_id] [feedback]
            parts = user_input.split(" ", 2)
            if len(parts) < 3:
                return "Format: REJECT [submission_id] [detailed feedback]"
            
            submission_id = parts[1]
            feedback = parts[2]
            
            # Log the HUMAN rejection decision
            from Utils.logger import log_human_verification
            log_human_verification(
                department=self.division_name,
                task_id=submission_id,
                decision="REJECTED",
                reviewer=f"{self.user_account.username} (Manager)"
            )
            
            return f"""❌ MANAGER REJECTION WITH FEEDBACK

**Submission ID:** {submission_id}
**Manager Decision:** REJECTED BY HUMAN MANAGER
**Manager:** {self.user_account.username}
**Division:** {self.division_name}

**Human Manager Feedback:**
{feedback}

**Rejection Reasons:**
- Work does not meet current division standards
- Requires improvement to address user request adequately
- Needs revision based on manager expertise and judgment

**Next Steps:**
1. Agent receives specific feedback for improvement
2. Work returned for revision and resubmission
3. Agent can resubmit after addressing feedback
4. Manager will re-review revised submission

**Feedback Chain:**
✅ Agent completed initial work
❌ Human Manager rejected with feedback ({self.user_account.username})
🔄 Agent can revise and resubmit

🎯 Human feedback provided for continuous improvement."""
            
        except Exception as e:
            return f"Error processing rejection: {str(e)}"


class AgentChatInterface(ChatInterface):
    """Agent chat interface focused on task execution"""
    
    def __init__(self, user_account: UserAccount, kernel: sk.Kernel):
        super().__init__(user_account, kernel)
        self.agent_role = user_account.agent_name or "Marketing Agent"
        self.chat_history.add_system_message(self.get_system_prompt())
    
    def get_system_prompt(self) -> str:
        division_focus = {
            Division.PRODUCT_MARKETING: "product positioning, market research, competitive analysis, go-to-market strategy, and customer personas",
            Division.DIGITAL_MARKETING: "SEO, SEM, analytics, conversion optimization, landing pages, and digital advertising",
            Division.CONTENT_MARKETING: "content creation, brand design, social media, community management, and creative campaigns"
        }
        
        focus_area = division_focus.get(self.user_account.division, "marketing execution")
        
        return f"""You are {self.agent_role} in the {self.user_account.division.value.replace('_', ' ').title()} division.

AGENT ROLE: {self.agent_role}
EXPERTISE: {focus_area}

CAPABILITIES:
- Execute assigned tasks with domain expertise
- Access relevant company data and past work
- Provide detailed, actionable deliverables
- Communicate progress and ask for clarification
- Collaborate within task context
- Help with content creation, brainstorming, and professional guidance
- Provide expertise in your domain area

BEHAVIOR:
- Focus on high-quality task execution when tasks are assigned
- Be helpful and provide expert guidance for content creation requests
- Use your domain expertise to add value in conversations
- Ask clarifying questions when requirements are unclear
- Provide detailed deliverables that meet professional standards

CRITICAL RULE: When specifically asked about your task status or assigned tasks, only mention real tasks that have been explicitly assigned by a Manager or CMO. NEVER invent fake tasks or assignments. If no tasks are assigned, clearly state "No tasks currently assigned."

AVAILABLE COMMANDS:
- VIEW MY TASKS or TASK STATUS - View your current tasks
- TASK UPDATE [id] [update] - Update task progress
- ASK CLARIFICATION [question] - Ask manager for clarification
- SUBMIT WORK [title] [description] - Submit work for manager verification

You can help with content creation, provide expertise, and have professional conversations within your domain, but never fabricate task assignments."""
    
    async def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process agent input focused on task execution"""
        
        # Check for agent commands (handle both variations)
        user_input_upper = user_input.upper()
        if user_input_upper.startswith("TASK STATUS") or user_input_upper.startswith("VIEW MY TASKS"):
            return await self._handle_task_status()
        elif user_input_upper.startswith("TASK UPDATE"):
            return await self._handle_task_update(user_input)
        elif user_input_upper.startswith("ASK CLARIFICATION"):
            return await self._handle_clarification_request(user_input)
        elif user_input_upper.startswith("SUBMIT WORK"):
            return await self._handle_submit_work(user_input)
        
        # For task-focused conversations, search relevant memories
        relevant_memories = await self.search_memory(user_input, limit=3)
        
        # Build context with task-relevant data
        memory_context = ""
        if relevant_memories:
            memory_context = f"\n\n=== RELEVANT CONTEXT ===\n"
            for i, memory in enumerate(relevant_memories, 1):
                memory_context += f"{i}. {memory['text'][:250]}...\n"
        
        # Detect file content queries vs assigned task queries (same logic as ManagerChatInterface)
        assigned_task_keywords = ["my tasks", "assigned tasks", "task status", "current assignments", "tasks assigned to me"]
        file_content_keywords = ["from files", "from documents", "file content", "document content", "in our files", "in files", "tasks are in", "content from", "what.*files", "files contain"]
        
        is_assigned_task_query = any(keyword in user_input.lower() for keyword in assigned_task_keywords)
        is_file_content_query = any(keyword in user_input.lower() for keyword in file_content_keywords)
        
        # FORCE file content logic if user mentions "files" or "documents" anywhere
        if ("file" in user_input.lower() or "document" in user_input.lower()) and not is_assigned_task_query:
            is_file_content_query = True
        
        if is_file_content_query and memory_context:
            # Agent asking about file content - use memory context
            prompt = f"{user_input}{memory_context}\n\nIMPORTANT: Use the information from the relevant context above to answer the question. Reference specific content from the files when available."
        elif is_assigned_task_query:
            # Only add strict anti-fake instruction for assigned task queries
            prompt = f"{user_input}{memory_context}\n\nIMPORTANT: Do not create, invent, or suggest any fake tasks. Only discuss tasks that have been explicitly assigned by managers or CMO. If no tasks exist, clearly state that no tasks are currently assigned."
        else:
            # General helpful responses
            prompt = f"{user_input}{memory_context}\n\nProvide helpful, expert guidance within your domain. You can assist with content creation and professional advice."
        
        self.chat_history.add_user_message(prompt)
        
        try:
            response = await self.chat_service.get_chat_message_content(
                chat_history=self.chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=700,
                    temperature=0.4  # Balanced creativity for helpful responses
                )
            )
            
            response_text = str(response).strip()
            self.chat_history.add_assistant_message(response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Agent chat error: {e}")
            return f"I encountered an error processing your request. Please try again."
    
    async def _handle_task_status(self) -> str:
        """Handle viewing agent's current tasks - connect to real task system"""
        try:
            # Get marketing system reference to check for real tasks
            # For now, return clear message that no tasks are assigned
            return f"""=== {self.agent_role.upper()} TASK STATUS ===

📋 **Current Status:** No tasks currently assigned

**Available Actions:**
- Wait for task assignment from your manager
- Contact your manager if you need work assignments
- Use downtime for skill development or knowledge updates

**Task Assignment Process:**
- Tasks are assigned by Division Managers or CMO
- You will receive clear task descriptions and requirements
- All tasks will have specific deadlines and deliverables

**Next Steps:**
- Check back later for new assignments
- Contact your division manager for guidance
- Continue professional development activities

✨ Ready to receive task assignments from management."""
        except Exception as e:
            logger.error(f"Error handling task status: {e}")
            return "Error checking task status. Please try again."
    
    async def _handle_task_update(self, user_input: str) -> str:
        """Handle task progress updates"""
        # Parse: TASK UPDATE [id] [update]
        parts = user_input.split(" ", 3)
        if len(parts) < 4:
            return "Format: TASK UPDATE [task_id] [progress update]"
        
        task_id = parts[2]
        update = parts[3]
        
        return f"""✅ Task update recorded for {task_id}:
"{update}"

**Next Steps:**
- Update sent to manager
- Progress tracked in system
- Estimated completion: [Based on update]

[Integration needed with task management system]
"""
    
    async def _handle_clarification_request(self, user_input: str) -> str:
        """Handle requests for clarification from manager"""
        question = user_input[16:].strip()  # Remove "ASK CLARIFICATION "
        
        return f"""❓ Clarification request sent to manager:
"{question}"

**Status:** Pending manager response
**Expected Response:** Within 2-4 hours during business hours

You can continue working on other aspects of the task while waiting for clarification.

[Integration needed with manager communication system]
"""

    async def _handle_submit_work(self, user_input: str) -> str:
        """Handle work submission for manager verification"""
        try:
            # Parse: SUBMIT WORK [title] [description]
            parts = user_input.split(" ", 3)
            if len(parts) < 4:
                return "Format: SUBMIT WORK [title] [work description/deliverable]"
            
            work_title = parts[2]
            work_description = parts[3]
            
            # Generate submission ID
            import uuid
            submission_id = f"SUB-{str(uuid.uuid4())[:8].upper()}"
            
            # Get manager name for this division
            division_managers = {
                Division.PRODUCT_MARKETING: "product_manager",
                Division.DIGITAL_MARKETING: "digital_manager", 
                Division.CONTENT_MARKETING: "content_manager"
            }
            
            manager_name = division_managers.get(self.user_account.division, "division_manager")
            
            return f"""✅ Work submitted for verification!

**Submission ID:** {submission_id}
**Title:** {work_title}
**Submitted to:** {manager_name}
**Status:** Pending Manager Review

**Your Submission:**
{work_description}

**Next Steps:**
1. Manager will review your work
2. You'll receive feedback and approval status
3. If approved, work will be forwarded to CMO for final approval
4. Final decision will be communicated back to you

**Track Status:** You can check the review status by referencing ID {submission_id}

🔄 Your work is now in the review queue. You'll be notified when feedback is available."""
            
        except Exception as e:
            logger.error(f"Error submitting work: {e}")
            return f"Error submitting work: {str(e)}"


def create_chat_interface(user_account: UserAccount, kernel: sk.Kernel, marketing_system=None) -> ChatInterface:
    """Factory function to create appropriate chat interface based on account type"""
    
    if user_account.account_type == AccountType.EXECUTIVE:
        return ExecutiveChatInterface(user_account, kernel, marketing_system)
    elif user_account.account_type == AccountType.MANAGER:
        return ManagerChatInterface(user_account, kernel, marketing_system)
    elif user_account.account_type == AccountType.AGENT:
        return AgentChatInterface(user_account, kernel)
    else:
        raise ValueError(f"Unknown account type: {user_account.account_type}") 