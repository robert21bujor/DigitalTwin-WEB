"""
Authentication module for Role-Based Multi-Agent Marketing System
"""

from .auth_manager import AuthManager
from .user_models import User, UserRole, AgentAssignment, AgentType
from .access_control import AccessController, MemoryAccessController
from .terminal_interface import TerminalAuthInterface

__all__ = [
    'AuthManager',
    'User',
    'UserRole',
    'AgentAssignment',
    'AgentType',
    'AccessController',
    'MemoryAccessController',
    'TerminalAuthInterface'
] 