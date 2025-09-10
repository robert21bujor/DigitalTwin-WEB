"""
Vector Store Manager for Qdrant operations
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import json
from pathlib import Path
import threading

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

# Global model cache and lock for thread safety
_model_cache = {}
_model_lock = threading.Lock()

def get_embedding_model(model_name: str):
    """Get cached embedding model with thread-safe singleton pattern"""
    with _model_lock:
        if model_name not in _model_cache:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {model_name} (this may take a moment on first run)")
                _model_cache[model_name] = SentenceTransformer(model_name)
                logger.info(f"✅ Successfully loaded embedding model: {model_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load embedding model {model_name}: {str(e)}")
                _model_cache[model_name] = None
        
        return _model_cache[model_name]


class VectorStoreManager:
    """Manage Qdrant vector store operations with optimized loading"""
    
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None, 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2", lazy_load: bool = True):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.embedding_model_name = embedding_model
        self.lazy_load = lazy_load
        
        # Initialize Qdrant client with connection test
        self.client = None
        self.qdrant_available = False
        self._initialize_qdrant()
        
        # Lazy load embedding model only when needed
        self.embedding_model = None
        if not lazy_load:
            self._ensure_embedding_model()
    
    def _initialize_qdrant(self):
        """Initialize Qdrant client with error handling"""
        try:
            self.client = QdrantClient(host=self.host, port=self.port, api_key=self.api_key)
            # Quick connection test
            collections = self.client.get_collections()
            self.qdrant_available = True
            logger.info(f"✅ Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.warning(f"⚠️ Qdrant not available at {self.host}:{self.port}: {str(e)}")
            self.client = None
            self.qdrant_available = False
    
    def _ensure_embedding_model(self):
        """Ensure embedding model is loaded"""
        if self.embedding_model is None:
            self.embedding_model = get_embedding_model(self.embedding_model_name)
        return self.embedding_model is not None
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        return self.qdrant_available and self.client is not None
    
    def create_collection(self, collection_name: str, vector_size: int = 384) -> bool:
        """Create a new collection in Qdrant"""
        try:
            # Check if collection already exists
            collections = self.client.get_collections()
            if any(col.name == collection_name for col in collections.collections):
                logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            
            logger.info(f"Created collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {str(e)}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from Qdrant"""
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        # Ensure embedding model is loaded
        if not self._ensure_embedding_model():
            logger.error("Embedding model not available")
            return None
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    def add_document(self, collection_name: str, document_id: str, text: str, 
                    metadata: Dict[str, Any] = None) -> bool:
        """Add a document to the vector store"""
        try:
            # Check if vector store is available
            if not self.is_available():
                logger.warning("Vector store not available - skipping document addition")
                return False
                
            # Generate embedding for the text
            embedding = self.generate_embedding(text)
            if not embedding:
                return False
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "text": text,
                "document_id": document_id,
                "embedding_model": self.embedding_model_name
            })
            
            # Create point
            point = PointStruct(
                id=self._generate_point_id(document_id),
                vector=embedding,
                payload=metadata
            )
            
            # Insert point
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"Added document {document_id} to collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {document_id}: {str(e)}")
            return False
    
    def search_similar(self, collection_name: str, query_text: str, limit: int = 5, 
                      score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Check if vector store is available
            if not self.is_available():
                logger.warning("Vector store not available - returning empty results")
                return []
                
            # Generate embedding for query
            query_embedding = self.generate_embedding(query_text)
            if not query_embedding:
                return []
            
            # Search in Qdrant
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.payload.get("text", ""),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
                })
            
            logger.info(f"Found {len(results)} similar documents in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching in collection {collection_name}: {str(e)}")
            return []
    
    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            point_id = self._generate_point_id(document_id)
            
            points = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id]
            )
            
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k != "text"}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete a document from the vector store"""
        try:
            point_id = self._generate_point_id(document_id)
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=[point_id]
            )
            
            logger.info(f"Deleted document {document_id} from collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False
    
    def update_document(self, collection_name: str, document_id: str, text: str, 
                       metadata: Dict[str, Any] = None) -> bool:
        """Update an existing document"""
        # For now, we'll delete and re-add the document
        # This ensures the embedding is updated if the text changed
        self.delete_document(collection_name, document_id)
        return self.add_document(collection_name, document_id, text, metadata)
    
    def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
            
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a collection"""
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": info.config.dict() if info.config else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info for {collection_name}: {str(e)}")
            return None
    
    def search_by_metadata(self, collection_name: str, metadata_filter: Dict[str, Any], 
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata"""
        try:
            # Build filter conditions
            filter_conditions = []
            for key, value in metadata_filter.items():
                filter_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            
            # Search with filter
            search_result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(must=filter_conditions),
                limit=limit
            )
            
            # Format results
            results = []
            for point in search_result[0]:  # scroll returns (points, next_page_offset)
                results.append({
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k != "text"}
                })
            
            logger.info(f"Found {len(results)} documents matching metadata filter")
            return results
            
        except Exception as e:
            logger.error(f"Error searching by metadata: {str(e)}")
            return []
    
    def _generate_point_id(self, document_id: str) -> int:
        """Generate a consistent point ID from document ID"""
        # Use hash to convert string ID to integer
        return int(hashlib.md5(document_id.encode()).hexdigest(), 16) % (2**32)
    
    def test_connection(self) -> bool:
        """Test connection to Qdrant"""
        try:
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant, found {len(collections.collections)} collections")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def create_agent_collections(self, agent_mapping: Dict[str, tuple]) -> bool:
        """Create collections for all agents based on mapping"""
        try:
            success_count = 0
            
            for folder_name, (agent_name, collection_name, is_shared) in agent_mapping.items():
                if self.create_collection(collection_name):
                    success_count += 1
                    logger.info(f"Created collection {collection_name} for {agent_name}")
            
            logger.info(f"Successfully created {success_count} agent collections")
            return success_count == len(agent_mapping)
            
        except Exception as e:
            logger.error(f"Error creating agent collections: {str(e)}")
            return False 