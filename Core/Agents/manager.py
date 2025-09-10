"""
Manager class for overseeing agent teams with Azure OpenAI integration
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
try:
    from Core.Agents.agent import Agent
    from Core.Tasks.task import Task, TaskStatus
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Core.Agents.agent import Agent
    from Core.Tasks.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class Manager:
    """
    Manager class for overseeing agent teams with Azure OpenAI integration
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        kernel: sk.Kernel,
        team_members: List[Agent] = None
    ):
        self.name = name
        self.role = role
        self.kernel = kernel
        self.team_members = team_members or []
        self.tasks_assigned = 0
        self.tasks_completed = 0
        self.created_at = datetime.now()
        
        # Initialize memory manager (will be set by the system)
        self.memory_manager = None  # type: Optional[Any]
        
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
    
    async def assign_task(self, task: Task, preferred_agent: str = None) -> bool:
        """Assign task to appropriate team member"""
        logger.info(f"{self.name} assigning task: {task.title}")
        
        try:
            # Find the best agent for the task
            agent = await self.select_agent(task, preferred_agent)
            
            if not agent:
                logger.error(f"No suitable agent found for task: {task.title}")
                return False
            
            # Assign the task
            task.assignee = agent.name
            task.assigned_agent = agent
            task.assigned_manager = self
            
            self.tasks_assigned += 1
            
            logger.info(f"Task {task.id} assigned to {agent.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {task.id}: {str(e)}")
            return False
    
    async def select_agent(self, task: Task, preferred_agent: str = None) -> Optional[Agent]:
        """Select the best agent for a task using AI analysis"""
        
        # If preferred agent is specified, try to use them
        if preferred_agent:
            for agent in self.team_members:
                if agent.name == preferred_agent:
                    return agent
        
        if not self.team_members:
            return None
        
        # Use AI to select the best agent
        try:
            agent_descriptions = []
            for agent in self.team_members:
                agent_descriptions.append(f"- {agent.name}: {agent.role} (Skills: {', '.join(agent.skills)})")
            
            prompt = f"""
Task: {task.title}
Description: {task.description}

Available agents:
{chr(10).join(agent_descriptions)}

Based on the task requirements and agent skills, which agent would be best suited for this task? 
Respond with only the agent name (e.g., "PositioningAgent").
"""
            
            chat_history = ChatHistory()
            chat_history.add_system_message("You are a team manager selecting the best agent for a task based on skills and requirements.")
            chat_history.add_user_message(prompt)
            
            response = await self.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=50,
                    temperature=0.3
                )
            )
            
            selected_name = str(response).strip()
            
            # Find the agent by name
            for agent in self.team_members:
                if agent.name == selected_name:
                    return agent
            
            # Fallback to first agent if AI selection fails
            return self.team_members[0]
            
        except Exception as e:
            logger.error(f"Error in AI agent selection: {str(e)}")
            # Fallback to first available agent
            return self.team_members[0] if self.team_members else None
    
    def _ensure_task_attributes(self, task: Task):
        """Ensure task has all required attributes for revision tracking"""
        if not hasattr(task, 'revision_count'):
            task.revision_count = 0
        if not hasattr(task, 'rejection_reason'):
            task.rejection_reason = ""

    async def review_task(self, task: Task) -> bool:
        """AI-based initial review of completed task - NOT human verification"""
        logger.info(f"{self.name} conducting AI review of task: {task.title}")
        
        # Ensure task has all required attributes
        self._ensure_task_attributes(task)
        
        try:
            # Use AI to review if the agent's solution matches what the user requested
            review_prompt = f"""
Original User Request: {task.description}
Agent's Solution: {task.output}
Agent: {task.assigned_agent.name if task.assigned_agent else 'Unknown'}

As a {self.role}, you need to determine if the agent's solution actually addresses what the user requested.

IMPORTANT: This is an AI-based initial screening. Human verification will occur separately through the chat interface.

EVALUATION CRITERIA:
1. RELEVANCE: Does the solution directly address the user's specific request?
2. COMPLETENESS: Does it cover all aspects mentioned in the user request?
3. ACCURACY: Is the information provided correct and useful?
4. ACTIONABILITY: Can the user actually use this solution for their needs?

IMPORTANT: Focus on whether the solution MATCHES the user's REQUEST, not just general quality.

RESPONSE FORMAT:
- If the solution adequately addresses the user request, respond with "APPROVE" followed by your detailed reasoning explaining WHY you approve it.
- If the solution does not match the user request or has significant gaps, respond with "REJECT" followed by your detailed reasoning explaining WHY you reject it and what needs to be corrected.

Always provide explicit reasoning for your decision.
"""
            
            chat_history = ChatHistory()
            chat_history.add_system_message(f"You are conducting an AI-based initial review as a {self.role}. Check if your team member's work addresses what the user requested. Human verification will occur separately. Always provide explicit reasoning for your decision.")
            chat_history.add_user_message(review_prompt)
            
            response = await self.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=500,
                    temperature=0.3
                )
            )
            
            review_result = str(response).strip()
            
            # Clean the response and check for approval - handle markdown and other formatting
            cleaned_result = review_result.replace("*", "").replace("#", "").strip()
            approved = cleaned_result.upper().startswith("APPROVE")
            
            # Extract reasoning for both approval and rejection
            decision_reason = self._extract_decision_reason(cleaned_result, approved)
            
            if approved:
                # Store approval reason in task context for future reference
                if not hasattr(task, 'approval_reason'):
                    task.approval_reason = decision_reason
                else:
                    task.approval_reason = decision_reason
                    
                task.update_status(TaskStatus.CMO_REVIEW, self.name, f"AI pre-screening approved: {decision_reason}")
                self.tasks_completed += 1
                logger.info(f"Task {task.id} passed AI pre-screening by {self.name}: {decision_reason}")
                
                # Log the AI-based approval with explicit reason
                from Utils.logger import log_manager_review
                log_manager_review(
                    department=self._get_department_name(),
                    manager_name=self.name,
                    task_id=task.id,
                    decision="AI_PRESCREENED",
                    reason=f"AI initial screening passed: {decision_reason}"
                )
                
                return True
            else:
                # Extract specific feedback for the rejection reason
                task.rejection_reason = decision_reason
                task.update_status(TaskStatus.UNDER_REVIEW, self.name, f"AI feedback: {decision_reason}")
                logger.info(f"Task {task.id} requires revision after AI screening: {decision_reason}")
                
                # Log the AI-based rejection with explicit reason
                from Utils.logger import log_manager_review
                log_manager_review(
                    department=self._get_department_name(),
                    manager_name=self.name,
                    task_id=task.id,
                    decision="AI_REJECTED",
                    reason=f"AI initial screening failed: {decision_reason}"
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error in AI review of task {task.id}: {str(e)}")
            task.rejection_reason = f"Technical error during AI review: {str(e)}"
            task.update_status(
                TaskStatus.REJECTED, 
                self.name, 
                f"AI review error: {str(e)}"
            )
            
            # Log the technical error
            from Utils.logger import log_manager_review
            log_manager_review(
                department=self._get_department_name(),
                manager_name=self.name,
                task_id=task.id,
                decision="AI_ERROR",
                reason=f"Technical error during AI review: {str(e)}"
            )
            
            return False
    
    def _extract_decision_reason(self, review_result: str, approved: bool) -> str:
        """Extract decision reason from AI response for both approval and rejection"""
        try:
            # Clean the response to handle markdown formatting
            cleaned_result = review_result.replace("*", "").replace("#", "").strip()
            
            if approved:
                # Look for "APPROVE" followed by explanation
                if "APPROVE" in cleaned_result.upper():
                    # Split by "APPROVE" and take everything after it
                    parts = cleaned_result.upper().split("APPROVE", 1)
                    if len(parts) > 1:
                        reason = parts[1].strip()
                        # Remove common prefixes like "D", ":", "-", etc.
                        reason = reason.lstrip("D").lstrip(":").lstrip("-").lstrip(".").strip()
                        if reason:
                            return reason
                
                # If APPROVE pattern not found, return the cleaned response as the reason
                return cleaned_result.strip()
            else:
                # Look for "REJECT" followed by explanation
                if "REJECT" in cleaned_result.upper():
                    # Split by "REJECT" and take everything after it
                    parts = cleaned_result.upper().split("REJECT", 1)
                    if len(parts) > 1:
                        reason = parts[1].strip()
                        # Remove common prefixes like "ED", ":", "-", etc.
                        reason = reason.lstrip("ED").lstrip(":").lstrip("-").lstrip(".").strip()
                        if reason:
                            return reason
                
                # If REJECT pattern not found, return the cleaned response as the reason
                return cleaned_result.strip()
        except Exception:
            return "Unable to extract decision reason from review"
    
    def _get_department_name(self) -> str:
        """Get department name from manager name"""
        try:
            # Extract department from manager name
            if "Content" in self.name:
                return "ContentMarketing"
            elif "Digital" in self.name:
                return "DigitalMarketing" 
            elif "Product" in self.name:
                return "ProductMarketing"
            elif "Executive" in self.name:
                return "Executive"
            else:
                return "General"
        except Exception:
            return "General"
    
    async def _request_revision(self, task: Task, feedback: str) -> bool:
        """Request agent to revise their work based on manager feedback"""
        logger.info(f"Requesting revision from {task.assigned_agent.name} for task {task.id}")
        
        try:
            # Create revision prompt for the agent
            revision_prompt = f"""
REVISION REQUEST

Original Task: {task.description}
Your Previous Solution: {task.output}

Manager Feedback: {feedback}

Please revise your solution to address the manager's feedback and better match what the user originally requested. Focus specifically on the feedback provided.

Provide an improved solution that directly addresses the concerns raised.
"""
            
            # Update task status to indicate revision in progress
            task.update_status(TaskStatus.IN_PROGRESS, self.name, f"Revision requested: {feedback}")
            
            # Get revised solution from agent
            if not task.assigned_agent.chat_service:
                logger.error("Agent chat service not available for revision")
                return False
            
            chat_history = ChatHistory()
            chat_history.add_system_message(task.assigned_agent.system_prompt)
            chat_history.add_user_message(revision_prompt)
            
            response = await task.assigned_agent.chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=PromptExecutionSettings(
                    max_tokens=2000,
                    temperature=0.7
                )
            )
            
            revised_output = str(response) if response else None
            
            if revised_output:
                task.output = revised_output
                task.update_status(TaskStatus.UNDER_REVIEW, task.assigned_agent.name, "Revision completed")
                logger.info(f"Agent {task.assigned_agent.name} provided revision for task {task.id}")
                return True
            else:
                logger.error(f"Agent {task.assigned_agent.name} failed to provide revision for task {task.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting revision for task {task.id}: {str(e)}")
            return False
    
    def get_team_status(self) -> Dict[str, Any]:
        """Get team status and metrics"""
        agent_info = []
        total_agent_tasks = 0
        total_agent_completed = 0
        
        for agent in self.team_members:
            metrics = agent.get_performance_metrics()
            agent_info.append({
                "name": agent.name,
                "role": agent.role,
                "type": agent.type.value,
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
                "success_rate": metrics["success_rate"]
            })
            total_agent_tasks += agent.tasks_completed + agent.tasks_failed
            total_agent_completed += agent.tasks_completed
        
        return {
            "manager": self.name,
            "role": self.role,
            "subordinates": len(self.team_members),
            "total_tasks": self.tasks_assigned,
            "completed_tasks": self.tasks_completed,
            "team_success_rate": (total_agent_completed / total_agent_tasks * 100) if total_agent_tasks > 0 else 0,
            "agents": agent_info
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get manager performance metrics"""
        team_status = self.get_team_status()
        
        return {
            "manager_name": self.name,
            "role": self.role,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "team_size": len(self.team_members),
            "team_performance": team_status["team_success_rate"],
            "uptime": self.get_uptime()
        }
    
    def get_uptime(self) -> str:
        """Get manager uptime as readable string"""
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
        """Convert manager to dictionary"""
        return {
            "name": self.name,
            "role": self.role,
            "team_size": len(self.team_members),
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "team_members": [agent.name for agent in self.team_members],
            "created_at": self.created_at.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.name} ({self.role}) - {len(self.team_members)} team members"
    
    async def get_memory_context(self, query: str, max_memories: int = 5) -> str:
        """Get relevant memory context for the query"""
        if not self.memory_manager:
            return ""
        
        try:
            return await self.memory_manager.get_relevant_context(
                current_task=query,
                max_memories=max_memories
            )
        except Exception as e:
            logger.warning(f"Memory context retrieval failed for {self.name}: {e}")
            return ""
    
    def has_memory_access(self) -> bool:
        """Check if manager has memory access configured"""
        return self.memory_manager is not None
    
    def __repr__(self) -> str:
        return f"Manager(name='{self.name}', role='{self.role}', team_size={len(self.team_members)})" 