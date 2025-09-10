"""
Access Control System for Role-Based Multi-Agent Authentication
"""

import logging
from typing import Dict, List, Optional, Any
from functools import wraps
from datetime import datetime

from .user_models import User, UserRole, AgentType, AgentAssignment
from .auth_manager import AuthManager

logger = logging.getLogger(__name__)


class AccessController:
    """Handles access control and authorization for the multi-agent system"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.access_log: List[Dict[str, Any]] = []
    
    def require_authentication(self, func):
        """Decorator to require authentication for function access"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.auth_manager.is_authenticated():
                logger.warning(f"Unauthorized access attempt to {func.__name__}")
                self._log_access_attempt(func.__name__, "DENIED", "Not authenticated")
                raise PermissionError("Authentication required")
            
            self._log_access_attempt(func.__name__, "GRANTED", "Authenticated user")
            return func(*args, **kwargs)
        
        return wrapper
    
    def require_agent_access(self, agent_type: AgentType):
        """Decorator to require specific agent access"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.auth_manager.is_authenticated():
                    logger.warning(f"Unauthorized access attempt to {func.__name__}")
                    self._log_access_attempt(func.__name__, "DENIED", "Not authenticated")
                    raise PermissionError("Authentication required")
                
                if not self.auth_manager.validate_agent_access(agent_type):
                    current_user = self.auth_manager.get_current_user()
                    username = current_user.username if current_user else "unknown"
                    logger.warning(f"User {username} denied access to {agent_type.value}")
                    self._log_access_attempt(func.__name__, "DENIED", f"No access to {agent_type.value}")
                    raise PermissionError(f"Access denied to {agent_type.value} agent")
                
                self._log_access_attempt(func.__name__, "GRANTED", f"Access to {agent_type.value}")
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_memory_access(self, collection_name: str):
        """Decorator to require specific memory collection access"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.auth_manager.is_authenticated():
                    logger.warning(f"Unauthorized access attempt to {func.__name__}")
                    self._log_access_attempt(func.__name__, "DENIED", "Not authenticated")
                    raise PermissionError("Authentication required")
                
                if not self.auth_manager.validate_memory_access(collection_name):
                    current_user = self.auth_manager.get_current_user()
                    username = current_user.username if current_user else "unknown"
                    logger.warning(f"User {username} denied access to memory: {collection_name}")
                    self._log_access_attempt(func.__name__, "DENIED", f"No access to memory: {collection_name}")
                    raise PermissionError(f"Access denied to memory collection: {collection_name}")
                
                self._log_access_attempt(func.__name__, "GRANTED", f"Access to memory: {collection_name}")
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_cmo_access(self, func):
        """Decorator to require CMO access"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.auth_manager.is_authenticated():
                logger.warning(f"Unauthorized access attempt to {func.__name__}")
                self._log_access_attempt(func.__name__, "DENIED", "Not authenticated")
                raise PermissionError("Authentication required")
            
            current_user = self.auth_manager.get_current_user()
            if not current_user or not current_user.is_cmo():
                username = current_user.username if current_user else "unknown"
                logger.warning(f"User {username} denied CMO access")
                self._log_access_attempt(func.__name__, "DENIED", "Not CMO")
                raise PermissionError("CMO access required")
            
            self._log_access_attempt(func.__name__, "GRANTED", "CMO access")
            return func(*args, **kwargs)
        
        return wrapper
    
    def require_manager_access(self, func):
        """Decorator to require manager access"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.auth_manager.is_authenticated():
                logger.warning(f"Unauthorized access attempt to {func.__name__}")
                self._log_access_attempt(func.__name__, "DENIED", "Not authenticated")
                raise PermissionError("Authentication required")
            
            current_user = self.auth_manager.get_current_user()
            if not current_user or not (current_user.is_cmo() or current_user.is_manager()):
                username = current_user.username if current_user else "unknown"
                logger.warning(f"User {username} denied manager access")
                self._log_access_attempt(func.__name__, "DENIED", "Not manager or CMO")
                raise PermissionError("Manager access required")
            
            self._log_access_attempt(func.__name__, "GRANTED", "Manager access")
            return func(*args, **kwargs)
        
        return wrapper
    
    def validate_user_context(self, user_id: str) -> bool:
        """Validate if current user can access another user's context"""
        if not self.auth_manager.is_authenticated():
            return False
        
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return False
        
        # CMO can access any user's context
        if current_user.is_cmo():
            return True
        
        # Users can only access their own context
        return current_user.id == user_id
    
    def filter_accessible_agents(self, agents: List[AgentType]) -> List[AgentType]:
        """Filter agents list to only include accessible ones"""
        if not self.auth_manager.is_authenticated():
            return []
        
        accessible_agents = self.auth_manager.get_accessible_agents()
        return [agent for agent in agents if agent in accessible_agents]
    
    def filter_accessible_memory_collections(self, collections: List[str]) -> List[str]:
        """Filter memory collections to only include accessible ones"""
        if not self.auth_manager.is_authenticated():
            return []
        
        accessible_collections = self.auth_manager.get_accessible_memory_collections()
        return [collection for collection in collections if collection in accessible_collections]
    
    def get_user_access_summary(self) -> Dict[str, Any]:
        """Get summary of current user's access permissions"""
        if not self.auth_manager.is_authenticated():
            return {"authenticated": False}
        
        current_user = self.auth_manager.get_current_user()
        
        return {
            "authenticated": True,
            "user_id": current_user.id,
            "username": current_user.username,
            "role": current_user.role.value,
            "is_cmo": current_user.is_cmo(),
            "is_manager": current_user.is_manager(),
            "accessible_agents": [agent.value for agent in current_user.get_accessible_agents()],
            "accessible_memory_collections": current_user.get_accessible_memory_collections(),
            "agent_assignments": [
                {
                    "agent_type": assignment.agent_type.value,
                    "access_level": assignment.access_level,
                    "memory_access": assignment.memory_access
                }
                for assignment in current_user.agent_assignments
            ]
        }
    
    def _log_access_attempt(self, resource: str, status: str, reason: str):
        """Log access attempt for audit purposes"""
        user_info = "anonymous"
        if self.auth_manager.is_authenticated():
            current_user = self.auth_manager.get_current_user()
            user_info = f"{current_user.username} ({current_user.role.value})"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_info,
            "resource": resource,
            "status": status,
            "reason": reason
        }
        
        self.access_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get access log (CMO only)"""
        if not self.auth_manager.is_authenticated():
            return []
        
        current_user = self.auth_manager.get_current_user()
        if not current_user.is_cmo():
            return []
        
        return self.access_log.copy()
    
    def clear_access_log(self):
        """Clear access log (CMO only)"""
        if not self.auth_manager.is_authenticated():
            return
        
        current_user = self.auth_manager.get_current_user()
        if current_user.is_cmo():
            self.access_log.clear()
            logger.info("Access log cleared by CMO")


class MemoryAccessController:
    """Specialized access controller for memory operations"""
    
    def __init__(self, access_controller: AccessController):
        self.access_controller = access_controller
        self.auth_manager = access_controller.auth_manager
    
    def validate_memory_read(self, collection_name: str) -> bool:
        """Validate memory read access"""
        if not self.auth_manager.is_authenticated():
            return False
        
        current_user = self.auth_manager.get_current_user()
        return current_user.has_memory_read_access(collection_name)
    
    def validate_memory_write(self, collection_name: str) -> bool:
        """Validate memory write access"""
        if not self.auth_manager.is_authenticated():
            return False
        
        current_user = self.auth_manager.get_current_user()
        return current_user.has_memory_write_access(collection_name)
    
    def get_readable_collections(self) -> List[str]:
        """Get all memory collections user can read"""
        if not self.auth_manager.is_authenticated():
            return []
        
        current_user = self.auth_manager.get_current_user()
        return current_user.get_readable_memory_collections()
    
    def get_writable_collections(self) -> List[str]:
        """Get all memory collections user can write to"""
        if not self.auth_manager.is_authenticated():
            return []
        
        current_user = self.auth_manager.get_current_user()
        return current_user.get_writable_memory_collections()
    
    def can_access_private_memory(self, agent_type: AgentType) -> bool:
        """Check if user can access private memory for specific agent"""
        if not self.auth_manager.is_authenticated():
            return False
        
        current_user = self.auth_manager.get_current_user()
        
        # Check if user has assignment for this agent
        assignment = current_user.get_agent_assignment(agent_type)
        if not assignment:
            return False
        
        # Check if assignment includes private memory
        private_memory_name = f'{agent_type.value}-private-memory'
        return private_memory_name in assignment.memory_access
    
    def get_agent_memory_access(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get detailed memory access for specific agent"""
        if not self.auth_manager.is_authenticated():
            return {"has_access": False}
        
        current_user = self.auth_manager.get_current_user()
        assignment = current_user.get_agent_assignment(agent_type)
        
        if not assignment:
            return {"has_access": False}
        
        return {
            "has_access": True,
            "access_level": assignment.access_level,
            "memory_collections": assignment.memory_access,
            "can_read": True,
            "can_write": assignment.access_level in ['full', 'write'],
            "private_memory_access": self.can_access_private_memory(agent_type)
        } 