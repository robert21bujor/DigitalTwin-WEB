"""
Core module for the AI Company System
Simplified and streamlined structure.
"""

# Core components - only what actually exists
from .Agents.agent import Agent, AgentType
from .Agents.manager import Manager
from .Tasks.task import Task, TaskStatus
from .Tasks.task_manager import TaskManager, get_task_manager

__all__ = [
    'Agent', 'AgentType', 'Manager',
    'Task', 'TaskStatus', 'TaskManager', 'get_task_manager'
]
