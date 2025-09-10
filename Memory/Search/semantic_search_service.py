"""
Semantic File Search Service
A comprehensive semantic search system for file discovery using natural language understanding,
vector embeddings, and multilingual support.
"""

import logging
import re
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

try:
    # Import memory optimizer first
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
        print(f"🔧 Memory mode: {memory_mode}")
    except ImportError:
        print("⚠️ Memory optimizer not available, using basic settings")
        # Fallback basic settings
        os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
        os.environ.setdefault('OMP_NUM_THREADS', '1')
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
        memory_mode = "conservative"
    
    # Lazy import ML libraries to avoid segfaults
    faiss = None
    np = None
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
except ImportError as e:
    print(f"⚠️ Semantic search dependencies not available: {e}")
    SEMANTIC_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Enhanced search result with semantic scoring"""
    file_id: str
    name: str
    folder_path: str
    full_path: str
    mime_type: str
    size: str
    modified_time: str
    web_view_link: str
    download_link: str
    file_type: str
    
    # Semantic search specific fields
    semantic_score: float
    keyword_boost: float
    recency_boost: float
    final_score: float
    match_snippet: str = ""
    match_explanation: str = ""

@dataclass
class SearchConfig:
    """Configuration for semantic search behavior"""
    min_similarity_threshold: float = 0.65
    max_results: int = 10
    boost_recency_days: int = 30
    recency_boost_factor: float = 0.1
    keyword_boost_factor: float = 0.2
    use_multilingual: bool = True
    supported_languages: List[str] = None
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ['en', 'ro']

class QueryProcessor:
    """Handles query understanding and preprocessing"""
    
    def __init__(self):
        self.stemmer = PorterStemmer()
        self._setup_nltk()
    
    def _setup_nltk(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK data...")
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process and analyze the user query
        
        Args:
            query: Raw user query
            
        Returns:
            Dict containing processed query information
        """
        result = {
            'original': query,
            'cleaned': self._clean_query(query),
            'language': self._detect_language(query),
            'keywords': [],
            'intent': self._detect_intent(query),
            'filters': self._extract_filters(query)
        }
        
        # Extract keywords
        result['keywords'] = self._extract_keywords(result['cleaned'])
        
        # Normalize for embedding
        result['normalized'] = self._normalize_for_embedding(result['cleaned'])
        
        return result
    
    def _clean_query(self, query: str) -> str:
        """Basic query cleaning"""
        # Remove extra whitespace and normalize
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Remove certain prefixes that agents might add
        prefixes_to_remove = [
            "show me", "find me", "get me", "search for",
            "can you", "please", "i need", "i want"
        ]
        
        query_lower = query.lower()
        for prefix in prefixes_to_remove:
            if query_lower.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        
        return query
    
    def _detect_language(self, query: str) -> str:
        """Detect query language"""
        try:
            if SEMANTIC_SEARCH_AVAILABLE:
                return langdetect.detect(query)
        except:
            pass
        return 'en'  # Default to English
    
    def _detect_intent(self, query: str) -> str:
        """Detect the intent of the query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['latest', 'recent', 'new', 'last']):
            return 'recent_files'
        elif any(word in query_lower for word in ['contract', 'agreement', 'deal']):
            return 'contracts'
        elif any(word in query_lower for word in ['email', 'mail', 'message', 'communication']):
            return 'emails'
        elif any(word in query_lower for word in ['report', 'analysis', 'briefing']):
            return 'reports'
        elif any(word in query_lower for word in ['internal', 'team', 'company']):
            return 'internal_docs'
        else:
            return 'general'
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters from query"""
        filters = {}
        query_lower = query.lower()
        
        # File type filters
        if 'pdf' in query_lower:
            filters['file_type'] = 'pdf'
        elif any(word in query_lower for word in ['doc', 'docx', 'word']):
            filters['file_type'] = 'doc'
        elif any(word in query_lower for word in ['excel', 'xlsx', 'spreadsheet']):
            filters['file_type'] = 'excel'
        
        # Time filters
        if any(word in query_lower for word in ['today', 'yesterday']):
            filters['days_back'] = 1
        elif 'this week' in query_lower:
            filters['days_back'] = 7
        elif 'this month' in query_lower:
            filters['days_back'] = 30
        elif 'recent' in query_lower:
            filters['days_back'] = 14
        
        # Client/project filters (extract potential client names)
        potential_clients = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        if potential_clients:
            filters['clients'] = potential_clients
        
        return filters
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        if not SEMANTIC_SEARCH_AVAILABLE:
            return query.split()
        
        try:
            # Tokenize
            tokens = word_tokenize(query.lower())
            
            # Remove stopwords
            stop_words = set(stopwords.words('english'))
            filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
            
            # Stem words
            stemmed = [self.stemmer.stem(token) for token in filtered_tokens]
            
            return stemmed
        except:
            # Fallback to simple split
            return [word.lower() for word in query.split() if len(word) > 2]
    
    def _normalize_for_embedding(self, query: str) -> str:
        """Normalize query for embedding generation"""
        # Keep it relatively clean but preserve meaning
        return re.sub(r'[^\w\s]', ' ', query).strip()

