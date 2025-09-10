"""
User-Agent Companion Matching System
Defines which users have access to calendar/files through their designated companion agents
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
import sys
from pathlib import Path

# Add project root to path to import centralized constants
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

# Import UserRole from Authentication to avoid duplication
try:
    from Auth.User_management.user_models import UserRole
    logger.info(f"✅ UserRole enum imported with {len(list(UserRole))} members")
except ImportError:
    logger.warning("Could not import UserRole from Authentication, using fallback enum")
    # Fallback if import fails
    class UserRole(str, Enum):
        """User roles that map to specific agent companions"""
        CMO = "cmo"
        BUSINESS_DEV_MANAGER = "business_dev_manager"
        OPERATIONS_MANAGER = "operations_manager"
        IPM_AGENT = "ipm_agent"
        BDM_AGENT = "bdm_agent"
        PRESALES_ENGINEER_AGENT = "presales_engineer_agent"
        HEAD_OF_OPERATIONS_AGENT = "head_of_operations_agent"
        SENIOR_CSM_AGENT = "senior_csm_agent"
        SENIOR_DELIVERY_CONSULTANT_AGENT = "senior_delivery_consultant_agent"
        DELIVERY_CONSULTANT_EN_AGENT = "delivery_consultant_en_agent"
        DELIVERY_CONSULTANT_BG_AGENT = "delivery_consultant_bg_agent"
        DELIVERY_CONSULTANT_HU_AGENT = "delivery_consultant_hu_agent"
        LEGAL_AGENT = "legal_agent"
        REPORTING_MANAGER_AGENT = "reporting_manager_agent"
        REPORTING_SPECIALIST_AGENT = "reporting_specialist_agent"

class UserAgentMatcher:
    """
    Handles mapping between user roles and their companion agents
    Determines calendar/file access permissions based on user-agent relationships
    """
    
    # Define which user roles map to which agent companions
    USER_AGENT_COMPANIONS: Dict[UserRole, str] = {
        UserRole.CMO: "agent.executive_cmo",
        UserRole.BUSINESS_DEV_MANAGER: "agent.bdm_agent", 
        UserRole.OPERATIONS_MANAGER: "agent.head_of_operations",
        UserRole.IPM_AGENT: "agent.ipm_agent",
        UserRole.BDM_AGENT: "agent.bdm_agent",
        UserRole.PRESALES_ENGINEER_AGENT: "agent.presales_engineer",
        UserRole.HEAD_OF_OPERATIONS_AGENT: "agent.head_of_operations",
        UserRole.SENIOR_CSM_AGENT: "agent.senior_csm",
        UserRole.SENIOR_DELIVERY_CONSULTANT_AGENT: "agent.senior_delivery_consultant",
        UserRole.DELIVERY_CONSULTANT_EN_AGENT: "agent.delivery_consultant_en",
        UserRole.DELIVERY_CONSULTANT_BG_AGENT: "agent.delivery_consultant_bg", 
        UserRole.DELIVERY_CONSULTANT_HU_AGENT: "agent.delivery_consultant_hu",
        UserRole.LEGAL_AGENT: "agent.legal_agent",
        UserRole.REPORTING_MANAGER_AGENT: "agent.reporting_manager",
        UserRole.REPORTING_SPECIALIST_AGENT: "agent.reporting_specialist",
    }
    
    # Agents that should have calendar access when acting as user companions
    CALENDAR_ENABLED_AGENTS = {
        # Executive and Leadership
        "agent.executive_cmo",           # CMO's digital twin
        
        # Business Development agents
        "agent.bdm_agent",               # Business Dev Manager's twin
        "agent.ipm_agent",               # IPM agent
        "agent.presales_engineer",       # Presales engineer agent
        
        # Operations agents
        "agent.head_of_operations",      # Operations Manager's twin
        "agent.senior_csm",              # Senior CSM's twin
        "agent.senior_delivery_consultant", # Senior Delivery Consultant
        "agent.delivery_consultant_en",  # English Delivery Consultant
        "agent.delivery_consultant_bg",  # Bulgarian Delivery Consultant
        "agent.delivery_consultant_hu",  # Hungarian Delivery Consultant
        "agent.legal_agent",             # Legal agent
        "agent.reporting_manager",       # Reporting Manager's twin
        "agent.reporting_specialist",    # Reporting Specialist
    }
    
    # Agents that should have file access when acting as user companions  
    FILE_ENABLED_AGENTS = {
        # Executive and Leadership
        "agent.executive_cmo",           # CMO needs access to all files
        
        # Marketing agents
        "agent.content_specialist",      # Content needs marketing materials
        "agent.seo_specialist",          # SEO needs web/content files
        "agent.analytics_specialist",    # Analytics needs data files
        
        # BusinessDev agents
        "agent.ipm_agent",               # IPM needs partnership files
        "agent.bdm_agent",               # Business Dev Manager needs business dev files
        "agent.presales_engineer",       # Presales needs technical docs
        
        # Operations agents
        "agent.head_of_operations",      # Operations needs operational docs
        "agent.senior_csm",              # Senior CSM needs client files
        "agent.senior_delivery_consultant",  # Senior Delivery needs project docs
        "agent.delivery_consultant_en",  # Delivery consultant needs project files
        "agent.delivery_consultant_bg",  # Delivery consultant needs project files
        "agent.delivery_consultant_hu",  # Delivery consultant needs project files
        "agent.legal_agent",             # Legal needs contract/legal docs
        "agent.reporting_manager",       # Reporting needs data files
        "agent.reporting_specialist",    # Reporting specialist needs data files
    }
    
    @classmethod
    def get_user_companion_agent(cls, user_role: str) -> Optional[str]:
        """
        Get the companion agent ID for a given user role
        
        Args:
            user_role: The user's role (e.g., "cmo", "operations_manager")
            
        Returns:
            Agent ID if user has a companion, None otherwise
        """
        try:
            role_enum = UserRole(user_role.lower())
            companion = cls.USER_AGENT_COMPANIONS.get(role_enum)
            
            if companion:
                logger.info(f"👥 User role '{user_role}' has companion agent: {companion}")
            else:
                logger.info(f"👤 User role '{user_role}' has no designated companion agent")
                
            return companion
        except ValueError:
            logger.warning(f"⚠️ Unknown user role: {user_role}")
            return None
    
    @classmethod
    def can_user_access_calendar_via_agent(cls, user_role: str, agent_id: str) -> bool:
        """
        Check if a user can access calendar functionality through a specific agent
        
        Args:
            user_role: The user's role
            agent_id: The agent being used
            
        Returns:
            True if user can access calendar through this agent
        """
        companion = cls.get_user_companion_agent(user_role)
        
        # User can access calendar if:
        # 1. This agent is their designated companion AND
        # 2. The companion agent is calendar-enabled
        can_access = (
            companion == agent_id and 
            agent_id in cls.CALENDAR_ENABLED_AGENTS
        )
        
        if can_access:
            logger.info(f"🗓️ User '{user_role}' CAN access calendar via companion agent '{agent_id}'")
        else:
            logger.info(f"🚫 User '{user_role}' cannot access calendar via agent '{agent_id}' (not companion or not calendar-enabled)")
            
        return can_access
    
    @classmethod  
    def can_user_access_files_via_agent(cls, user_role: str, agent_id: str, folder_path: str = None) -> bool:
        """
        Check if a user can access file functionality through a specific agent
        
        Args:
            user_role: The user's role
            agent_id: The agent being used
            folder_path: Optional specific folder path being accessed
            
        Returns:
            True if user can access files through this agent
        """
        companion = cls.get_user_companion_agent(user_role)
        
        # Define management roles that can access all files across departments
        management_roles = {
            "cmo", "operations_manager", "business_dev_manager", 
            "head_of_operations_agent", "executive_cmo"
        }
        
        # Check if accessing a private folder
        is_private_folder = folder_path and ("private" in folder_path.lower() or "_private" in folder_path.lower())
        
        # Determine which department this folder belongs to
        folder_department = None
        if folder_path:
            if "business development" in folder_path.lower() or "/business development" in folder_path.lower():
                folder_department = "business_development"
            elif "operations" in folder_path.lower():
                folder_department = "operations"
            elif "marketing" in folder_path.lower():
                folder_department = "marketing"
            elif "executive" in folder_path.lower():
                folder_department = "executive"
        
        # Determine user's department from their companion agent
        user_department = None
        if companion:
            # Business Development agents
            if any(agent in companion for agent in ["bdm_agent", "ipm_agent", "presales_engineer"]):
                user_department = "business_development"
            # Operations agents
            elif any(agent in companion for agent in ["head_of_operations", "senior_csm", "senior_delivery_consultant", 
                                                     "delivery_consultant_en", "delivery_consultant_bg", "delivery_consultant_hu",
                                                     "legal_agent", "reporting_manager", "reporting_specialist"]):
                user_department = "operations"
            # Marketing agents
            elif any(agent in companion for agent in ["content_specialist", "seo_specialist", "analytics_specialist"]):
                user_department = "marketing"
            # Executive agents
            elif any(agent in companion for agent in ["cmo", "executive_cmo"]):
                user_department = "executive"
        
        # User can access files if:
        # 1. Companion access to their own department (including private folders), OR
        # 2. Companion access to other departments' public folders only, OR  
        # 3. Management role access to non-private folders, OR
        # 4. Public access to non-private folders
        is_own_department_companion = (companion == agent_id and agent_id in cls.FILE_ENABLED_AGENTS and 
                                      (not folder_department or folder_department == user_department))
        is_other_department_public = (companion == agent_id and agent_id in cls.FILE_ENABLED_AGENTS and 
                                     folder_department and folder_department != user_department and not is_private_folder)
        is_management_access = (user_role.lower() in management_roles and agent_id in cls.FILE_ENABLED_AGENTS and not is_private_folder)  
        is_public_access = (agent_id in cls.FILE_ENABLED_AGENTS and not is_private_folder)  
        
        can_access = is_own_department_companion or is_other_department_public or is_management_access or is_public_access
        
        if can_access:
            if is_own_department_companion:
                logger.info(f"📁 User '{user_role}' CAN access files via companion agent '{agent_id}' (own department)" + (f" (folder: {folder_path})" if folder_path else ""))
            elif is_other_department_public:
                logger.info(f"📁 User '{user_role}' CAN access public files via companion agent '{agent_id}' (other department)" + (f" (folder: {folder_path})" if folder_path else ""))
            elif is_management_access:
                logger.info(f"📁 Management user '{user_role}' CAN access files via cross-departmental agent '{agent_id}'" + (f" (folder: {folder_path})" if folder_path else ""))
            else:
                logger.info(f"📁 User '{user_role}' CAN access public files via agent '{agent_id}'" + (f" (folder: {folder_path})" if folder_path else ""))
        else:
            if is_private_folder and folder_department != user_department:
                logger.info(f"🚫 User '{user_role}' cannot access PRIVATE folder '{folder_path}' from different department via agent '{agent_id}' (restricted)")
            elif is_private_folder:
                logger.info(f"🚫 User '{user_role}' cannot access PRIVATE folder '{folder_path}' via agent '{agent_id}' (not authorized)")
            else:
                logger.info(f"🚫 User '{user_role}' cannot access files via agent '{agent_id}' (not authorized)")
            
        return can_access
    
    @classmethod
    def get_user_permissions_summary(cls, user_role: str) -> Dict[str, any]:
        """
        Get a summary of what the user can access through their companion agent
        
        Args:
            user_role: The user's role
            
        Returns:
            Dictionary with user's permissions and companion info
        """
        companion = cls.get_user_companion_agent(user_role)
        
        if not companion:
            return {
                "user_role": user_role,
                "has_companion": False,
                "companion_agent": None,
                "calendar_access": False,
                "file_access": False
            }
        
        return {
            "user_role": user_role,
            "has_companion": True,
            "companion_agent": companion,
            "calendar_access": companion in cls.CALENDAR_ENABLED_AGENTS,
            "file_access": companion in cls.FILE_ENABLED_AGENTS
        }

# Global instance for easy import
user_agent_matcher = UserAgentMatcher()