"""
Unified Semantic Search Service
Combines files and emails into one semantic search space with intent-aware filtering.
"""

import logging
import re
import os
import json
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

try:
    # Import memory optimizer first to set up environment
    import os
    import sys
    from pathlib import Path
    
    # Add Memory directory to path
    memory_path = str(Path(__file__).parent.parent)
    if memory_path not in sys.path:
        sys.path.append(memory_path)
    
    # Import memory optimizer to configure environment before ML libraries
    try:
        from memory_optimizer import setup_memory_optimized_environment, check_available_memory, cleanup_memory
        memory_mode = check_available_memory()
    except ImportError:
        print("⚠️ Memory optimizer not available, using basic settings")
        # Fallback basic settings
        os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
        os.environ.setdefault('OMP_NUM_THREADS', '1')
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
        memory_mode = "conservative"
    
    # Lazy import ALL ML libraries to avoid segfaults during module import
    np = None
    faiss = None
    SentenceTransformer = None
    import langdetect
    
    # Try NLTK imports with fallback
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk.stem import PorterStemmer
    except ImportError:
        print("📝 NLTK not available - using basic text processing")
        # Create fallback implementations
        def word_tokenize(text):
            return text.split()
        
        class PorterStemmer:
            def stem(self, word):
                return word
        
        # Create a fallback stopwords set
        stopwords = type('stopwords', (), {
            'words': lambda lang: {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        })()
    
    SEMANTIC_SEARCH_AVAILABLE = True
    print("✅ Semantic search libraries loaded successfully")
    
except ImportError as e:
    print(f"⚠️ Unified semantic search dependencies not available: {e}")
    SEMANTIC_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class UnifiedSearchResult:
    """Unified search result for both files and emails"""
    id: str
    type: str  # "file" or "email"
    user_id: str
    name: str
    path: str
    content_snippet: str
    
    # File-specific fields
    file_id: Optional[str] = None
    folder_path: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None
    
    # Email-specific fields
    sender: Optional[str] = None
    subject: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None
    
    # Scoring fields
    semantic_score: float = 0.0
    keyword_boost: float = 0.0
    recency_boost: float = 0.0
    final_score: float = 0.0
    match_explanation: str = ""

class QueryProcessor:
    """Processes natural language queries to detect intent and extract terms"""
    
    def __init__(self):
        self.email_keywords_en = [
            "email", "emails", "message", "messages", "mail", "mails",
            "correspondence", "inbox", "sent", "received", "communication", 
            "communications", "letter", "letters"
        ]
        
        self.email_keywords_ro = [
            "email", "emailuri", "mesaj", "mesaje", "mail", "mailuri",
            "corespondenta", "primite", "trimise", "comunicare", "comunicari"
        ]
        
        self.time_keywords = [
            "recent", "latest", "new", "today", "yesterday", "last week",
            "recent", "nou", "ultima", "azi", "ieri", "saptamana trecuta"
        ]
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query to detect intent and extract meaningful terms"""
        query_lower = query.lower().strip()
        
        # Detect language
        try:
            language = langdetect.detect(query_lower)
        except:
            language = "en"
        
        # Detect if this is email-specific
        email_keywords = self.email_keywords_en + self.email_keywords_ro
        is_email_only = any(keyword in query_lower for keyword in email_keywords) and \
                       any(word in query_lower for word in ["only", "just", "doar", "numai"])
        
        contains_email_terms = any(keyword in query_lower for keyword in email_keywords)
        
        # Extract person names (after "from")
        person_match = re.search(r'from\s+([a-zA-Z0-9\.\-_@]+)', query_lower)
        from_person = person_match.group(1) if person_match else None
        
        # Extract time context
        is_recent = any(keyword in query_lower for keyword in self.time_keywords)
        
        # Clean the query - remove filler words
        cleaned_query = self._clean_query(query_lower)
        
        return {
            "original": query,
            "cleaned": cleaned_query,
            "language": language,
            "filter_type": "email" if is_email_only else ("mixed" if contains_email_terms else "all"),
            "from_person": from_person,
            "is_recent": is_recent,
            "contains_email_terms": contains_email_terms
        }
    
    def _clean_query(self, query: str) -> str:
        """Remove filler words and extract meaningful search terms"""
        # Remove common request phrases
        filler_phrases = [
            "can you find me", "can you find", "can you search for", "search for",
            "find me", "show me", "get me", "lookup", "look for",
            "gaseste", "cauta", "arata-mi", "da-mi"
        ]
        
        for phrase in filler_phrases:
            if phrase in query:
                query = query.replace(phrase, "").strip()
        
        # Remove common articles and prepositions
        stop_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with"]
        words = query.split()
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return " ".join(meaningful_words)

class UnifiedDocumentIndexer:
    """Indexes both files and emails into a unified vector space"""
    
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v1"):
        self.model_name = model_name
        self.model = None
        self.index = None
        self.document_metadata = []
        self.embedding_dimension = 512  # distiluse-base-multilingual-cased-v1 dimension
        
        # Don't initialize model in constructor to avoid segfaults during import
        # Model will be initialized lazily when needed
        self.model_name = model_name
    
    def _ensure_model_loaded(self):
        """Ensure the model is loaded, initialize if needed"""
        if self.model is None and SEMANTIC_SEARCH_AVAILABLE:
            try:
                # Lazy import heavy ML libraries only when needed
                global SentenceTransformer, faiss, np, memory_mode
                
                # Check memory availability before loading
                if memory_mode == "conservative":
                    logger.warning("⚠️ Conservative memory mode - using lightweight model")
                    # Use a smaller, more memory-efficient model
                    model_name = "all-MiniLM-L6-v2"  # Much smaller than distiluse-base-multilingual
                elif memory_mode == "balanced":
                    model_name = "distiluse-base-multilingual-cased-v1"
                else:
                    model_name = self.model_name
                
                if np is None:
                    import numpy as np
                if SentenceTransformer is None:
                    from sentence_transformers import SentenceTransformer
                if faiss is None:
                    import faiss
                
                logger.info(f"🤖 Loading semantic model: {model_name} (mode: {memory_mode})")
                
                # Load model with memory-conservative settings
                self.model = SentenceTransformer(model_name, device='cpu')
                
                # Reduce model precision to save memory if in conservative mode
                if memory_mode == "conservative":
                    try:
                        # Try to use half precision if supported
                        self.model = self.model.half()
                        logger.info("🔧 Using half precision to save memory")
                    except Exception:
                        logger.debug("Half precision not supported, using full precision")
                
                self.embedding_dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"✅ Semantic model loaded successfully (dim: {self.embedding_dimension})")
                
                # Force cleanup after loading
                try:
                    cleanup_memory()
                except NameError:
                    import gc
                    gc.collect()
                
                return True
            except Exception as e:
                logger.error(f"❌ Failed to initialize embedding model: {e}")
                logger.info("🔄 Falling back to keyword-only search")
                self.model = None
                return False
        return self.model is not None
    
    def create_index(self, documents: List[Dict[str, Any]]) -> bool:
        """Create unified FAISS index from documents"""
        if not self._ensure_model_loaded():
            logger.error("❌ Embedding model not available")
            return False
        
        try:
            # Extract text content for embedding
            texts = []
            metadata = []
            
            for doc in documents:
                # Create searchable text combining all relevant fields
                searchable_text = self._create_searchable_text(doc)
                texts.append(searchable_text)
                metadata.append(doc)
            
            if not texts:
                logger.warning("⚠️ No documents to index")
                return False
            
            # Generate embeddings
            logger.info(f"🔄 Generating embeddings for {len(texts)} documents...")
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            
            # Create FAISS index
            self.index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for cosine similarity
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings.astype('float32'))
            
            self.document_metadata = metadata
            logger.info(f"✅ Unified index created with {len(texts)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create unified index: {e}")
            return False
    
    def _create_searchable_text(self, doc: Dict[str, Any]) -> str:
        """Create comprehensive searchable text from document metadata"""
        parts = []
        
        # Common fields
        if doc.get("name"):
            parts.append(doc["name"])
        if doc.get("path"):
            parts.append(doc["path"])
        if doc.get("content"):
            parts.append(doc["content"])
        
        # Email-specific fields
        if doc.get("type") == "email":
            if doc.get("sender"):
                parts.append(f"from {doc['sender']}")
            if doc.get("subject"):
                parts.append(doc["subject"])
            if doc.get("category"):
                parts.append(doc["category"])
        
        # File-specific fields
        elif doc.get("type") == "file":
            if doc.get("folder_path"):
                parts.append(doc["folder_path"])
        
        return " ".join(filter(None, parts))

class UnifiedSemanticSearchService:
    """Unified semantic search service for files and emails"""
    
    def __init__(self):
        self.query_processor = QueryProcessor()
        self.indexer = UnifiedDocumentIndexer()
        self.is_initialized = False
    
    def initialize(self, file_documents: List[Dict], email_documents: List[Dict]) -> bool:
        """Initialize the unified search system"""
        if not SEMANTIC_SEARCH_AVAILABLE:
            logger.warning("⚠️ Semantic search dependencies not available")
            return False
        
        # Combine documents with type markers
        all_documents = []
        
        # Add file documents
        for doc in file_documents:
            unified_doc = {
                "id": doc.get("id", doc.get("file_id", "")),
                "type": "file",
                "user_id": doc.get("user_id", ""),
                "name": doc.get("name", ""),
                "path": doc.get("full_path", doc.get("path", "")),
                "content": doc.get("content", ""),
                "file_id": doc.get("file_id"),
                "folder_path": doc.get("folder_path"),
                "mime_type": doc.get("mime_type"),
                "size": doc.get("size"),
                "modified_time": doc.get("modified_time"),
                "web_view_link": doc.get("web_view_link"),
                "download_link": doc.get("download_link")
            }
            all_documents.append(unified_doc)
        
        # Add email documents
        for doc in email_documents:
            unified_doc = {
                "id": doc.get("id", doc.get("message_id", "")),
                "type": "email",
                "user_id": doc.get("user_id", ""),
                "name": doc.get("name", doc.get("subject", "")),
                "path": doc.get("path", doc.get("file_path", "")),
                "content": doc.get("content", doc.get("body", "")),
                "sender": doc.get("sender", doc.get("sender_email", "")),
                "subject": doc.get("subject", ""),
                "date": doc.get("date", doc.get("timestamp", "")),
                "category": doc.get("category", ""),
                "web_view_link": doc.get("web_view_link"),
                "download_link": doc.get("download_link")
            }
            all_documents.append(unified_doc)
        
        # Create unified index
        success = self.indexer.create_index(all_documents)
        self.is_initialized = success
        
        if success:
            logger.info(f"🎉 Unified semantic search initialized with {len(file_documents)} files and {len(email_documents)} emails")
        
        return success
    
    def search(self, query: str, max_results: int = 10, user_id: Optional[str] = None) -> List[UnifiedSearchResult]:
        """Perform unified semantic search"""
        if not self.is_initialized or not self.indexer.index:
            logger.warning("⚠️ Unified search not initialized")
            return []
        
        try:
            # Process query
            query_info = self.query_processor.process_query(query)
            logger.info(f"🔍 Query processed: {query_info}")
            
            # Generate query embedding
            query_embedding = self.indexer.model.encode([query_info["cleaned"]], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.indexer.index.search(query_embedding.astype('float32'), max_results * 2)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # No more results
                    break
                
                doc = self.indexer.document_metadata[idx]
                
                # Apply filtering based on query intent
                if query_info["filter_type"] == "email" and doc["type"] != "email":
                    continue
                
                # User filtering
                if user_id and doc.get("user_id") and doc["user_id"] != user_id:
                    continue
                
                # Apply person filtering for emails
                if query_info["from_person"] and doc["type"] == "email":
                    sender = doc.get("sender", "").lower()
                    if query_info["from_person"] not in sender:
                        continue
                
                # Calculate boosts
                keyword_boost = self._calculate_keyword_boost(query_info["cleaned"], doc)
                recency_boost = self._calculate_recency_boost(doc, query_info["is_recent"])
                
                final_score = float(score) + keyword_boost + recency_boost
                
                # Create result
                result = UnifiedSearchResult(
                    id=doc["id"],
                    type=doc["type"],
                    user_id=doc.get("user_id", ""),
                    name=doc["name"],
                    path=doc["path"],
                    content_snippet=self._create_snippet(doc["content"], query_info["cleaned"]),
                    
                    # File fields
                    file_id=doc.get("file_id"),
                    folder_path=doc.get("folder_path"),
                    mime_type=doc.get("mime_type"),
                    size=doc.get("size"),
                    modified_time=doc.get("modified_time"),
                    web_view_link=doc.get("web_view_link"),
                    download_link=doc.get("download_link"),
                    
                    # Email fields
                    sender=doc.get("sender"),
                    subject=doc.get("subject"),
                    date=doc.get("date"),
                    category=doc.get("category"),
                    
                    # Scores
                    semantic_score=float(score),
                    keyword_boost=keyword_boost,
                    recency_boost=recency_boost,
                    final_score=final_score,
                    match_explanation=self._create_match_explanation(doc, query_info, float(score))
                )
                
                results.append(result)
                
                if len(results) >= max_results:
                    break
            
            # Sort by final score
            results.sort(key=lambda x: x.final_score, reverse=True)
            
            logger.info(f"📊 Found {len(results)} unified results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Unified search failed: {e}")
            return []
    
    def _calculate_keyword_boost(self, query: str, doc: Dict) -> float:
        """Calculate keyword matching boost"""
        boost = 0.0
        query_words = set(query.lower().split())
        
        # Check name/title
        name_words = set(doc.get("name", "").lower().split())
        if query_words.intersection(name_words):
            boost += 0.2
        
        # Check path
        path_words = set(doc.get("path", "").lower().split())
        if query_words.intersection(path_words):
            boost += 0.1
        
        # Email-specific boosts
        if doc["type"] == "email":
            if doc.get("sender") and any(word in doc["sender"].lower() for word in query_words):
                boost += 0.3
            if doc.get("subject") and any(word in doc["subject"].lower() for word in query_words):
                boost += 0.2
        
        return boost
    
    def _calculate_recency_boost(self, doc: Dict, is_recent_query: bool) -> float:
        """Calculate recency boost for time-sensitive queries"""
        if not is_recent_query:
            return 0.0
        
        try:
            date_str = doc.get("date") or doc.get("modified_time")
            if not date_str:
                return 0.0
            
            # Parse date (handle different formats)
            doc_date = None
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    doc_date = datetime.strptime(date_str[:19], fmt)
                    break
                except:
                    continue
            
            if not doc_date:
                return 0.0
            
            days_old = (datetime.now() - doc_date).days
            if days_old <= 1:
                return 0.3
            elif days_old <= 7:
                return 0.2
            elif days_old <= 30:
                return 0.1
            
        except Exception:
            pass
        
        return 0.0
    
    def _create_snippet(self, content: str, query: str) -> str:
        """Create a relevant snippet from content"""
        if not content:
            return ""
        
        content = content.strip()
        if len(content) <= 150:
            return content
        
        # Try to find query terms in content
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_pos = 0
        for word in query_words:
            pos = content_lower.find(word)
            if pos != -1:
                best_pos = max(0, pos - 50)
                break
        
        snippet = content[best_pos:best_pos + 150]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + 150 < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _create_match_explanation(self, doc: Dict, query_info: Dict, semantic_score: float) -> str:
        """Create explanation for why this result matched"""
        explanations = []
        
        if semantic_score > 0.8:
            explanations.append("High semantic similarity")
        elif semantic_score > 0.6:
            explanations.append("Good semantic match")
        else:
            explanations.append("Semantic match")
        
        if doc["type"] == "email":
            explanations.append("Email document")
            if query_info.get("from_person") and doc.get("sender"):
                explanations.append(f"From {doc['sender']}")
        else:
            explanations.append("File document")
        
        return "; ".join(explanations)

# Global instance
unified_search_service = UnifiedSemanticSearchService()