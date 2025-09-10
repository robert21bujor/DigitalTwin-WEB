"""
Agent Memory Interface
====================

Role-based memory interface for agents to retrieve relevant knowledge.
Integrates with existing Google Drive and vector store systems.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
from datetime import datetime

from .schemas import MessageIntent, AgentCommError

# Type-only imports for annotations
if TYPE_CHECKING:
    from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager
    from Memory.Vector_store.vector_store import VectorStore
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager

# Runtime imports with fallback
try:
    from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager as _GoogleDriveManager
    from Memory.Vector_store.vector_store import VectorStore as _VectorStore
    from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager as _EnhancedMemoryManager
    MEMORY_SYSTEMS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Memory system imports not available: {e}")
    _GoogleDriveManager = None
    _VectorStore = None
    _EnhancedMemoryManager = None
    MEMORY_SYSTEMS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class AgentMemoryInterface:
    """
    Memory interface for agent-specific knowledge retrieval
    
    Features:
    - Role-based memory access
    - Intent-specific knowledge retrieval
    - Integration with existing Google Drive and vector store
    - Contextual search and filtering
    - Memory caching and optimization
    """
    
    def __init__(
        self,
        gdrive_config_path: Optional[str] = "Memory/Config/gdrive_config.json",
        vector_store_url: str = "http://localhost:6333",
        enable_gdrive: bool = True,
        enable_vector_store: bool = True,
        cache_ttl: int = 300
    ):
        """
        Initialize agent memory interface
        
        Args:
            gdrive_config_path: Path to Google Drive configuration
            vector_store_url: Vector store (Qdrant) URL
            enable_gdrive: Whether to enable Google Drive integration
            enable_vector_store: Whether to enable vector store
            cache_ttl: Cache time-to-live in seconds
        """
        self.gdrive_config_path = gdrive_config_path
        self.vector_store_url = vector_store_url
        self.enable_gdrive = enable_gdrive
        self.enable_vector_store = enable_vector_store
        self.cache_ttl = cache_ttl
        
        # Memory system components
        self._gdrive_manager: Optional['GoogleDriveManager'] = None
        self._vector_store: Optional['VectorStore'] = None
        self._memory_managers: Dict[str, Any] = {}  # agent_id -> EnhancedMemoryManager
        
        # Caching
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        
        # Role-based memory access permissions
        self._role_permissions = self._initialize_role_permissions()
        
        logger.info("AgentMemoryInterface initialized")
    
    async def initialize(self) -> None:
        """Initialize memory systems"""
        try:
            # Initialize Google Drive if available and enabled
            if self.enable_gdrive and _GoogleDriveManager:
                try:
                    self._gdrive_manager = _GoogleDriveManager(self.gdrive_config_path)
                    # Test connection
                    if self._gdrive_manager.test_connection():
                        logger.info("Google Drive integration initialized")
                    else:
                        logger.warning("Google Drive connection test failed")
                        self._gdrive_manager = None
                except Exception as e:
                    logger.warning(f"Google Drive initialization failed: {e}")
                    self._gdrive_manager = None
            
            # Initialize Vector Store if available and enabled
            if self.enable_vector_store and _VectorStore:
                try:
                    self._vector_store = _VectorStore(
                        url=self.vector_store_url,
                        collection_name="agent_knowledge"
                    )
                    # Test connection
                    if self._vector_store.test_connection():
                        logger.info("Vector store integration initialized")
                    else:
                        logger.warning("Vector store connection test failed")
                        self._vector_store = None
                except Exception as e:
                    logger.warning(f"Vector store initialization failed: {e}")
                    self._vector_store = None
            
            logger.info("AgentMemoryInterface initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory interface: {e}")
            raise AgentCommError(f"Memory interface initialization failed: {e}")
    
    async def get_agent_memory_manager(self, agent_id: str, role: str) -> Optional[Any]:
        """
        Get or create memory manager for a specific agent
        
        Args:
            agent_id: Agent identifier
            role: Agent role for permission-based access
            
        Returns:
            EnhancedMemoryManager instance or None
        """
        if agent_id in self._memory_managers:
            return self._memory_managers[agent_id]
        
        if not _EnhancedMemoryManager:
            logger.warning("EnhancedMemoryManager not available")
            return None
        
        try:
            # Determine collection name based on role
            collection_name = self._get_collection_for_role(role)
            
            # Create memory manager for this agent
            memory_manager = _EnhancedMemoryManager(
                agent_name=agent_id,
                collection_name=collection_name
            )
            
            # Initialize the memory manager
            await memory_manager.initialize()
            
            self._memory_managers[agent_id] = memory_manager
            logger.info(f"Created memory manager for agent {agent_id} with collection {collection_name}")
            
            return memory_manager
            
        except Exception as e:
            logger.error(f"Failed to create memory manager for {agent_id}: {e}")
            return None
    
    async def search_knowledge(
        self,
        agent_id: str,
        role: str,
        query: str,
        intent: Optional[MessageIntent] = None,
        context: Optional[Dict[str, Any]] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant knowledge based on agent role and query
        
        Args:
            agent_id: Agent making the request
            role: Agent role for permission filtering
            query: Search query
            intent: Message intent for context
            context: Additional context information
            max_results: Maximum number of results to return
            
        Returns:
            List of knowledge items with relevance scores
        """
        try:
            # Check cache first
            cache_key = f"{agent_id}:{role}:{query}:{intent}"
            if cache_key in self._search_cache:
                cached_result = self._search_cache[cache_key]
                if (datetime.now() - cached_result["timestamp"]).seconds < self.cache_ttl:
                    logger.debug(f"Returning cached search results for {agent_id}")
                    return cached_result["results"]
            
            results = []
            
            # Search vector store if available
            if self._vector_store:
                vector_results = await self._search_vector_store(
                    agent_id, role, query, intent, context, max_results
                )
                results.extend(vector_results)
            
            # Search Google Drive if available
            if self._gdrive_manager:
                gdrive_results = await self._search_gdrive(
                    agent_id, role, query, intent, context, max_results
                )
                results.extend(gdrive_results)
            
            # Search agent-specific memory
            memory_manager = await self.get_agent_memory_manager(agent_id, role)
            if memory_manager:
                memory_results = await self._search_agent_memory(
                    memory_manager, query, intent, context, max_results
                )
                results.extend(memory_results)
            
            # Filter by role permissions
            filtered_results = self._filter_by_role_permissions(results, role)
            
            # Sort by relevance and limit results
            sorted_results = sorted(
                filtered_results,
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )[:max_results]
            
            # Cache results
            self._search_cache[cache_key] = {
                "results": sorted_results,
                "timestamp": datetime.now()
            }
            
            logger.debug(f"Found {len(sorted_results)} knowledge items for {agent_id}")
            return sorted_results
            
        except Exception as e:
            logger.error(f"Knowledge search failed for {agent_id}: {e}")
            return []
    
    async def store_knowledge(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store knowledge item for an agent
        
        Args:
            agent_id: Agent storing the knowledge
            role: Agent role for permission checking
            content: Knowledge content to store
            metadata: Additional metadata
            tags: Tags for categorization
            
        Returns:
            bool: True if storage successful
        """
        try:
            # Check write permissions
            if not self._check_write_permission(role):
                logger.warning(f"Agent {agent_id} with role {role} lacks write permission")
                return False
            
            # Get agent memory manager
            memory_manager = await self.get_agent_memory_manager(agent_id, role)
            if not memory_manager:
                logger.error(f"No memory manager available for {agent_id}")
                return False
            
            # Store in agent memory
            success = await memory_manager.add_memory(
                content=content,
                metadata=metadata or {},
                tags=tags or []
            )
            
            if success:
                logger.info(f"Stored knowledge for agent {agent_id}")
                # Clear related cache entries
                self._clear_agent_cache(agent_id)
                return True
            else:
                logger.error(f"Failed to store knowledge for agent {agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"Knowledge storage failed for {agent_id}: {e}")
            return False
    
    async def get_context_for_intent(
        self,
        agent_id: str,
        role: str,
        intent: MessageIntent,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get relevant context for a specific intent
        
        Args:
            agent_id: Agent requesting context
            role: Agent role
            intent: Message intent
            additional_context: Additional context information
            
        Returns:
            Dictionary with relevant context
        """
        try:
            # Define intent-specific search queries
            intent_queries = {
                MessageIntent.GET_ROADMAP: "roadmap strategic planning product development",
                MessageIntent.ASSIGN_TASK: "task management project assignment",
                MessageIntent.REQUEST_KNOWLEDGE: "knowledge base documentation",
                MessageIntent.SHARE_INSIGHTS: "insights analytics data findings",
                MessageIntent.REQUEST_REVIEW: "review process feedback approval",
                MessageIntent.SCHEDULE_MEETING: "calendar scheduling meetings availability"
            }
            
            query = intent_queries.get(intent, str(intent.value))
            
            # Search for relevant knowledge
            knowledge_items = await self.search_knowledge(
                agent_id=agent_id,
                role=role,
                query=query,
                intent=intent,
                context=additional_context,
                max_results=3
            )
            
            # Build context
            context = {
                "intent": intent.value,
                "agent_role": role,
                "knowledge_items": knowledge_items,
                "timestamp": datetime.now().isoformat()
            }
            
            if additional_context:
                context.update(additional_context)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context for intent {intent}: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    def _initialize_role_permissions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize role-based memory access permissions"""
        return {
            "cmo": {
                "read_collections": ["executive", "marketing", "sales", "product"],
                "write_collections": ["executive"],
                "can_access_sensitive": True
            },
            "marketing_manager": {
                "read_collections": ["marketing", "product"],
                "write_collections": ["marketing"],
                "can_access_sensitive": False
            },
            "content_agent": {
                "read_collections": ["marketing", "content"],
                "write_collections": ["content"],
                "can_access_sensitive": False
            },
            "seo_agent": {
                "read_collections": ["marketing", "seo"],
                "write_collections": ["seo"],
                "can_access_sensitive": False
            },
            "default": {
                "read_collections": ["general"],
                "write_collections": [],
                "can_access_sensitive": False
            }
        }
    
    def _get_collection_for_role(self, role: str) -> str:
        """Get appropriate memory collection for role"""
        role_collections = {
            "cmo": "executive-shared-memory",
            "marketing_manager": "marketing-shared-memory",
            "content_agent": "content-shared-memory",
            "seo_agent": "seo-shared-memory",
            "product_manager": "product-shared-memory"
        }
        return role_collections.get(role.lower(), "general-shared-memory")
    
    async def _search_vector_store(
        self,
        agent_id: str,
        role: str,
        query: str,
        intent: Optional[MessageIntent],
        context: Optional[Dict[str, Any]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search vector store for relevant knowledge"""
        try:
            if not self._vector_store:
                return []
            
            # Perform vector search
            search_results = await self._vector_store.search(
                query_text=query,
                limit=max_results,
                score_threshold=0.7
            )
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "source": "vector_store",
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "relevance_score": result.get("score", 0),
                    "type": "knowledge_item"
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector store search failed: {e}")
            return []
    
    async def _search_gdrive(
        self,
        agent_id: str,
        role: str,
        query: str,
        intent: Optional[MessageIntent],
        context: Optional[Dict[str, Any]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search Google Drive for relevant documents"""
        try:
            if not self._gdrive_manager:
                return []
            
            # Search Google Drive
            drive_results = self._gdrive_manager.search_documents(
                query=query,
                max_results=max_results
            )
            
            # Format results
            formatted_results = []
            for result in drive_results:
                formatted_results.append({
                    "source": "google_drive",
                    "content": result.get("content", ""),
                    "metadata": {
                        "file_name": result.get("name", ""),
                        "file_id": result.get("id", ""),
                        "modified_time": result.get("modifiedTime", ""),
                        "size": result.get("size", 0)
                    },
                    "relevance_score": 0.8,  # Default relevance for Drive results
                    "type": "document"
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Google Drive search failed: {e}")
            return []
    
    async def _search_agent_memory(
        self,
        memory_manager: Any,
        query: str,
        intent: Optional[MessageIntent],
        context: Optional[Dict[str, Any]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search agent-specific memory"""
        try:
            # Get relevant context from memory manager
            memory_context = await memory_manager.get_relevant_context(
                current_task=query,
                max_memories=max_results
            )
            
            if not memory_context:
                return []
            
            # Format as knowledge items
            return [{
                "source": "agent_memory",
                "content": memory_context,
                "metadata": {
                    "agent_specific": True,
                    "context_type": "memory"
                },
                "relevance_score": 0.9,  # High relevance for agent-specific memory
                "type": "memory_context"
            }]
            
        except Exception as e:
            logger.error(f"Agent memory search failed: {e}")
            return []
    
    def _filter_by_role_permissions(self, results: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
        """Filter results based on role permissions"""
        try:
            permissions = self._role_permissions.get(role.lower(), self._role_permissions["default"])
            read_collections = permissions.get("read_collections", [])
            can_access_sensitive = permissions.get("can_access_sensitive", False)
            
            filtered_results = []
            for result in results:
                # Check collection access
                metadata = result.get("metadata", {})
                collection = metadata.get("collection", "general")
                
                if collection in read_collections or "general" in read_collections:
                    # Check sensitivity
                    is_sensitive = metadata.get("sensitive", False)
                    if not is_sensitive or can_access_sensitive:
                        filtered_results.append(result)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Permission filtering failed: {e}")
            return results  # Return unfiltered results on error
    
    def _check_write_permission(self, role: str) -> bool:
        """Check if role has write permission"""
        permissions = self._role_permissions.get(role.lower(), self._role_permissions["default"])
        write_collections = permissions.get("write_collections", [])
        return len(write_collections) > 0
    
    def _clear_agent_cache(self, agent_id: str) -> None:
        """Clear cache entries for a specific agent"""
        keys_to_remove = [key for key in self._search_cache.keys() if key.startswith(f"{agent_id}:")]
        for key in keys_to_remove:
            del self._search_cache[key]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on memory systems"""
        status = {
            "status": "healthy",
            "components": {},
            "memory_managers": len(self._memory_managers),
            "cache_entries": len(self._search_cache)
        }
        
        # Check Google Drive
        if self._gdrive_manager:
            try:
                gdrive_status = self._gdrive_manager.test_connection()
                status["components"]["google_drive"] = "healthy" if gdrive_status else "unhealthy"
            except Exception as e:
                status["components"]["google_drive"] = f"error: {e}"
        else:
            status["components"]["google_drive"] = "disabled"
        
        # Check Vector Store
        if self._vector_store:
            try:
                vector_status = self._vector_store.test_connection()
                status["components"]["vector_store"] = "healthy" if vector_status else "unhealthy"
            except Exception as e:
                status["components"]["vector_store"] = f"error: {e}"
        else:
            status["components"]["vector_store"] = "disabled"
        
        # Overall status
        unhealthy_components = [k for k, v in status["components"].items() 
                             if v not in ["healthy", "disabled"]]
        if unhealthy_components:
            status["status"] = "degraded"
            status["unhealthy_components"] = unhealthy_components
        
        return status 