class SemanticSearchService:
    """Main semantic search service"""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.query_processor = QueryProcessor()
        self.model = None
        self.index = None
        self.file_metadata = {}
        self.embeddings_cache = {}
        
        if SEMANTIC_SEARCH_AVAILABLE:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            # Lazy import SentenceTransformer to avoid segfaults during module import
            global SentenceTransformer, memory_mode
            if SentenceTransformer is None:
                from sentence_transformers import SentenceTransformer
            
            # Choose model based on memory mode and config
            if hasattr(self, 'memory_mode') and memory_mode == "conservative":
                model_name = "all-MiniLM-L6-v2"  # Smaller model for conservative mode
            elif self.config.use_multilingual:
                # Multilingual model for English + Romanian
                model_name = "distiluse-base-multilingual-cased-v1"
            else:
                # English-only model (faster)
                model_name = "all-MiniLM-L6-v2"
            
            logger.info(f"Loading semantic model: {model_name}")
            self.model = SentenceTransformer(model_name, device='cpu')
            logger.info("✅ Semantic search model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if semantic search is available"""
        return SEMANTIC_SEARCH_AVAILABLE and self.model is not None
    
    def search(self, query: str, files: List[Dict], user_id: str = None) -> List[SearchResult]:
        """
        Perform semantic search on files
        
        Args:
            query: User search query
            files: List of file dictionaries from Google Drive
            user_id: User ID for personalization
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        if not self.is_available():
            logger.warning("Semantic search not available, falling back to keyword search")
            return self._fallback_keyword_search(query, files)
        
        try:
            # Process the query
            processed_query = self.query_processor.process_query(query)
            logger.info(f"🔍 Semantic search query: '{processed_query['normalized']}' "
                       f"(intent: {processed_query['intent']}, lang: {processed_query['language']})")
            
            # Generate query embedding (cached)
            query_text = processed_query['normalized']
            if hasattr(self, '_query_cache') and query_text in self._query_cache:
                query_embedding = self._query_cache[query_text]
            else:
                query_embedding = self.model.encode([query_text])
                if not hasattr(self, '_query_cache'):
                    self._query_cache = {}
                self._query_cache[query_text] = query_embedding
            
            # Prepare file data for semantic matching
            file_texts = []
            file_metadata = []
            
            for file_data in files:
                # Create searchable text from file metadata
                searchable_text = self._create_searchable_text(file_data)
                file_texts.append(searchable_text)
                file_metadata.append(file_data)
            
            if not file_texts:
                return []
            
            # Generate embeddings for files (batch processing with caching)
            file_cache_key = str(hash(tuple(file_texts)))
            if hasattr(self, '_file_cache') and file_cache_key in self._file_cache:
                file_embeddings = self._file_cache[file_cache_key]
            else:
                file_embeddings = self.model.encode(file_texts)
                if not hasattr(self, '_file_cache'):
                    self._file_cache = {}
                self._file_cache[file_cache_key] = file_embeddings
                # Limit cache size to prevent memory issues
                if len(self._file_cache) > 100:
                    # Remove oldest entries
                    oldest_key = next(iter(self._file_cache))
                    del self._file_cache[oldest_key]
            
            # Calculate similarities (lazy import numpy)
            global np
            if np is None:
                import numpy as np
            similarities = np.dot(query_embedding, file_embeddings.T).flatten()
            
            # Create search results with scores
            results = []
            for i, (similarity, file_data) in enumerate(zip(similarities, file_metadata)):
                if similarity < self.config.min_similarity_threshold:
                    continue
                
                # Calculate additional scoring factors
                keyword_boost = self._calculate_keyword_boost(processed_query['keywords'], file_data)
                recency_boost = self._calculate_recency_boost(file_data)
                
                # Final score calculation
                final_score = similarity + (keyword_boost * self.config.keyword_boost_factor) + (recency_boost * self.config.recency_boost_factor)
                
                # Create result object
                result = SearchResult(
                    file_id=file_data.get('file_id', ''),
                    name=file_data.get('name', ''),
                    folder_path=file_data.get('folder_path', ''),
                    full_path=file_data.get('full_path', ''),
                    mime_type=file_data.get('mime_type', ''),
                    size=file_data.get('size', ''),
                    modified_time=file_data.get('modified_time', ''),
                    web_view_link=file_data.get('web_view_link', ''),
                    download_link=file_data.get('download_link', ''),
                    file_type=file_data.get('file_type', ''),
                    semantic_score=float(similarity),
                    keyword_boost=keyword_boost,
                    recency_boost=recency_boost,
                    final_score=final_score,
                    match_snippet=self._generate_match_snippet(processed_query, file_data),
                    match_explanation=self._generate_match_explanation(processed_query, similarity, keyword_boost)
                )
                
                results.append(result)
            
            # Sort by final score and limit results
            results.sort(key=lambda x: x.final_score, reverse=True)
            results = results[:self.config.max_results]
            
            logger.info(f"📊 Semantic search found {len(results)} relevant files "
                       f"(threshold: {self.config.min_similarity_threshold})")
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._fallback_keyword_search(query, files)
    
    def _create_searchable_text(self, file_data: Dict) -> str:
        """Create searchable text representation of a file"""
        components = []
        
        # File name (most important)
        if 'name' in file_data:
            components.append(file_data['name'])
        
        # Folder path (context)
        if 'folder_path' in file_data:
            path_parts = file_data['folder_path'].replace('My Drive/', '').split('/')
            components.extend(path_parts)
        
        # File type
        if 'file_type' in file_data:
            components.append(file_data['file_type'])
        
        # Join and clean
        searchable_text = ' '.join(components).replace('_', ' ').replace('-', ' ')
        
        return searchable_text
    
    def _calculate_keyword_boost(self, keywords: List[str], file_data: Dict) -> float:
        """Calculate keyword overlap boost"""
        if not keywords:
            return 0.0
        
        file_text = self._create_searchable_text(file_data).lower()
        
        matches = sum(1 for keyword in keywords if keyword in file_text)
        
        return matches / len(keywords)
    
    def _calculate_recency_boost(self, file_data: Dict) -> float:
        """Calculate recency boost based on file modification time"""
        try:
            if 'modified_time' not in file_data:
                return 0.0
            
            # Parse modification time
            modified_time = datetime.fromisoformat(file_data['modified_time'].replace('Z', '+00:00'))
            now = datetime.now(modified_time.tzinfo)
            
            days_old = (now - modified_time).days
            
            if days_old <= self.config.boost_recency_days:
                # Linear decay: newest files get full boost
                boost = 1.0 - (days_old / self.config.boost_recency_days)
                return boost
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _generate_match_snippet(self, processed_query: Dict, file_data: Dict) -> str:
        """Generate a snippet explaining why this file matched"""
        components = []
        
        if file_data.get('name'):
            components.append(f"File: {file_data['name']}")
        
        if file_data.get('folder_path'):
            folder = file_data['folder_path'].replace('My Drive/', '')
            components.append(f"Location: {folder}")
        
        return " | ".join(components)
    
    def _generate_match_explanation(self, processed_query: Dict, semantic_score: float, keyword_boost: float) -> str:
        """Generate explanation of why this file matched"""
        explanations = []
        
        if semantic_score > 0.8:
            explanations.append("Strong semantic match")
        elif semantic_score > 0.7:
            explanations.append("Good semantic match")
        else:
            explanations.append("Relevant match")
        
        if keyword_boost > 0.5:
            explanations.append("keyword overlap")
        
        if processed_query.get('intent') != 'general':
            explanations.append(f"matches {processed_query['intent']} intent")
        
        return ", ".join(explanations)
    
    def _fallback_keyword_search(self, query: str, files: List[Dict]) -> List[SearchResult]:
        """Fallback to simple keyword search when semantic search is unavailable"""
        logger.info(f"🔄 Using fallback keyword search for: '{query}'")
        
        query_terms = query.lower().split()
        results = []
        
        for file_data in files:
            searchable_text = self._create_searchable_text(file_data).lower()
            
            # Count keyword matches
            matches = sum(1 for term in query_terms if term in searchable_text)
            
            if matches > 0:
                score = matches / len(query_terms)
                
                result = SearchResult(
                    file_id=file_data.get('file_id', ''),
                    name=file_data.get('name', ''),
                    folder_path=file_data.get('folder_path', ''),
                    full_path=file_data.get('full_path', ''),
                    mime_type=file_data.get('mime_type', ''),
                    size=file_data.get('size', ''),
                    modified_time=file_data.get('modified_time', ''),
                    web_view_link=file_data.get('web_view_link', ''),
                    download_link=file_data.get('download_link', ''),
                    file_type=file_data.get('file_type', ''),
                    semantic_score=score,
                    keyword_boost=0.0,
                    recency_boost=0.0,
                    final_score=score,
                    match_snippet=self._generate_match_snippet({'keywords': query_terms}, file_data),
                    match_explanation=f"Keyword match ({matches}/{len(query_terms)} terms)"
                )
                
                results.append(result)
        
        # Sort by score
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results[:self.config.max_results]

# Global instance
semantic_search = SemanticSearchService() if SEMANTIC_SEARCH_AVAILABLE else None

def get_semantic_search_service() -> Optional[SemanticSearchService]:
    """Get the global semantic search service instance"""
    return semantic_search