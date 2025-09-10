"""
Task management system with clean, readable naming
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    CMO_REVIEW = "cmo_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class WorkflowEntry:
    """Single workflow step entry"""
    status: TaskStatus
    actor: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class Task:
    """
    Task entity with clean, descriptive properties
    """
    
    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        assignee: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.PENDING,
        context: Dict[str, Any] = None,
        output: str = "",
        created_at: datetime = None,
        updated_at: datetime = None,
        workflow_history: List[WorkflowEntry] = None,
        assigned_agent: Optional[Any] = None,
        assigned_manager: Optional[Any] = None,
        rejection_reason: str = "",
        revision_count: int = 0
    ):
        self.id = id
        self.title = title
        self.description = description
        self.assignee = assignee
        self.priority = priority
        self.status = status
        self.context = context or {}
        self.output = output
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.workflow_history = workflow_history or []
        self.assigned_agent = assigned_agent
        self.assigned_manager = assigned_manager
        self.rejection_reason = rejection_reason
        self.revision_count = revision_count
    
    def update_status(self, status: TaskStatus, actor: str, message: str = ""):
        """Update task status with workflow tracking"""
        self.status = status
        self.updated_at = datetime.now()
        self.add_workflow_entry(status, actor, message)
    
    def add_workflow_entry(self, status: TaskStatus, actor: str, message: str):
        """Add entry to workflow history"""
        entry = WorkflowEntry(
            status=status,
            actor=actor,
            message=message
        )
        self.workflow_history.append(entry)
    
    def get_duration(self) -> str:
        """Get task duration as readable string"""
        if not self.created_at:
            return "Unknown"
        
        duration = datetime.now() - self.created_at
        
        if duration.days > 0:
            return f"{duration.days} days"
        elif duration.seconds > 3600:
            hours = duration.seconds // 3600
            return f"{hours} hours"
        elif duration.seconds > 60:
            minutes = duration.seconds // 60
            return f"{minutes} minutes"
        else:
            return "< 1 minute"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "priority": self.priority.value,
            "status": self.status.value,
            "context": self.context,
            "output": self.output,
            "rejection_reason": self.rejection_reason,
            "revision_count": self.revision_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "duration": self.get_duration(),
            "workflow_history": [
                {
                    "status": entry.status.value,
                    "actor": entry.actor,
                    "message": entry.message,
                    "timestamp": entry.timestamp.isoformat()
                }
                for entry in self.workflow_history
            ]
        } 