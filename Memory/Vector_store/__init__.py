"""
Vector Store Operations
Handles vector storage and retrieval for semantic search
"""

try:
    from Memory.Vector_store.vector_store import VectorStoreManager
    from Memory.Vector_store.enhanced_vector_store import *
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Memory.Vector_store.vector_store import VectorStoreManager
    from Memory.Vector_store.enhanced_vector_store import *
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager

__all__ = ['VectorStoreManager', 'EnhancedMemoryManager']
