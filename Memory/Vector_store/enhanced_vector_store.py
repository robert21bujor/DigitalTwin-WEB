"""
Enhanced Vector Store for Semantic File Search
Supports both FAISS (in-memory) and Qdrant for flexible semantic search operations
"""

import logging
import os
import pickle
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
import threading

try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    np = None
    faiss = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

class SemanticVectorStore:
    """Enhanced vector store supporting both FAISS and Qdrant for semantic search"""
    
    def __init__(self, 
                 storage_type: str = "faiss",  # "faiss" or "qdrant"
                 model_name: str = "distiluse-base-multilingual-cased-v1",
                 index_path: str = "Memory/semantic_index",
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333):
        
        self.storage_type = storage_type
        self.model_name = model_name
        self.index_path = index_path
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        
        # Initialize storage backend
        self.model = None
        self.faiss_index = None
        self.qdrant_client = None
        self.metadata_store = {}
        self.dimension = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize the chosen storage backend"""
        # Load embedding model
        if FAISS_AVAILABLE:
            try:
                logger.info(f"Loading semantic model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"✅ Loaded model with dimension: {self.dimension}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return
        
        # Initialize storage backend
        if self.storage_type == "faiss" and FAISS_AVAILABLE:
            self._initialize_faiss()
        elif self.storage_type == "qdrant" and QDRANT_AVAILABLE:
            self._initialize_qdrant()
        else:
            logger.warning(f"Storage type {self.storage_type} not available, using fallback")
            if FAISS_AVAILABLE:
                self.storage_type = "faiss"
                self._initialize_faiss()
            elif QDRANT_AVAILABLE:
                self.storage_type = "qdrant"
                self._initialize_qdrant()
    
    def _initialize_faiss(self):
        """Initialize FAISS index"""
        try:
            if self.dimension:
                # Use IndexFlatIP for cosine similarity (after normalization)
                self.faiss_index = faiss.IndexFlatIP(self.dimension)
                logger.info(f"✅ Initialized FAISS index (dimension: {self.dimension})")
                
                # Try to load existing index
                self._load_faiss_index()
            else:
                logger.error("Cannot initialize FAISS without model dimension")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS: {e}")
    
    def _initialize_qdrant(self):
        """Initialize Qdrant client"""
        try:
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host, 
                port=self.qdrant_port
            )
            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"✅ Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.qdrant_client = None
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        if self.storage_type == "faiss":
            return FAISS_AVAILABLE and self.model is not None and self.faiss_index is not None
        elif self.storage_type == "qdrant":
            return QDRANT_AVAILABLE and self.qdrant_client is not None
        return False
    
    def add_documents(self, documents: List[Dict[str, Any]], collection_name: str = "default") -> bool:
        """
        Add multiple documents to the vector store
        
        Args:
            documents: List of documents with 'text' and 'metadata' keys
            collection_name: Collection/index name
            
        Returns:
            Success status
        """
        if not self.is_available():
            logger.warning("Vector store not available")
            return False
        
        try:
            with self._lock:
                if self.storage_type == "faiss":
                    return self._add_documents_faiss(documents, collection_name)
                elif self.storage_type == "qdrant":
                    return self._add_documents_qdrant(documents, collection_name)
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def _add_documents_faiss(self, documents: List[Dict[str, Any]], collection_name: str) -> bool:
        """Add documents to FAISS index"""
        try:
            texts = [doc['text'] for doc in documents]
            
            # Generate embeddings in batch
            logger.info(f"Generating embeddings for {len(texts)} documents...")
            embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to index
            start_id = self.faiss_index.ntotal
            self.faiss_index.add(embeddings)
            
            # Store metadata
            if collection_name not in self.metadata_store:
                self.metadata_store[collection_name] = {}
            
            for i, doc in enumerate(documents):
                doc_id = start_id + i
                self.metadata_store[collection_name][doc_id] = {
                    **doc.get('metadata', {}),
                    'text': doc['text'],
                    'added_at': datetime.now().isoformat()
                }
            
            logger.info(f"✅ Added {len(documents)} documents to FAISS index")
            self._save_faiss_index()
            return True
            
        except Exception as e:
            logger.error(f"FAISS add error: {e}")
            return False
    
    def _add_documents_qdrant(self, documents: List[Dict[str, Any]], collection_name: str) -> bool:
        """Add documents to Qdrant"""
        # Implementation would go here for Qdrant support
        logger.warning("Qdrant support not fully implemented yet")
        return False
    
    def search(self, query: str, collection_name: str = "default", 
               top_k: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            collection_name: Collection to search in
            top_k: Number of results to return
            min_score: Minimum similarity score
            
        Returns:
            List of search results
        """
        if not self.is_available():
            logger.warning("Vector store not available")
            return []
        
        try:
            with self._lock:
                if self.storage_type == "faiss":
                    return self._search_faiss(query, collection_name, top_k, min_score)
                elif self.storage_type == "qdrant":
                    return self._search_qdrant(query, collection_name, top_k, min_score)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _search_faiss(self, query: str, collection_name: str, top_k: int, min_score: float) -> List[Dict[str, Any]]:
        """Search using FAISS index"""
        try:
            if self.faiss_index.ntotal == 0:
                logger.info("FAISS index is empty")
                return []
            
            # Generate query embedding
            query_embedding = self.model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.faiss_index.search(query_embedding, min(top_k, self.faiss_index.ntotal))
            
            # Format results
            results = []
            collection_metadata = self.metadata_store.get(collection_name, {})
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or score < min_score:  # -1 indicates no result
                    continue
                
                metadata = collection_metadata.get(idx, {})
                
                result = {
                    'id': idx,
                    'score': float(score),
                    'text': metadata.get('text', ''),
                    'metadata': {k: v for k, v in metadata.items() if k != 'text'}
                }
                results.append(result)
            
            logger.info(f"🔍 FAISS search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return []
    
    def _search_qdrant(self, query: str, collection_name: str, top_k: int, min_score: float) -> List[Dict[str, Any]]:
        """Search using Qdrant"""
        # Implementation would go here for Qdrant support
        logger.warning("Qdrant search not fully implemented yet")
        return []
    
    def update_document(self, doc_id: Union[str, int], text: str, metadata: Dict[str, Any], 
                       collection_name: str = "default") -> bool:
        """Update a document in the vector store"""
        # For FAISS, this would require rebuilding the index
        # For now, we'll remove and re-add
        return self.remove_document(doc_id, collection_name) and \
               self.add_documents([{'text': text, 'metadata': metadata}], collection_name)
    
    def remove_document(self, doc_id: Union[str, int], collection_name: str = "default") -> bool:
        """Remove a document from the vector store"""
        try:
            with self._lock:
                if self.storage_type == "faiss":
                    # FAISS doesn't support direct removal, would need index rebuild
                    collection_metadata = self.metadata_store.get(collection_name, {})
                    if doc_id in collection_metadata:
                        del collection_metadata[doc_id]
                        self._save_faiss_index()
                        return True
                    return False
                elif self.storage_type == "qdrant":
                    # Qdrant supports direct removal
                    pass
            
        except Exception as e:
            logger.error(f"Failed to remove document: {e}")
            return False
    
    def get_stats(self, collection_name: str = "default") -> Dict[str, Any]:
        """Get statistics about the vector store"""
        stats = {
            'storage_type': self.storage_type,
            'model_name': self.model_name,
            'available': self.is_available()
        }
        
        if self.storage_type == "faiss" and self.faiss_index:
            stats.update({
                'total_documents': self.faiss_index.ntotal,
                'dimension': self.dimension,
                'collections': list(self.metadata_store.keys())
            })
        
        return stats
    
    def _save_faiss_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            os.makedirs(self.index_path, exist_ok=True)
            
            # Save FAISS index
            index_file = os.path.join(self.index_path, "faiss.index")
            faiss.write_index(self.faiss_index, index_file)
            
            # Save metadata
            metadata_file = os.path.join(self.index_path, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved FAISS index to {self.index_path}")
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
    
    def _load_faiss_index(self):
        """Load FAISS index and metadata from disk"""
        try:
            index_file = os.path.join(self.index_path, "faiss.index")
            metadata_file = os.path.join(self.index_path, "metadata.json")
            
            if os.path.exists(index_file) and os.path.exists(metadata_file):
                # Load FAISS index
                self.faiss_index = faiss.read_index(index_file)
                
                # Load metadata
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata_store = json.load(f)
                
                # Convert string keys back to integers for FAISS IDs
                for collection_name, collection_data in self.metadata_store.items():
                    if isinstance(collection_data, dict):
                        converted_data = {}
                        for k, v in collection_data.items():
                            try:
                                converted_data[int(k)] = v
                            except ValueError:
                                converted_data[k] = v
                        self.metadata_store[collection_name] = converted_data
                
                logger.info(f"✅ Loaded FAISS index from {self.index_path} "
                           f"({self.faiss_index.ntotal} documents)")
            else:
                logger.info("No existing FAISS index found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            # Reinitialize on error
            if self.dimension:
                self.faiss_index = faiss.IndexFlatIP(self.dimension)
                self.metadata_store = {}
    
    def clear_collection(self, collection_name: str = "default") -> bool:
        """Clear all documents from a collection"""
        try:
            with self._lock:
                if collection_name in self.metadata_store:
                    del self.metadata_store[collection_name]
                
                if self.storage_type == "faiss":
                    # For FAISS, we need to rebuild without this collection's data
                    self._rebuild_faiss_index()
                
                self._save_faiss_index()
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
    
    def _rebuild_faiss_index(self):
        """Rebuild FAISS index from remaining metadata"""
        try:
            # Create new index
            if self.dimension:
                new_index = faiss.IndexFlatIP(self.dimension)
                new_metadata = {}
                
                # Collect all remaining documents
                all_docs = []
                for collection_name, collection_data in self.metadata_store.items():
                    for doc_id, doc_metadata in collection_data.items():
                        if 'text' in doc_metadata:
                            all_docs.append({
                                'text': doc_metadata['text'],
                                'metadata': doc_metadata,
                                'collection': collection_name
                            })
                
                if all_docs:
                    # Generate embeddings
                    texts = [doc['text'] for doc in all_docs]
                    embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False)
                    faiss.normalize_L2(embeddings)
                    
                    # Add to new index
                    new_index.add(embeddings)
                    
                    # Rebuild metadata with new IDs
                    for i, doc in enumerate(all_docs):
                        collection_name = doc['collection']
                        if collection_name not in new_metadata:
                            new_metadata[collection_name] = {}
                        new_metadata[collection_name][i] = doc['metadata']
                
                # Replace old index and metadata
                self.faiss_index = new_index
                self.metadata_store = new_metadata
                
                logger.info(f"✅ Rebuilt FAISS index with {new_index.ntotal} documents")
            
        except Exception as e:
            logger.error(f"Failed to rebuild FAISS index: {e}")

# Global instances
semantic_vector_store = None

def get_semantic_vector_store(storage_type: str = "faiss") -> Optional[SemanticVectorStore]:
    """Get the global semantic vector store instance"""
    global semantic_vector_store
    
    if semantic_vector_store is None and (FAISS_AVAILABLE or QDRANT_AVAILABLE):
        semantic_vector_store = SemanticVectorStore(storage_type=storage_type)
    
    return semantic_vector_store

def initialize_semantic_vector_store(storage_type: str = "faiss", **kwargs) -> Optional[SemanticVectorStore]:
    """Initialize semantic vector store with custom parameters"""
    global semantic_vector_store
    
    if FAISS_AVAILABLE or QDRANT_AVAILABLE:
        semantic_vector_store = SemanticVectorStore(storage_type=storage_type, **kwargs)
        return semantic_vector_store
    else:
        logger.warning("Neither FAISS nor Qdrant available for semantic vector store")
        return None