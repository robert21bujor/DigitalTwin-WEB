"""
Memory system for the AI Company System
Handles vector storage, Google Drive sync, and agent memory.
Includes dual memory RBAC system with public/private collections.
"""

from .Vector_store import EnhancedMemoryManager
# Google Drive components moved to Integrations.Google.Drive
try:
    from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager
except ImportError:
    # Fallback during migration
    GoogleDriveManager = None
from .Vector_store import VectorStoreManager
from .dual_memory_rbac import DualMemoryRBACManager, MemoryType, AccessType
try:
    from Integrations.Google.Drive.gdrive_rbac_manager import GoogleDriveRBACManager
except ImportError:
    # Fallback during migration
    GoogleDriveRBACManager = None
from .unified_rbac_service import (
    UnifiedRBACService,
    get_unified_rbac_service,
    initialize_unified_rbac_service
)

__all__ = [
    'EnhancedMemoryManager',
    'GoogleDriveManager', 
    'VectorStoreManager',
    'DualMemoryRBACManager',
    'GoogleDriveRBACManager',
    'UnifiedRBACService',
    'get_unified_rbac_service',
    'initialize_unified_rbac_service',
    'MemoryType',
    'AccessType'
] 