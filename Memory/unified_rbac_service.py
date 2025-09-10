"""
Unified RBAC Service
Provides a single interface for dual memory and Google Drive operations with access control.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

try:
    from Memory.dual_memory_rbac import DualMemoryRBACManager, MemoryType, AccessType
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Memory.dual_memory_rbac import DualMemoryRBACManager, MemoryType, AccessType
try:
    from Integrations.Google.Drive.gdrive_rbac_manager import GoogleDriveRBACManager
except ImportError:
    # Fallback during migration
    GoogleDriveRBACManager = None
from Auth.User_management.user_models import User

logger = logging.getLogger(__name__)

class UnifiedRBACService:
    """Unified service for memory and drive operations with role-based access control"""
    
    def __init__(self, lazy_init: bool = True):
        """Initialize the unified RBAC service"""
        self.memory_manager = DualMemoryRBACManager(lazy_init=lazy_init)
        self.drive_manager = GoogleDriveRBACManager()
        
        # Agent to department mapping from the memory manager
        self.agent_department_map = self.memory_manager.AGENT_DEPARTMENT_MAP
    
    def initialize_system(self, admin_user_id: str) -> Dict[str, Any]:
        """Initialize the complete dual memory + drive system"""
        results = {
            'collections_created': False,
            'drive_structure_created': False,
            'private_folders_created': False,
            'errors': []
        }
        
        try:
            # 1. Ensure all Qdrant collections exist
            logger.info("🔄 Creating Qdrant collections...")
            if self.memory_manager.ensure_collections_exist():
                results['collections_created'] = True
                logger.info("✅ All Qdrant collections created/verified")
            else:
                results['errors'].append("Failed to create some Qdrant collections")
            
            # 2. Setup Google Drive department structure
            logger.info("🔄 Setting up Google Drive department structure...")
            drive_results = self.drive_manager.setup_department_structure(admin_user_id)
            if len(drive_results) >= len(self.drive_manager.DEPARTMENT_FOLDERS):
                results['drive_structure_created'] = True
                results['drive_folders'] = drive_results
                logger.info("✅ Google Drive department structure created/verified")
            else:
                results['errors'].append("Failed to create some department folders")
            
            # 3. Setup private folders for all agents
            logger.info("🔄 Setting up agent private folders...")
            private_results = self.drive_manager.setup_agent_private_folders(
                admin_user_id, 
                self.agent_department_map
            )
            if len(private_results) >= len(self.agent_department_map):
                results['private_folders_created'] = True
                results['private_folders'] = private_results
                logger.info("✅ Agent private folders created/verified")
            else:
                results['errors'].append("Failed to create some private folders")
            
            # 4. Log summary
            success_count = sum([
                results['collections_created'],
                results['drive_structure_created'],
                results['private_folders_created']
            ])
            
            logger.info(f"🎯 System initialization: {success_count}/3 components successful")
            
            if success_count == 3:
                logger.info("🎉 Dual memory + Drive RBAC system fully initialized!")
            
            return results
            
        except Exception as e:
            logger.error(f"System initialization error: {e}")
            results['errors'].append(str(e))
            return results
    
    def add_public_memory(self, user: User, agent_name: str, memory_id: str, 
                         content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add memory to public department collection"""
        return self.memory_manager.add_memory(
            user=user,
            agent_name=agent_name,
            memory_type=MemoryType.PUBLIC,
            memory_id=memory_id,
            content=content,
            metadata=metadata
        )
    
    def add_private_memory(self, user: User, agent_name: str, memory_id: str,
                          content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add memory to private agent collection"""
        return self.memory_manager.add_memory(
            user=user,
            agent_name=agent_name,
            memory_type=MemoryType.PRIVATE,
            memory_id=memory_id,
            content=content,
            metadata=metadata
        )
    
    def search_public_memory(self, user: User, agent_name: str, query: str,
                           limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search public department memory"""
        return self.memory_manager.search_memory(
            user=user,
            agent_name=agent_name,
            memory_type=MemoryType.PUBLIC,
            query=query,
            limit=limit,
            score_threshold=score_threshold
        )
    
    def search_private_memory(self, user: User, agent_name: str, query: str,
                            limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search private agent memory"""
        return self.memory_manager.search_memory(
            user=user,
            agent_name=agent_name,
            memory_type=MemoryType.PRIVATE,
            query=query,
            limit=limit,
            score_threshold=score_threshold
        )
    
    def get_user_access_summary(self, user: User) -> Dict[str, Any]:
        """Get comprehensive access summary for a user"""
        summary = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role.value,
            'memory_access': self.memory_manager.get_accessible_collections(user),
            'departments': [],
            'agents': []
        }
        
        # Analyze department access
        for assignment in user.agent_assignments:
            agent_name = assignment.agent_type.value
            department = self.memory_manager.get_agent_department(agent_name)
            
            if department and department not in [d['name'] for d in summary['departments']]:
                # User has access to this department
                public_collection = self.memory_manager.get_public_collection_name(department)
                can_read = self.memory_manager.validate_memory_access(user, public_collection, AccessType.READ)
                can_write = self.memory_manager.validate_memory_access(user, public_collection, AccessType.WRITE)
                
                summary['departments'].append({
                    'name': department,
                    'public_collection': public_collection,
                    'can_read': can_read,
                    'can_write': can_write,
                    'drive_folder': self.drive_manager.DEPARTMENT_FOLDERS.get(department, department)
                })
            
            # Analyze agent access
            private_collection = self.memory_manager.get_private_collection_name(agent_name)
            can_read_private = self.memory_manager.validate_memory_access(user, private_collection, AccessType.READ)
            can_write_private = self.memory_manager.validate_memory_access(user, private_collection, AccessType.WRITE)
            
            summary['agents'].append({
                'name': agent_name,
                'department': department,
                'private_collection': private_collection,
                'private_drive_folder': self.memory_manager.get_private_drive_folder_name(agent_name),
                'can_read_private': can_read_private,
                'can_write_private': can_write_private,
                'access_level': assignment.access_level
            })
        
        return summary
    
    def verify_drive_access(self, user_id: str, folder_path: str) -> bool:
        """Verify if user has access to a specific Drive folder"""
        return self.drive_manager.verify_folder_access(user_id, folder_path)
    
    def setup_user_drive_structure(self, user_id: str) -> Dict[str, Any]:
        """Setup Drive structure for a specific user"""
        return self.drive_manager.setup_department_structure(user_id)
    
    def get_drive_structure(self, user_id: str) -> Dict[str, Any]:
        """Get current Drive folder structure for user"""
        return self.drive_manager.get_folder_structure(user_id)
    
    def validate_access(self, user: User, resource_type: str, resource_name: str, 
                       access_type: str) -> Tuple[bool, str]:
        """Unified access validation with detailed reasons"""
        try:
            if resource_type == "memory":
                access_enum = AccessType(access_type.lower())
                granted = self.memory_manager.validate_memory_access(user, resource_name, access_enum)
                reason = f"Memory access {access_type} for {resource_name}"
            elif resource_type == "drive":
                granted = self.verify_drive_access(user.id, resource_name)
                reason = f"Drive access for {resource_name}"
            else:
                granted = False
                reason = f"Unknown resource type: {resource_type}"
            
            status = "granted" if granted else "denied"
            return granted, f"{reason} - {status}"
            
        except Exception as e:
            logger.error(f"Access validation error: {e}")
            return False, f"Access validation failed: {str(e)}"
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'memory_system': {
                'available': False,
                'collections': 0,
                'errors': []
            },
            'drive_system': {
                'available': False,
                'errors': []
            },
            'overall_status': 'unknown'
        }
        
        try:
            # Check memory system
            if self.memory_manager._initialize_vector_store():
                health['memory_system']['available'] = True
                collections = self.memory_manager.vector_store.list_collections()
                health['memory_system']['collections'] = len(collections)
            
            # Check drive system (basic check)
            health['drive_system']['available'] = True  # If we can instantiate, it's available
            
            # Overall status
            if health['memory_system']['available'] and health['drive_system']['available']:
                health['overall_status'] = 'healthy'
            elif health['memory_system']['available'] or health['drive_system']['available']:
                health['overall_status'] = 'partial'
            else:
                health['overall_status'] = 'down'
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            health['memory_system']['errors'].append(str(e))
            health['drive_system']['errors'].append(str(e))
            health['overall_status'] = 'error'
        
        return health


# Global instance for easy access
unified_rbac_service = None

def get_unified_rbac_service(lazy_init: bool = True) -> UnifiedRBACService:
    """Get the global unified RBAC service instance"""
    global unified_rbac_service
    
    if unified_rbac_service is None:
        unified_rbac_service = UnifiedRBACService(lazy_init=lazy_init)
    
    return unified_rbac_service

def initialize_unified_rbac_service(admin_user_id: str, lazy_init: bool = True) -> Dict[str, Any]:
    """Initialize the unified RBAC service and setup the system"""
    service = get_unified_rbac_service(lazy_init=lazy_init)
    return service.initialize_system(admin_user_id)





