"""
Enhanced Memory Manager for agent memory operations
"""

import logging
from typing import Dict, List, Optional, Any
import os
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class EnhancedMemoryManager:
    """Enhanced memory manager for agents with vector search capabilities"""
    
    def __init__(self, agent_name: str, collection_name: str, lazy_init: bool = True):
        self.agent_name = agent_name
        self.collection_name = collection_name
        self.lazy_init = lazy_init
        
        # Initialize as None - will be loaded on first use
        self.vector_store = None
        self.available = False
        
        # Memory cache for frequently accessed items
        self._memory_cache = {}
        self._cache_max_size = 100
        
        # Initialize immediately if not lazy
        if not lazy_init:
            self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize vector store with error handling"""
        if self.vector_store is not None:
            return self.available
        
        try:
            try:
                from Memory.Vector_store.vector_store import VectorStoreManager
            except ImportError:
                # Fallback imports with path adjustment
                import sys
                from pathlib import Path
                project_root = str(Path(__file__).parent.parent.parent)
                if project_root not in sys.path:
                    sys.path.append(project_root)
                
                from Memory.Vector_store.vector_store import VectorStoreManager
            from Utils.config import Config
            
            # Get memory configuration
            memory_config = Config.get_memory_config()
            
            # Initialize vector store with lazy loading
            self.vector_store = VectorStoreManager(
                host=memory_config["qdrant_host"],
                port=memory_config["qdrant_port"],
                api_key=memory_config.get("qdrant_api_key"),
                embedding_model=memory_config["embedding_model"],
                lazy_load=True
            )
            
            # Check if vector store is available
            self.available = self.vector_store.is_available()
            
            if self.available:
                # Ensure collection exists
                self._ensure_collection_exists() 
                logger.info(f"✅ Memory system initialized for {self.agent_name}")
            else:
                logger.info(f"⚠️ Memory system not available for {self.agent_name} (operating without memory)")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize memory for {self.agent_name}: {str(e)}")
            self.available = False
        
        return self.available
    
    def _ensure_collection_exists(self):
        """Ensure the agent's collection exists in Qdrant"""
        if not self.available or not self.vector_store:
            return
        
        try:
            self.vector_store.create_collection(self.collection_name)
            logger.debug(f"Ensured collection {self.collection_name} exists for {self.agent_name}")
        except Exception as e:
            logger.warning(f"Could not ensure collection exists: {str(e)}")
    
    def _ensure_initialized(self) -> bool:
        """Ensure vector store is initialized before use"""
        if self.vector_store is None:
            return self._initialize_vector_store()
        return self.available
    
    async def add_memory(self, memory_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a memory to the agent's collection"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return False
                
            if metadata is None:
                metadata = {}
            
            # Add agent-specific metadata
            metadata.update({
                "agent_name": self.agent_name,
                "collection": self.collection_name,
                "memory_type": metadata.get("memory_type", "general")
            })
            
            # Add to vector store
            success = self.vector_store.add_document(
                collection_name=self.collection_name,
                document_id=memory_id,
                text=content,
                metadata=metadata
            )
            
            if success:
                # Update cache
                self._update_cache(memory_id, {"content": content, "metadata": metadata})
                logger.info(f"Added memory {memory_id} for agent {self.agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding memory {memory_id}: {str(e)}")
            return False
    
    async def search_memories(self, query: str, limit: int = 5, score_threshold: float = 0.7,
                            memory_type: str = None) -> List[Dict[str, Any]]:
        """Search for relevant memories"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return []
            
            # Search in vector store
            results = self.vector_store.search_similar(
                collection_name=self.collection_name,
                query_text=query,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Filter by memory type if specified
            if memory_type:
                results = [r for r in results if r.get("metadata", {}).get("memory_type") == memory_type]
            
            logger.info(f"Found {len(results)} relevant memories for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            return []
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID"""
        try:
            # Check cache first
            if memory_id in self._memory_cache:
                return self._memory_cache[memory_id]
            
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return None
            
            # Get from vector store
            result = self.vector_store.get_document(
                collection_name=self.collection_name,
                document_id=memory_id
            )
            
            if result:
                # Update cache
                self._update_cache(memory_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting memory {memory_id}: {str(e)}")
            return None
    
    async def update_memory(self, memory_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Update an existing memory"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return False
                
            if metadata is None:
                metadata = {}
            
            # Add agent-specific metadata
            metadata.update({
                "agent_name": self.agent_name,
                "collection": self.collection_name,
                "memory_type": metadata.get("memory_type", "general")
            })
            
            # Update in vector store
            success = self.vector_store.update_document(
                collection_name=self.collection_name,
                document_id=memory_id,
                text=content,
                metadata=metadata
            )
            
            if success:
                # Update cache
                self._update_cache(memory_id, {"content": content, "metadata": metadata})
                # Remove from cache to force refresh on next access
                if memory_id in self._memory_cache:
                    del self._memory_cache[memory_id]
                
                logger.info(f"Updated memory {memory_id} for agent {self.agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {str(e)}")
            return False
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return False
                
            # Delete from vector store
            success = self.vector_store.delete_document(
                collection_name=self.collection_name,
                document_id=memory_id
            )
            
            if success:
                # Remove from cache
                if memory_id in self._memory_cache:
                    del self._memory_cache[memory_id]
                
                logger.info(f"Deleted memory {memory_id} for agent {self.agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {str(e)}")
            return False
    
    async def get_memories_by_type(self, memory_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories by type"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return []
                
            results = self.vector_store.search_by_metadata(
                collection_name=self.collection_name,
                metadata_filter={"memory_type": memory_type},
                limit=limit
            )
            
            logger.info(f"Found {len(results)} memories of type {memory_type}")
            return results
            
        except Exception as e:
            logger.error(f"Error getting memories by type {memory_type}: {str(e)}")
            return []
    
    async def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memories (requires timestamp in metadata)"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return []
                
            # This is a simplified version - in practice, you'd want to sort by timestamp
            results = self.vector_store.search_by_metadata(
                collection_name=self.collection_name,
                metadata_filter={"agent_name": self.agent_name},
                limit=limit
            )
            
            logger.info(f"Retrieved {len(results)} recent memories")
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent memories: {str(e)}")
            return []
    
    async def clear_all_memories(self) -> bool:
        """Clear all memories for this agent (use with caution)"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return False
                
            # Delete and recreate the collection
            self.vector_store.delete_collection(self.collection_name)
            success = self.vector_store.create_collection(self.collection_name)
            
            if success:
                # Clear cache
                self._memory_cache.clear()
                logger.warning(f"Cleared all memories for agent {self.agent_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error clearing memories: {str(e)}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for this agent"""
        try:
            # Ensure vector store is initialized
            if not self._ensure_initialized():
                return {
                    "agent_name": self.agent_name,
                    "collection_name": self.collection_name,
                    "total_memories": 0,
                    "cache_size": len(self._memory_cache),
                    "cache_max_size": self._cache_max_size,
                    "status": "not_initialized"
                }
                
            collection_info = self.vector_store.get_collection_info(self.collection_name)
            
            return {
                "agent_name": self.agent_name,
                "collection_name": self.collection_name,
                "total_memories": collection_info.get("points_count", 0) if collection_info else 0,
                "cache_size": len(self._memory_cache),
                "cache_max_size": self._cache_max_size,
                "status": "initialized"
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {str(e)}")
            return {
                "agent_name": self.agent_name,
                "collection_name": self.collection_name,
                "total_memories": 0,
                "cache_size": len(self._memory_cache),
                "cache_max_size": self._cache_max_size,
                "status": "error"
            }
    
    def _update_cache(self, memory_id: str, data: Dict[str, Any]):
        """Update the memory cache with size limit"""
        # Remove oldest item if cache is full
        if len(self._memory_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        
        self._memory_cache[memory_id] = data
    
    async def add_task_memory(self, task_id: str, task_description: str, result: str, 
                            success: bool = True) -> bool:
        """Add task-specific memory"""
        metadata = {
            "memory_type": "task",
            "task_id": task_id,
            "success": success,
            "task_description": task_description
        }
        
        memory_content = f"Task: {task_description}\nResult: {result}\nSuccess: {success}"
        memory_id = f"task_{task_id}"
        
        return await self.add_memory(memory_id, memory_content, metadata)
    
    async def add_interaction_memory(self, interaction_type: str, context: str, 
                                   outcome: str) -> bool:
        """Add interaction-specific memory"""
        import time
        
        metadata = {
            "memory_type": "interaction",
            "interaction_type": interaction_type,
            "timestamp": int(time.time())
        }
        
        memory_content = f"Interaction: {interaction_type}\nContext: {context}\nOutcome: {outcome}"
        memory_id = f"interaction_{int(time.time())}_{interaction_type}"
        
        return await self.add_memory(memory_id, memory_content, metadata)
    
    async def get_relevant_context(self, current_task: str, max_memories: int = 3) -> str:
        """Get relevant context for current task from memory"""
        try:
            # Check if this agent has multi-collection access (CMO)
            if hasattr(self, 'accessible_collections') and len(self.accessible_collections) > 1:
                # Multi-collection search for CMO
                logger.info(f"Performing multi-collection search across {len(self.accessible_collections)} collections")
                all_memories = []
                
                for collection in self.accessible_collections:
                    try:
                        # Create temporary memory manager for each collection
                        temp_manager = EnhancedMemoryManager(
                            agent_name=f"{self.agent_name}_temp",
                            collection_name=collection
                        )
                        
                        # Search in this collection
                        memories = await temp_manager.search_memories(
                            query=current_task,
                            limit=max_memories,
                            score_threshold=0.4  # Lower threshold for broader search
                        )
                        
                        # Add collection info to metadata
                        for memory in memories:
                            if 'metadata' not in memory:
                                memory['metadata'] = {}
                            memory['metadata']['source_collection'] = collection
                        
                        all_memories.extend(memories)
                        
                    except Exception as e:
                        logger.warning(f"Failed to search collection {collection}: {e}")
                
                # Sort by score and take top results
                all_memories.sort(key=lambda x: x.get('score', 0), reverse=True)
                relevant_memories = all_memories[:max_memories]
                
                logger.info(f"Multi-collection search found {len(relevant_memories)} relevant memories")
                
            else:
                # Single collection search for regular agents
                relevant_memories = await self.search_memories(
                    query=current_task,
                    limit=max_memories,
                    score_threshold=0.4  # Lowered threshold to include more relevant content
                )
            
            if not relevant_memories:
                return ""
            
            # Format context
            context_parts = []
            for memory in relevant_memories:
                memory_type = memory.get("metadata", {}).get("memory_type", "general")
                source_collection = memory.get("metadata", {}).get("source_collection", self.collection_name)
                content = memory.get("text", "")[:2000]  # Increased limit for better context
                
                # Add collection info for multi-collection results
                if hasattr(self, 'accessible_collections') and len(self.accessible_collections) > 1:
                    context_parts.append(f"[{memory_type.upper()}] [{source_collection.upper()}] {content}")
                else:
                    context_parts.append(f"[{memory_type.upper()}] {content}")
            
            context = "\n\n".join(context_parts)
            logger.info(f"Retrieved relevant context with {len(relevant_memories)} memories")
            
            return f"RELEVANT MEMORY CONTEXT:\n{context}\n\n"
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {str(e)}")
            return "" 