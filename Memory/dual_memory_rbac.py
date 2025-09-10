"""
Dual Memory RBAC System
Implements public and private memory collections with role-based access control.
Integrates with Google Drive folder structure and permissions.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    from Memory.Vector_store import VectorStoreManager
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Memory.Vector_store import VectorStoreManager
from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager
from Integrations.Google.Gmail.gmail_auth import GmailAuthService
from Integrations.Google.Gmail.gmail_database import gmail_database
from Auth.User_management.user_models import User, AgentType
from Utils.config import Config

logger = logging.getLogger(__name__)

class AccessType(Enum):
    """Types of access for memory and drive operations"""
    READ = "read"
    WRITE = "write"
    FULL = "full"

class MemoryType(Enum):
    """Types of memory collections"""
    PUBLIC = "public"
    PRIVATE = "private"

@dataclass
class DepartmentMapping:
    """Maps departments to their configuration"""
    name: str
    display_name: str
    public_collection: str
    drive_folder: str
    agents: List[str]

@dataclass
class AgentMapping:
    """Maps agents to their configuration"""
    name: str
    department: str
    public_collection: str
    private_collection: str
    private_drive_folder: str

class DualMemoryRBACManager:
    """Manages dual memory system with role-based access control"""
    
    # Department mappings as specified in the requirements
    DEPARTMENT_MAPPINGS = {
        "Executive": DepartmentMapping(
            name="Executive",
            display_name="Executive",
            public_collection="public_executive",
            drive_folder="Executive",
            agents=["cmo"]
        ),
        "Business Development": DepartmentMapping(
            name="Business Development", 
            display_name="Business Development",
            public_collection="public_business_development",
            drive_folder="Business Development",
            agents=["ipm", "bdm", "presales_engineer"]
        ),
        "Operations": DepartmentMapping(
            name="Operations",
            display_name="Operations", 
            public_collection="public_operations",
            drive_folder="Operations",
            agents=[
                "head_of_operations", "senior_csm", "senior_delivery_consultant",
                "delivery_consultant_en", "delivery_consultant_bg", "delivery_consultant_hu",
                "legal", "reporting_manager", "reporting_specialist"
            ]
        ),
        "Marketing": DepartmentMapping(
            name="Marketing",
            display_name="Marketing",
            public_collection="public_marketing", 
            drive_folder="Marketing",
            agents=["content", "seo", "analytics", "brand", "social", "community", "positioning", "persona", "gtm", "competitor", "launch", "funnel", "landing", "sem"]
        )
    }
    
    # Agent to department mapping for easy lookup
    AGENT_DEPARTMENT_MAP = {}
    for dept_name, dept_config in DEPARTMENT_MAPPINGS.items():
        for agent in dept_config.agents:
            AGENT_DEPARTMENT_MAP[agent] = dept_name
    
    def __init__(self, lazy_init: bool = True):
        """Initialize the dual memory RBAC manager"""
        self.lazy_init = lazy_init
        self.vector_store = None
        self.gmail_auth_service = GmailAuthService()
        
        # Cache for drive services per user
        self._drive_services_cache = {}
        
        # Cache for access decisions
        self._access_cache = {}
        
        # Initialize vector store if not lazy loading
        if not lazy_init:
            self._initialize_vector_store()
    
    def _initialize_vector_store(self) -> bool:
        """Initialize the vector store connection"""
        if self.vector_store is not None:
            return True
            
        try:
            memory_config = Config.get_memory_config()
            self.vector_store = VectorStoreManager(
                host=memory_config["qdrant_host"],
                port=memory_config["qdrant_port"],
                api_key=memory_config.get("qdrant_api_key"),
                embedding_model=memory_config["embedding_model"],
                lazy_load=True
            )
            
            if self.vector_store.is_available():
                logger.info("✅ Dual memory RBAC system initialized with Qdrant")
                return True
            else:
                logger.warning("⚠️ Qdrant not available for dual memory system")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    def _get_user_drive_service(self, user_id: str):
        """Get Google Drive service using user's OAuth tokens"""
        if user_id in self._drive_services_cache:
            return self._drive_services_cache[user_id]
            
        try:
            from googleapiclient.discovery import build
            
            # Get Gmail OAuth tokens for this user
            token_data = gmail_database.get_gmail_tokens(user_id)
            if not token_data:
                logger.warning(f"No Gmail tokens found for user {user_id}")
                return None
            
            # Get credentials
            credentials = self.gmail_auth_service.get_credentials(token_data)
            if not credentials:
                logger.warning(f"Failed to get valid credentials for user {user_id}")
                return None
            
            # Build Google Drive service
            drive_service = build('drive', 'v3', credentials=credentials)
            self._drive_services_cache[user_id] = drive_service
            
            logger.info(f"Google Drive service initialized for user {user_id}")
            return drive_service
            
        except Exception as e:
            logger.error(f"Error getting Drive service for user {user_id}: {e}")
            return None
    
    def get_agent_department(self, agent_name: str) -> Optional[str]:
        """Get department for a given agent"""
        return self.AGENT_DEPARTMENT_MAP.get(agent_name)
    
    def get_public_collection_name(self, department: str) -> str:
        """Get public collection name for a department"""
        dept_config = self.DEPARTMENT_MAPPINGS.get(department)
        return dept_config.public_collection if dept_config else f"public_{department.lower().replace(' ', '_')}"
    
    def get_private_collection_name(self, agent_name: str) -> str:
        """Get private collection name for an agent"""
        return f"private_{agent_name}"
    
    def get_private_drive_folder_name(self, agent_name: str) -> str:
        """Get private Drive folder name for an agent"""
        return f"{agent_name}_private"
    
    def validate_memory_access(self, user: User, collection_name: str, access_type: AccessType) -> bool:
        """Validate if user has access to a memory collection"""
        cache_key = f"{user.id}:{collection_name}:{access_type.value}"
        if cache_key in self._access_cache:
            return self._access_cache[cache_key]
        
        # Determine if this is a public or private collection
        is_private = collection_name.startswith("private_")
        is_public = collection_name.startswith("public_")
        
        if is_private:
            # Extract agent name from private collection
            agent_name = collection_name[8:]  # Remove "private_" prefix
            result = self._validate_private_memory_access(user, agent_name, access_type)
        elif is_public:
            # Extract department from public collection
            dept_name = collection_name[7:]  # Remove "public_" prefix
            result = self._validate_public_memory_access(user, dept_name, access_type)
        else:
            # Legacy or unknown collection - deny access
            logger.warning(f"Unknown collection type: {collection_name}")
            result = False
        
        # Cache the result
        self._access_cache[cache_key] = result
        self._log_access_decision(user, collection_name, access_type, result)
        
        return result
    
    def _validate_private_memory_access(self, user: User, agent_name: str, access_type: AccessType) -> bool:
        """Validate access to private agent memory"""
        # Agent runtime always has full access (in practice this would be validated differently)
        # For now, we assume if user has agent assignment, they are the "agent runtime"
        
        # Check if user has assignment to this specific agent
        # Handle different agent name formats (e.g., "bdm_agent" vs "bdm")
        for assignment in user.agent_assignments:
            agent_type_name = assignment.agent_type.value.lower()
            
            # Try exact match first
            if agent_type_name == agent_name.lower():
                return True
                
            # Try with "_agent" suffix
            if f"{agent_type_name}_agent" == agent_name.lower():
                return True
                
            # Try removing "_agent" suffix from agent_name
            if agent_name.lower().endswith("_agent"):
                base_name = agent_name.lower()[:-6]  # Remove "_agent"
                if agent_type_name == base_name:
                    return True
        
        # Check if this is the assigned owner with sharing enabled
        # This would require additional user metadata to track share_private_with_owner setting
        if self._is_assigned_owner_with_sharing(user, agent_name):
            return True
        
        return False
    
    def _validate_public_memory_access(self, user: User, department: str, access_type: AccessType) -> bool:
        """Validate access to public department memory"""
        # Get department name from collection name
        dept_mapping = None
        for dept_name, config in self.DEPARTMENT_MAPPINGS.items():
            if config.public_collection == f"public_{department}":
                dept_mapping = config
                break
        
        if not dept_mapping:
            return False
        
        # Check if user has any agent assignment in this department
        for assignment in user.agent_assignments:
            agent_type_name = assignment.agent_type.value.lower()
            
            # Check if this agent belongs to this department
            agent_in_dept = False
            for dept_agent in dept_mapping.agents:
                dept_agent_lower = dept_agent.lower()
                
                # Try exact match
                if agent_type_name == dept_agent_lower:
                    agent_in_dept = True
                    break
                    
                # Try with "_agent" suffix
                if f"{agent_type_name}_agent" == dept_agent_lower:
                    agent_in_dept = True
                    break
                    
                # Try removing "_agent" suffix from dept_agent
                if dept_agent_lower.endswith("_agent"):
                    base_name = dept_agent_lower[:-6]  # Remove "_agent"
                    if agent_type_name == base_name:
                        agent_in_dept = True
                        break
            
            if agent_in_dept:
                # Has agent in department - check access type
                if access_type == AccessType.READ:
                    # All department members can read public memory
                    return True
                elif access_type == AccessType.WRITE:
                    # Check if user has write access to this department's memory
                    # Be flexible with collection name matching
                    collection_name = dept_mapping.public_collection
                    if assignment.has_memory_write_access(collection_name):
                        return True
                    
                    # Also check alternative naming patterns
                    alt_names = [
                        f"public_{department}",
                        f"{department.lower().replace(' ', '_')}-shared-memory",
                        f"{department.lower().replace(' ', '_')}_shared_memory"
                    ]
                    
                    for alt_name in alt_names:
                        if assignment.has_memory_write_access(alt_name):
                            return True
                            
                elif access_type == AccessType.FULL:
                    # Full access requires write permission
                    collection_name = dept_mapping.public_collection
                    return assignment.has_memory_write_access(collection_name)
        
        return False
    
    def _is_assigned_owner_with_sharing(self, user: User, agent_name: str) -> bool:
        """Check if user is assigned owner with private sharing enabled"""
        # This would check user metadata for share_private_with_owner setting
        # For now, return False - this feature needs to be implemented with user preferences
        return False
    
    def _log_access_decision(self, user: User, resource: str, access_type: AccessType, granted: bool):
        """Log access decisions for audit purposes"""
        status = "GRANTED" if granted else "DENIED"
        logger.info(f"ACCESS {status}: user={user.username} resource={resource} type={access_type.value}")
    
    def ensure_collections_exist(self) -> bool:
        """Ensure all required public and private collections exist"""
        if not self._initialize_vector_store():
            return False
        
        success_count = 0
        total_collections = 0
        
        # Create public collections for all departments
        for dept_name, dept_config in self.DEPARTMENT_MAPPINGS.items():
            total_collections += 1
            if self.vector_store.create_collection(dept_config.public_collection):
                success_count += 1
                logger.info(f"Ensured public collection: {dept_config.public_collection}")
        
        # Create private collections for all agents
        for dept_config in self.DEPARTMENT_MAPPINGS.values():
            for agent_name in dept_config.agents:
                total_collections += 1
                private_collection = self.get_private_collection_name(agent_name)
                if self.vector_store.create_collection(private_collection):
                    success_count += 1
                    logger.info(f"Ensured private collection: {private_collection}")
        
        logger.info(f"Collection setup: {success_count}/{total_collections} successful")
        return success_count == total_collections
    
    def add_memory(self, user: User, agent_name: str, memory_type: MemoryType, 
                  memory_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add memory to appropriate collection with access control"""
        if not self._initialize_vector_store():
            return False
        
        # Determine target collection
        if memory_type == MemoryType.PUBLIC:
            department = self.get_agent_department(agent_name)
            if not department:
                logger.error(f"Unknown department for agent: {agent_name}")
                return False
            collection_name = self.get_public_collection_name(department)
        else:  # PRIVATE
            collection_name = self.get_private_collection_name(agent_name)
        
        # Validate write access
        if not self.validate_memory_access(user, collection_name, AccessType.WRITE):
            logger.warning(f"User {user.username} denied write access to {collection_name}")
            return False
        
        # Add metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "agent_name": agent_name,
            "memory_type": memory_type.value,
            "department": self.get_agent_department(agent_name),
            "created_by": user.id,
            "created_at": datetime.now().isoformat()
        })
        
        # Add to vector store
        success = self.vector_store.add_document(
            collection_name=collection_name,
            document_id=memory_id,
            text=content,
            metadata=metadata
        )
        
        if success:
            logger.info(f"Added {memory_type.value} memory {memory_id} for agent {agent_name}")
        
        return success
    
    def search_memory(self, user: User, agent_name: str, memory_type: MemoryType,
                     query: str, limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search memory with access control"""
        if not self._initialize_vector_store():
            return []
        
        # Determine target collection
        if memory_type == MemoryType.PUBLIC:
            department = self.get_agent_department(agent_name)
            if not department:
                logger.error(f"Unknown department for agent: {agent_name}")
                return []
            collection_name = self.get_public_collection_name(department)
        else:  # PRIVATE
            collection_name = self.get_private_collection_name(agent_name)
        
        # Validate read access
        if not self.validate_memory_access(user, collection_name, AccessType.READ):
            logger.warning(f"User {user.username} denied read access to {collection_name}")
            return []
        
        # Search in vector store
        results = self.vector_store.search_similar(
            collection_name=collection_name,
            query_text=query,
            limit=limit,
            score_threshold=score_threshold
        )
        
        logger.info(f"Found {len(results)} {memory_type.value} memories for agent {agent_name}")
        return results
    
    def get_accessible_collections(self, user: User) -> Dict[str, List[str]]:
        """Get all collections user can access, organized by access type"""
        accessible = {
            "read": [],
            "write": [],
            "full": []
        }
        
        # Check all public collections
        for dept_config in self.DEPARTMENT_MAPPINGS.values():
            collection = dept_config.public_collection
            if self.validate_memory_access(user, collection, AccessType.READ):
                accessible["read"].append(collection)
            if self.validate_memory_access(user, collection, AccessType.WRITE):
                accessible["write"].append(collection)
                accessible["full"].append(collection)
        
        # Check all private collections for user's agents
        for assignment in user.agent_assignments:
            agent_name = assignment.agent_type.value
            collection = self.get_private_collection_name(agent_name)
            if self.validate_memory_access(user, collection, AccessType.READ):
                accessible["read"].append(collection)
            if self.validate_memory_access(user, collection, AccessType.WRITE):
                accessible["write"].append(collection)
                accessible["full"].append(collection)
        
        return accessible
