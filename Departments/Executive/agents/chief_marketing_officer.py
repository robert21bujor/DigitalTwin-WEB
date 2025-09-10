"""
Executive Agent (CMO) with global memory access and strategic capabilities
"""

from datetime import datetime
from typing import Dict, Any, List
import logging

import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
from Core.Agents.agent import Agent, AgentType
from Core.Tasks.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class ExecutiveAgent(Agent):
    """
    Executive Agent (CMO) with global access to all marketing data and strategic capabilities
    """
    
    def __init__(self, kernel: sk.Kernel):
        super().__init__(
            name="ExecutiveAgent",
            role="Chief Marketing Officer",
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel,
            skills=["Strategic Planning", "Financial Analysis", "Cross-division Coordination", "Executive Decision Making", "Task Review & Approval"]
        )
        
        # Executive-specific attributes
        self.executive_level = True
        self.cross_division_access = True
        self.department = "Executive"
        
        # Performance tracking
        self.tasks_reviewed = 0
        self.tasks_approved = 0
        self.created_at = datetime.now()
        
        logger.info(f"Executive Agent initialized with global memory access")
    
    def _get_memory_collection_name(self) -> str:
        """Override to ensure Executive Agent uses executive shared memory collection"""
        return "executive-shared-memory"
    
    def get_system_prompt(self) -> str:
        """Get executive-specific system prompt with emphasis on data accuracy"""
        # Get the base agent prompt with email awareness and all core capabilities
        base_prompt = super().get_default_system_prompt()
        
        executive_additions = f"""You are the Chief Marketing Officer (CMO) with executive authority over all marketing operations.

EXECUTIVE ROLE: {self.role}
DEPARTMENT: {self.department}  
AGENT: {self.name}

EXECUTIVE CAPABILITIES:
- Global oversight across all marketing divisions (Product, Digital, Content)
- Strategic planning and cross-division coordination
- Access to ALL company data including earnings reports, financial data, and competitive intelligence
- Authority to create high-priority directives for any division
- Real-time access to comprehensive business metrics and performance data

CRITICAL DIRECTIVE FOR FINANCIAL DATA:
- When discussing earnings, revenue, growth rates, or any financial metrics: ALWAYS use specific numbers from your memory
- NEVER use placeholders like "X%", "significant growth", or "strong performance"
- Reference actual dollar amounts, percentages, and specific figures
- If you have access to quarterly results, annual reports, or financial data, cite the exact numbers

BEHAVIOR:
- Think strategically at the executive level
- Provide data-driven analysis with SPECIFIC NUMBERS and METRICS
- Make decisions that impact the entire marketing organization
- Focus on business impact, ROI, and competitive advantage
- Be decisive and action-oriented
- Coordinate initiatives across multiple divisions when appropriate

TASK EXECUTION:
- Analyze requests from a strategic perspective
- Use all available company data to inform recommendations
- Provide comprehensive, executive-level deliverables
- Consider cross-division implications and opportunities
- Focus on scalable, high-impact solutions

MEMORY ACCESS: You have access to global shared memory containing:
- Financial reports and earnings data
- Competitive intelligence 
- Market research and analysis
- Cross-division performance metrics
- Strategic documents and executive briefings

🔍 **ENHANCED SEMANTIC SEARCH & FILE ACCESS:**
You have AI-powered semantic search capabilities for our company's Google Drive. The system understands natural language and finds relevant documents intelligently.

**🧠 SEMANTIC SEARCH FUNCTIONS:**
- search_files(query, folder, file_type): **NOW WITH AI UNDERSTANDING** - Use natural language!
- search_by_folder("Executive"): Access executive-level documents and reports  
- list_folders(): Show all available document categories

**FOR RECENT/LATEST QUERIES:** Always use search_files() with time-based terms like "recent", "latest", "new"

**Key Executive Folders:**
- Executive: Board reports, strategic plans, financial documents, earnings releases
- Marketing: Campaign reports, performance data, strategy documents
- Product Marketing: Product plans, launch materials, market research
- Digital Marketing: Analytics reports, campaign data, performance metrics

**🚀 ENHANCED SEARCH CAPABILITIES:**

**NATURAL LANGUAGE QUERIES (Recommended):**
- "Show me files about Amazon" → search_files("Amazon files and documents")
- "Find Q1 earnings report" → search_files("Q1 earnings financial report")
- "Latest marketing campaign data" → search_files("latest marketing campaign performance")
- "Client meeting notes from this month" → search_files("recent client meeting notes")

**INTELLIGENT FEATURES:**
✅ **Semantic Understanding**: Understands intent behind requests
✅ **Relevance Ranking**: Results ranked by actual relevance with scores
✅ **Smart Filtering**: Reduces false positives from keyword matching
✅ **Multilingual**: Supports English and Romanian queries
✅ **Context Aware**: Understands business terminology and relationships

**EXAMPLE ENHANCED RESPONSES:**
User: "Show me files about Amazon"
YOU: *Call search_files("Amazon related files and documents")*
Result: Semantically ranked list with relevance scores and match explanations

User: "What's our latest financial performance?"
YOU: *Call search_files("latest financial performance earnings")*
Result: Most relevant financial documents ranked by recency and relevance

**SEARCH STRATEGY:**
1. **Use conversational language** in search queries for better results
2. **Include context terms** like "latest", "recent", "performance", "analysis"
3. **Let the AI understand intent** - don't overthink keyword selection
4. **Review relevance scores** provided in results to identify best matches

**🚨 CRITICAL: ALWAYS SEARCH WHEN USERS ASK ABOUT FILES OR EMAILS**

When users ask about:
- **"emails from [person]"** → IMMEDIATELY call search_files("emails from [person]")
- **"my emails"** → IMMEDIATELY call search_files("my emails")
- **"recent emails"** → IMMEDIATELY call search_files("recent emails")
- **"show me emails"** → IMMEDIATELY call search_files("emails")
- **"find files about [topic]"** → IMMEDIATELY call search_files("[topic]")

**NEVER say "I don't have access" - ALWAYS try search_files() first!**

The unified semantic system finds both files AND emails automatically!

Always leverage this comprehensive data access to provide informed, strategic responses with specific metrics and figures."""
        
        # Combine base capabilities with executive-specific instructions
        return base_prompt + "\n\n" + executive_additions
    
    async def perform_work(self, task: Task) -> str:
        """Executive task execution with enhanced data access and strategic focus"""
        logger.info(f"Executive Agent executing strategic task: {task.title}")
        
        try:
            # Get comprehensive memory context - more extensive for executive level
            memory_context = await self.memory_manager.get_relevant_context(
                current_task=f"{task.title} {task.description}",
                max_memories=8  # Executive needs more comprehensive context
            )
            
            # Create executive-level task prompt with data emphasis
            user_prompt = self.create_executive_task_prompt(task, memory_context)
            
            # Execute with strategic focus
            result = await self._execute_with_ai(user_prompt, executive_mode=True)
            
            # Store executive task result
            await self.memory_manager.add_task_memory(
                task_id=task.id,
                task_description=f"[EXECUTIVE] {task.description}",
                result=result,
                success=True
            )
            
            logger.info(f"Executive task {task.id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Executive Agent error on task {task.id}: {str(e)}")
            
            # Store failure in memory for learning
            await self.memory_manager.add_task_memory(
                task_id=task.id,
                task_description=f"[EXECUTIVE] {task.description}",
                result=f"Task failed: {str(e)}",
                success=False
            )
            
            return f"I apologize, but I encountered an error while executing this executive task: {str(e)}. Please try rephrasing your request or contact system support."
    
    def create_executive_task_prompt(self, task: Task, memory_context: str) -> str:
        """Create executive-level task prompt with enhanced data focus"""
        
        base_prompt = f"""
EXECUTIVE TASK ASSIGNMENT

Task: {task.title}
Request: {task.description}
Priority: {task.priority.value.upper()}

AVAILABLE COMPANY DATA:
{memory_context}

EXECUTIVE DIRECTIVE:
Execute this task with strategic perspective and comprehensive analysis. 

CRITICAL REQUIREMENTS:
1. Use SPECIFIC NUMBERS, PERCENTAGES, and METRICS from the company data above
2. NEVER use placeholders like "X%" or "significant growth" - use actual figures
3. Provide executive-level strategic insights and recommendations
4. Consider cross-division implications and opportunities
5. Focus on business impact, ROI, and competitive advantage
6. Be decisive and action-oriented

If the request involves financial data, earnings, or performance metrics:
- Reference exact dollar amounts and percentages from the data
- Cite specific quarters, time periods, and growth rates
- Compare against previous periods with actual numbers
- Provide strategic context for the financial performance

Deliver a comprehensive, professional response that demonstrates executive-level strategic thinking and data mastery.
"""
        
        return base_prompt
    
    async def _execute_with_ai(self, prompt: str, executive_mode: bool = False) -> str:
        """Execute task with AI service, optimized for executive accuracy"""
        
        if not self.chat_service:
            return "I apologize, but I cannot access the AI service to complete this task."
        
        try:
            # Create chat history with executive system prompt
            chat_history = ChatHistory()
            chat_history.add_system_message(self.get_system_prompt())
            chat_history.add_user_message(prompt)
            
            # Executive mode uses very low temperature for accuracy
            temperature = 0.05 if executive_mode else 0.3
            
            response = await self.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=1200,  # More tokens for comprehensive executive responses
                    temperature=temperature
                )
            )
            
            return str(response).strip()
            
        except Exception as e:
            logger.error(f"Executive AI execution error: {str(e)}")
            raise e
    
    def get_executive_capabilities(self) -> Dict[str, Any]:
        """Get executive-specific capabilities and permissions"""
        return {
            "global_access": True,
            "cross_division_authority": True,
            "strategic_planning": True,
            "financial_data_access": True,
            "high_priority_task_creation": True,
            "executive_decision_making": True,
            "memory_collections": ["global-shared-memory"],
            "accessible_divisions": ["Product Marketing", "Digital Marketing", "Content Marketing"],
            "data_sources": [
                "Earnings reports",
                "Financial statements", 
                "Competitive intelligence",
                "Market research",
                "Performance metrics",
                "Strategic documents"
            ]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced dictionary representation for executive agent"""
        base_dict = super().to_dict()
        base_dict.update({
            "executive_level": self.executive_level,
            "cross_division_access": self.cross_division_access,
            "capabilities": self.get_executive_capabilities(),
            "memory_access": "global-shared-memory"
        })
        return base_dict 

    async def final_review(self, task: Task) -> bool:
        """AI-based executive review and approval of completed tasks - NOT human verification"""
        logger.info(f"CMO conducting AI-based executive review of task: {task.title}")
        
        # Ensure task has required attributes
        if not hasattr(task, 'approval_reason'):
            task.approval_reason = "No manager approval reason found"
        
        try:
            # Use AI to conduct strategic executive review
            executive_review_prompt = f"""
EXECUTIVE STRATEGIC REVIEW

Task Title: {task.title}
Original Request: {task.description}
Agent Solution: {task.output}
Manager Approval Reason: {task.approval_reason}

As Chief Marketing Officer, conduct a strategic executive review focusing on:

STRATEGIC EVALUATION CRITERIA:
1. STRATEGIC ALIGNMENT: Does this align with our overall marketing strategy?
2. BRAND CONSISTENCY: Is this consistent with our brand voice and positioning?
3. RESOURCE OPTIMIZATION: Is this the best use of our marketing resources?
4. MARKET IMPACT: Will this positively impact our market position?
5. RISK ASSESSMENT: Are there any strategic risks or concerns?
6. COMPETITIVE ADVANTAGE: Does this strengthen our competitive position?

IMPORTANT: This is an AI-based executive screening. Human executive verification will occur separately through the chat interface.

RESPONSE FORMAT:
- If the work meets executive standards and strategic objectives, respond with "EXECUTIVE APPROVE" followed by your strategic reasoning.
- If the work has strategic concerns or doesn't meet executive standards, respond with "EXECUTIVE REJECT" followed by your strategic concerns and recommended improvements.

Focus on strategic and executive-level considerations, not just tactical execution.
"""
            
            chat_history = ChatHistory()
            chat_history.add_system_message("You are an AI conducting executive-level strategic review as Chief Marketing Officer. Focus on strategic alignment, brand consistency, and market impact. Human executive verification will occur separately.")
            chat_history.add_user_message(executive_review_prompt)
            
            response = await self.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=600,
                    temperature=0.2  # Lower temperature for executive decisions
                )
            )
            
            review_result = str(response).strip()
            
            # Parse executive decision
            cleaned_result = review_result.replace("*", "").replace("#", "").strip()
            approved = "EXECUTIVE APPROVE" in cleaned_result.upper()
            
            # Extract decision reasoning
            decision_reason = self._extract_executive_decision_reason(cleaned_result, approved)
            
            # Update performance tracking
            self.tasks_reviewed += 1
            
            if approved:
                self.tasks_approved += 1
                task.update_status(TaskStatus.COMPLETED, self.name, f"AI executive screening approved: {decision_reason}")
                logger.info(f"CMO AI screening approved task {task.id}: {decision_reason}")
                
                # Log the AI-based executive approval
                from Utils.logger import log_manager_review
                log_manager_review(
                    department="Executive",
                    manager_name=self.name,
                    task_id=task.id,
                    decision="AI_EXECUTIVE_APPROVED",
                    reason=f"AI executive screening passed: {decision_reason}"
                )
                
                return True
            else:
                task.rejection_reason = decision_reason
                task.update_status(TaskStatus.UNDER_REVIEW, self.name, f"AI executive feedback: {decision_reason}")
                logger.info(f"CMO AI screening rejected task {task.id}: {decision_reason}")
                
                # Log the AI-based executive rejection
                from Utils.logger import log_manager_review
                log_manager_review(
                    department="Executive",
                    manager_name=self.name,
                    task_id=task.id,
                    decision="AI_EXECUTIVE_REJECTED",
                    reason=f"AI executive screening failed: {decision_reason}"
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error in CMO AI review of task {task.id}: {str(e)}")
            task.update_status(TaskStatus.REJECTED, self.name, f"AI executive review error: {str(e)}")
            
            # Log the technical error
            from Utils.logger import log_manager_review
            log_manager_review(
                department="Executive",
                manager_name=self.name,
                task_id=task.id,
                decision="AI_EXECUTIVE_ERROR",
                reason=f"Technical error during AI executive review: {str(e)}"
            )
            
            return False

    def _extract_executive_decision_reason(self, cleaned_result: str, approved: bool) -> str:
        """Extract CMO decision reason from AI response for both approval and rejection"""
        try:
            if approved:
                # Look for "EXECUTIVE APPROVE" followed by explanation
                if "EXECUTIVE APPROVE" in cleaned_result.upper():
                    # Split by "EXECUTIVE APPROVE" and take everything after it
                    parts = cleaned_result.upper().split("EXECUTIVE APPROVE", 1)
                    if len(parts) > 1:
                        reason = parts[1].strip()
                        # Remove common prefixes like "D", ":", "-", etc.
                        reason = reason.lstrip("D").lstrip(":").lstrip("-").lstrip(".").strip()
                        if reason:
                            return reason
                
                # If EXECUTIVE APPROVE pattern not found, return the cleaned response as the reason
                return cleaned_result.strip()
            else:
                # Look for "EXECUTIVE REJECT" followed by explanation
                if "EXECUTIVE REJECT" in cleaned_result.upper():
                    # Split by "EXECUTIVE REJECT" and take everything after it
                    parts = cleaned_result.upper().split("EXECUTIVE REJECT", 1)
                    if len(parts) > 1:
                        reason = parts[1].strip()
                        # Remove common prefixes like "ED", ":", "-", etc.
                        reason = reason.lstrip("ED").lstrip(":").lstrip("-").lstrip(".").strip()
                        if reason:
                            return reason
                
                # If EXECUTIVE REJECT pattern not found, return the cleaned response as the reason
                return cleaned_result.strip()
        except Exception:
            return "Unable to extract CMO decision reason from review"

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive CMO performance metrics"""
        approval_rate = (self.tasks_approved / self.tasks_reviewed * 100) if self.tasks_reviewed > 0 else 0
        
        return {
            "name": self.name,
            "role": self.role,
            "tasks_reviewed": self.tasks_reviewed,
            "tasks_approved": self.tasks_approved,
            "approval_rate": approval_rate,
            "uptime": self.get_uptime(),
            "executive_capabilities": self.get_executive_capabilities()
        }

    def get_uptime(self) -> str:
        """Get executive agent uptime"""
        uptime_delta = datetime.now() - self.created_at
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m" 