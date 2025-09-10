"""
Comprehensive Task Manager
Handles task storage, assignment tracking, and agent/manager task lists
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict
import json
import os
from pathlib import Path

try:
    from Core.Tasks.task import Task, TaskStatus, TaskPriority
    from Core.Agents.agent import Agent
    from Core.Agents.manager import Manager
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Core.Tasks.task import Task, TaskStatus, TaskPriority
    from Core.Agents.agent import Agent
    from Core.Agents.manager import Manager

# Import specialized logging functions
from Utils.logger import (
    log_task_creation, 
    log_task_activity, 
    log_verification_step,
    get_department_logger
)

logger = logging.getLogger("task_manager")


class TaskManager:
    """
    Centralized task management system with file-based persistence for multi-instance support
    """
    
    def __init__(self, storage_file: str = "tasks_storage.json"):
        # Central task storage
        self.storage_file = Path(storage_file)
        self.tasks: Dict[str, Task] = {}
        
        # Task organization
        self.tasks_by_status: Dict[TaskStatus, List[str]] = defaultdict(list)
        self.agent_tasks: Dict[str, List[str]] = defaultdict(list)
        self.manager_tasks: Dict[str, List[str]] = defaultdict(list)
        self.department_tasks: Dict[str, List[str]] = defaultdict(list)
        
        # System metrics
        self.total_created = 0
        self.total_completed = 0
        self.total_failed = 0
        
        # Load existing tasks from file
        self._load_tasks()
        
        logger.info(f"TaskManager initialized with {len(self.tasks)} existing tasks")
        
        # Log system initialization
        system_logger = logging.getLogger("marketing_system")
        system_logger.info("TASK_SYSTEM | TaskManager initialized | Ready for task management")
    
    def _load_tasks(self):
        """Load tasks from storage file"""
        if not self.storage_file.exists():
            logger.info("No existing task storage found, starting fresh")
            return
        
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            
            # Restore tasks
            for task_data in data.get('tasks', []):
                # Convert datetime strings back to datetime objects
                if task_data.get('created_at'):
                    task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                if task_data.get('updated_at'):
                    task_data['updated_at'] = datetime.fromisoformat(task_data['updated_at'])
                
                # Convert status and priority enums
                task_data['status'] = TaskStatus(task_data['status'])
                task_data['priority'] = TaskPriority(task_data['priority'])
                
                # Handle workflow history
                workflow_history = []
                if 'workflow_history' in task_data:
                    from .task import WorkflowEntry
                    for entry_data in task_data['workflow_history']:
                        workflow_entry = WorkflowEntry(
                            status=TaskStatus(entry_data['status']),
                            actor=entry_data['actor'],
                            message=entry_data['message'],
                            timestamp=datetime.fromisoformat(entry_data['timestamp'])
                        )
                        workflow_history.append(workflow_entry)
                    task_data['workflow_history'] = workflow_history
                
                # Remove unsupported fields for Task constructor
                task_data.pop('assigned_at', None)
                
                # Recreate task object
                task = Task(**task_data)
                self.tasks[task.id] = task
                
                # Rebuild indexes
                self.tasks_by_status[task.status].append(task.id)
                if task.assignee:
                    # Determine if assignee is agent or manager based on naming convention
                    if 'manager' in task.assignee.lower():
                        self.manager_tasks[task.assignee].append(task.id)
                    else:
                        self.agent_tasks[task.assignee].append(task.id)
                
                department = task.context.get('department', 'general')
                self.department_tasks[department].append(task.id)
            
            # Restore metrics
            self.total_created = data.get('total_created', len(self.tasks))
            self.total_completed = data.get('total_completed', 0)
            self.total_failed = data.get('total_failed', 0)
            
            logger.info(f"Loaded {len(self.tasks)} tasks from storage")
            
        except Exception as e:
            logger.error(f"Error loading tasks from storage: {e}")
            logger.info("Starting with empty task storage")
    
    def _save_tasks(self):
        """Save tasks to storage file"""
        try:
            # Prepare data for JSON serialization
            tasks_data = []
            for task in self.tasks.values():
                # Convert Task object to dict manually
                task_dict = {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'assignee': task.assignee,
                    'priority': task.priority.value,
                    'status': task.status.value,
                    'context': task.context,
                    'output': task.output,
                    'rejection_reason': task.rejection_reason,
                    'revision_count': task.revision_count,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'workflow_history': [
                        {
                            'status': entry.status.value,
                            'actor': entry.actor,
                            'message': entry.message,
                            'timestamp': entry.timestamp.isoformat()
                        }
                        for entry in task.workflow_history
                    ]
                }
                tasks_data.append(task_dict)
            
            data = {
                'tasks': tasks_data,
                'total_created': self.total_created,
                'total_completed': self.total_completed,
                'total_failed': self.total_failed,
                'last_updated': datetime.now().isoformat()
            }
            
            # Create backup before writing
            if self.storage_file.exists():
                backup_file = self.storage_file.with_suffix('.backup')
                self.storage_file.replace(backup_file)
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.tasks)} tasks to storage")
            
        except Exception as e:
            logger.error(f"Error saving tasks to storage: {e}")
            # Restore from backup if available
            backup_file = self.storage_file.with_suffix('.backup')
            if backup_file.exists():
                backup_file.replace(self.storage_file)
                logger.info("Restored from backup after save failure")
    
    def create_task(
        self, 
        task_id: str,
        title: str, 
        description: str,
        department: str = "general",
        priority: TaskPriority = TaskPriority.MEDIUM,
        created_by: str = "system",
        context: Dict[str, Any] = None
    ) -> Task:
        """
        Create and store a new task
        """
        try:
            # Create task
            task = Task(
                id=task_id,
                title=title,
                description=description,
                priority=priority,
                context=context or {"created_by": created_by, "department": department}
            )
            
            # Store task
            self.tasks[task_id] = task
            self.department_tasks[department].append(task_id)
            self.tasks_by_status[TaskStatus.PENDING].append(task_id)
            self.total_created += 1
            
            # Save to persistent storage
            self._save_tasks()
            
            # Log task creation
            log_task_activity(
                department=department,
                task_id=task_id,
                activity="CREATED",
                actor=created_by,
                details=f"Title: {title[:50]}{'...' if len(title) > 50 else ''} | Priority: {priority.value}"
            )
            
            logger.info(f"Task created: {task_id} | {title[:50]}{'...' if len(title) > 50 else ''}")
            return task
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    def assign_task_to_agent(self, task_id: str, agent, manager=None) -> bool:
        """
        Assign a task to an agent
        
        Args:
            task_id: The task ID to assign
            agent: Agent object or agent name string
            manager: Optional manager object or manager name string
        """
        try:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found for assignment")
                return False
            
            task = self.tasks[task_id]
            
            # Handle both string agent names and Agent objects
            if isinstance(agent, str):
                agent_name = agent
            else:
                agent_name = getattr(agent, 'name', str(agent))
            
            # Handle both string manager names and Manager objects
            if manager:
                if isinstance(manager, str):
                    manager_name = manager
                else:
                    manager_name = getattr(manager, 'name', str(manager))
            else:
                manager_name = None
            
            # Update task assignment
            task.assignee = agent_name
            task.assigned_at = datetime.now()
            
            # Update tracking
            if agent_name not in self.agent_tasks:
                self.agent_tasks[agent_name] = []
            self.agent_tasks[agent_name].append(task_id)
            
            if manager_name:
                if manager_name not in self.manager_tasks:
                    self.manager_tasks[manager_name] = []
                self.manager_tasks[manager_name].append(task_id)
            
            department = task.context.get("department", "general")
            
            # Log assignment
            log_task_activity(
                department=department,
                task_id=task_id,
                activity="ASSIGNED",
                actor="TaskManager",
                details=f"Agent: {agent_name}" + (f" | Manager: {manager_name}" if manager_name else "")
            )
            
            # Save to persistent storage
            self._save_tasks()
            
            logger.info(f"Task {task_id} assigned to agent {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {task_id}: {e}")
            return False
    
    def assign_task_to_manager(self, task_id: str, manager) -> bool:
        """
        Assign a task to a manager
        
        Args:
            task_id: The task ID to assign
            manager: Manager object or manager name string
        """
        try:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found for assignment")
                return False
            
            task = self.tasks[task_id]
            
            # Handle both string manager names and Manager objects
            if isinstance(manager, str):
                manager_name = manager
            else:
                manager_name = getattr(manager, 'name', str(manager))
            
            # Update task assignment
            task.assignee = manager_name
            task.assigned_at = datetime.now()
            
            # Update tracking
            if manager_name not in self.manager_tasks:
                self.manager_tasks[manager_name] = []
            self.manager_tasks[manager_name].append(task_id)
            
            department = task.context.get("department", "general")
            
            # Log assignment
            log_task_activity(
                department=department,
                task_id=task_id,
                activity="ASSIGNED",
                actor="TaskManager",
                details=f"Manager: {manager_name}"
            )
            
            # Save to persistent storage
            self._save_tasks()
            
            logger.info(f"Task {task_id} assigned to manager {manager_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {task_id} to manager: {e}")
            return False
    
    def update_task_status(self, task_id: str, status: TaskStatus, actor: str, message: str = "") -> bool:
        """
        Update task status and tracking
        """
        try:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found for status update")
                return False
            
            task = self.tasks[task_id]
            old_status = task.status
            department = task.context.get("department", "general")
            
            # Update task
            task.update_status(status, actor, message)
            
            # Update status tracking
            if task_id in self.tasks_by_status[old_status]:
                self.tasks_by_status[old_status].remove(task_id)
            self.tasks_by_status[status].append(task_id)
            
            # Update completion metrics
            if status == TaskStatus.COMPLETED:
                self.total_completed += 1
            elif status == TaskStatus.REJECTED:
                self.total_failed += 1
            
            # Log status change
            log_task_activity(
                department=department,
                task_id=task_id,
                activity="STATUS_CHANGED",
                actor=actor,
                details=f"{old_status.value} -> {status.value} | Message: {message}"
            )
            
            # Log verification steps for specific statuses
            if status in [TaskStatus.UNDER_REVIEW, TaskStatus.CMO_REVIEW, TaskStatus.COMPLETED, TaskStatus.REJECTED]:
                log_verification_step(
                    task_id=task_id,
                    step=status.value.upper(),
                    actor=actor,
                    status="UPDATED",
                    message=message
                )
            
            # Save to persistent storage
            self._save_tasks()
            
            logger.info(f"Task {task_id} status updated: {old_status.value} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID"""
        return self.tasks.get(task_id)
    
    def get_agent_tasks(self, agent_name: str, status_filter: TaskStatus = None) -> List[Task]:
        """
        Get all tasks assigned to a specific agent
        """
        task_ids = self.agent_tasks.get(agent_name, [])
        tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
        
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        
        return tasks
    
    def get_manager_tasks(self, manager_name: str, status_filter: TaskStatus = None) -> List[Task]:
        """
        Get all tasks managed by a specific manager
        """
        task_ids = self.manager_tasks.get(manager_name, [])
        tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
        
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        
        return tasks
    
    def get_department_tasks(self, department: str, status_filter: TaskStatus = None) -> List[Task]:
        """
        Get all tasks for a specific department
        """
        task_ids = self.department_tasks.get(department, [])
        tasks = [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
        
        if status_filter:
            tasks = [task for task in tasks if task.status == status_filter]
        
        return tasks
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get all tasks with a specific status
        """
        task_ids = self.tasks_by_status.get(status, [])
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks in the system"""
        return list(self.tasks.values())
    
    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """Get a summary of a specific task"""
        task = self.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "assignee": task.assignee,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "duration": task.get_duration(),
            "workflow_history": [
                {
                    "status": entry.status.value,
                    "actor": entry.actor,
                    "message": entry.message,
                    "timestamp": entry.timestamp.isoformat()
                }
                for entry in task.workflow_history
            ]
        }
    
    def get_agent_dashboard(self, agent_name: str) -> Dict[str, Any]:
        """
        Get a dashboard view for an agent showing their tasks
        """
        all_tasks = self.get_agent_tasks(agent_name)
        
        pending_tasks = [t for t in all_tasks if t.status == TaskStatus.PENDING]
        in_progress_tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
        under_review_tasks = [t for t in all_tasks if t.status == TaskStatus.UNDER_REVIEW]
        completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        rejected_tasks = [t for t in all_tasks if t.status == TaskStatus.REJECTED]
        
        return {
            "agent_name": agent_name,
            "total_tasks": len(all_tasks),
            "pending": len(pending_tasks),
            "in_progress": len(in_progress_tasks),
            "under_review": len(under_review_tasks),
            "completed": len(completed_tasks),
            "rejected": len(rejected_tasks),
            "tasks": {
                "pending": [self.get_task_summary(t.id) for t in pending_tasks],
                "in_progress": [self.get_task_summary(t.id) for t in in_progress_tasks],
                "under_review": [self.get_task_summary(t.id) for t in under_review_tasks],
                "completed": [self.get_task_summary(t.id) for t in completed_tasks[-5:]],  # Last 5
                "rejected": [self.get_task_summary(t.id) for t in rejected_tasks[-5:]]   # Last 5
            }
        }
    
    def get_manager_dashboard(self, manager_name: str) -> Dict[str, Any]:
        """
        Get a dashboard view for a manager showing their team's tasks
        """
        all_tasks = self.get_manager_tasks(manager_name)
        
        # Group by agent
        agent_tasks = defaultdict(list)
        for task in all_tasks:
            agent_tasks[task.assignee].append(task)
        
        # Status counts
        status_counts = defaultdict(int)
        for task in all_tasks:
            status_counts[task.status.value] += 1
        
        return {
            "manager_name": manager_name,
            "total_tasks": len(all_tasks),
            "status_breakdown": dict(status_counts),
            "agent_assignments": {
                agent: len(tasks) for agent, tasks in agent_tasks.items()
            },
            "recent_tasks": [
                self.get_task_summary(t.id) for t in sorted(all_tasks, key=lambda x: x.updated_at, reverse=True)[:10]
            ]
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get overall system task metrics
        """
        status_counts = {status.value: len(task_ids) for status, task_ids in self.tasks_by_status.items()}
        
        # Calculate success rate
        success_rate = (self.total_completed / self.total_created * 100) if self.total_created > 0 else 0
        
        metrics = {
            "total_tasks_created": self.total_created,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "success_rate": round(success_rate, 2),
            "status_breakdown": status_counts,
            "department_breakdown": {
                dept: len(task_ids) for dept, task_ids in self.department_tasks.items()
            },
            "active_agents": len(self.agent_tasks),
            "active_managers": len(self.manager_tasks)
        }
        
        # Log metrics request
        logger.info(f"System metrics requested | Tasks: {self.total_created} | Success Rate: {success_rate:.1f}%")
        
        return metrics
    
    def search_tasks(self, query: str, limit: int = 10) -> List[Task]:
        """
        Search tasks by title or description
        """
        query_lower = query.lower()
        matching_tasks = []
        
        for task in self.tasks.values():
            if (query_lower in task.title.lower() or 
                query_lower in task.description.lower()):
                matching_tasks.append(task)
                
                if len(matching_tasks) >= limit:
                    break
        
        return matching_tasks
    
    def cleanup_completed_tasks(self, days_old: int = 30) -> int:
        """
        Archive old completed tasks (in a real system, this would move to archive storage)
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        tasks_to_archive = []
        
        for task in self.tasks.values():
            if (task.status == TaskStatus.COMPLETED and 
                task.updated_at and task.updated_at < cutoff_date):
                tasks_to_archive.append(task.id)
        
        # For now, just log what would be archived
        logger.info(f"Would archive {len(tasks_to_archive)} completed tasks older than {days_old} days")
        return len(tasks_to_archive)

    def reload_tasks(self):
        """Reload tasks from storage file to sync with other instances"""
        try:
            old_count = len(self.tasks)
            
            # Clear current data
            self.tasks.clear()
            self.tasks_by_status.clear()
            self.agent_tasks.clear()
            self.manager_tasks.clear()
            self.department_tasks.clear()
            
            # Reload from file
            self._load_tasks()
            
            new_count = len(self.tasks)
            logger.info(f"Reloaded tasks: {old_count} -> {new_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error reloading tasks: {e}")
            return False


# Global task manager instance
_task_manager_instance = None

def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = TaskManager()
    return _task_manager_instance 