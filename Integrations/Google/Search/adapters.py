"""
Search Adapter for Hybrid Search System
Maintains existing API signatures while using the new hybrid search orchestrator
"""

import logging
from typing import List, Dict, Any, Optional

from .orchestrator import get_search_orchestrator, SearchRequest
from .query_interpreter import SearchSource

logger = logging.getLogger(__name__)


class SearchAdapter:
    """
    Adapter that maintains compatibility with existing search interfaces
    All calls route to the hybrid search orchestrator
    """
    
    def __init__(self):
        self.orchestrator = get_search_orchestrator()
        logger.info("🚀 Using hybrid search implementation")

    def search_files(self, 
                    query: str, 
                    folder_filter: Optional[str] = None,
                    file_type_filter: Optional[str] = None,
                    max_results: int = 10,
                    user_id: Optional[str] = None,
                    use_semantic_search: bool = True) -> List[Dict[str, Any]]:
        """
        GoogleDriveSearchService.search_files() compatibility
        
        Args:
            query: Search query (natural language supported)
            folder_filter: Filter by folder path (e.g., "Executive", "Marketing") 
            file_type_filter: Filter by file type (e.g., "pdf", "doc", "excel")
            max_results: Maximum number of results to return
            user_id: User ID for accessing user-specific Google Drive via Gmail OAuth
            use_semantic_search: Whether to use semantic search (ignored - always uses hybrid)
            
        Returns:
            List of file dictionaries in legacy format
        """
        logger.info(f"🔍 Hybrid search_files: '{query}'")
        
        return self._search_files_hybrid(
            query, folder_filter, file_type_filter, max_results, user_id
        )

    def _search_files_hybrid(self, 
                           query: str, 
                           folder_filter: Optional[str],
                           file_type_filter: Optional[str], 
                           max_results: int, 
                           user_id: Optional[str]) -> List[Dict[str, Any]]:
        """Execute search using hybrid orchestrator"""
        try:
            # Modify query to include file type filter if specified
            enhanced_query = query
            if file_type_filter:
                # Map common file types to Romanian-aware query enhancement
                type_mappings = {
                    'pdf': 'tip:pdf',
                    'doc': 'tip:docx',
                    'docx': 'tip:docx', 
                    'excel': 'tip:xlsx',
                    'xlsx': 'tip:xlsx',
                    'ppt': 'tip:pptx',
                    'pptx': 'tip:pptx'
                }
                type_query = type_mappings.get(file_type_filter.lower(), f'tip:{file_type_filter}')
                enhanced_query = f"{query} {type_query}"
            
            request = SearchRequest(
                query=enhanced_query,
                max_results=max_results,
                user_id=user_id,
                sources=[SearchSource.DRIVE],  # Files only
                folder_filter=folder_filter
            )
            
            response = self.orchestrator.search(request)
            
            # Convert to legacy format
            legacy_results = []
            for result in response.results:
                if result.get('source') == 'drive':
                    # Convert hybrid format to legacy GoogleDriveSearchResult format
                    legacy_result = {
                        'file_id': result['id'],
                        'name': result['name'],
                        'folder_path': result.get('folder_path', ''),
                        'full_path': f"{result.get('folder_path', '')}/{result['name']}".strip('/'),
                        'mime_type': result['mime_type'],
                        'size': result.get('size', 0),
                        'modified_time': result['modified_time'],
                        'web_view_link': result['web_view_link'],
                        'download_link': result['download_link'],
                        'file_type': result.get('file_type', 'Unknown File Type'),
                        'ranking_score': result.get('ranking_score', 0.0)
                    }
                    legacy_results.append(legacy_result)
            
            logger.info(f"✅ Hybrid search returned {len(legacy_results)} files")
            return legacy_results
            
        except Exception as e:
            logger.error(f"❌ Hybrid file search failed: {e}")
            return []



    def search_emails(self, 
                     query: str, 
                     user_id: str, 
                     max_results: int = 10) -> List[Dict[str, Any]]:
        """
        SemanticEmailSearch.search_emails() compatibility
        
        Args:
            query: Natural language search query
            user_id: User identifier for folder targeting
            max_results: Maximum number of results to return
            
        Returns:
            List of email dictionaries in legacy format
        """
        logger.info(f"📧 Hybrid search_emails: '{query}'")
        
        return self._search_emails_hybrid(query, user_id, max_results)

    def _search_emails_hybrid(self, 
                            query: str, 
                            user_id: str, 
                            max_results: int) -> List[Dict[str, Any]]:
        """Execute email search using hybrid orchestrator"""
        try:
            request = SearchRequest(
                query=query,
                max_results=max_results,
                user_id=user_id,
                sources=[SearchSource.GMAIL],  # Emails only
                include_content=True
            )
            
            response = self.orchestrator.search(request)
            
            # Convert to legacy format
            legacy_results = []
            for result in response.results:
                if result.get('source') == 'gmail':
                    # Convert hybrid format to legacy SearchResult format
                    legacy_result = {
                        'id': result['id'],
                        'title': result.get('subject', '(No Subject)'),
                        'content': result.get('snippet', ''),
                        'full_content': result.get('content', ''),
                        'sender': result.get('sender', '(Unknown Sender)'),
                        'recipient': result.get('recipient', ''),
                        'date': result['date'],
                        'url': result.get('url', ''),
                        'source': 'email',
                        'file_path': f"Gmail/{result['id']}.eml",
                        'ranking_score': result.get('ranking_score', 0.0),
                        'labels': result.get('labels', []),
                        'has_attachments': result.get('has_attachments', False)
                    }
                    legacy_results.append(legacy_result)
            
            logger.info(f"✅ Hybrid email search returned {len(legacy_results)} emails")
            return legacy_results
            
        except Exception as e:
            logger.error(f"❌ Hybrid email search failed: {e}")
            return []



    def unified_search(self, 
                      query: str, 
                      max_results: int = 25, 
                      user_id: Optional[str] = None,
                      include_emails: bool = True,
                      include_files: bool = True) -> Dict[str, Any]:
        """
        Unified search across both Gmail and Drive
        
        Args:
            query: Search query string
            max_results: Maximum total results
            user_id: Optional user ID
            include_emails: Whether to search emails
            include_files: Whether to search files
            
        Returns:
            Unified search results
        """
        logger.info(f"🔍 Unified hybrid search: '{query}'")
        
        return self._unified_search_hybrid(
            query, max_results, user_id, include_emails, include_files
        )

    def _unified_search_hybrid(self, 
                             query: str, 
                             max_results: int, 
                             user_id: Optional[str],
                             include_emails: bool, 
                             include_files: bool) -> Dict[str, Any]:
        """Execute unified search using hybrid orchestrator"""
        try:
            # Determine sources
            sources = []
            if include_emails:
                sources.append(SearchSource.GMAIL)
            if include_files:
                sources.append(SearchSource.DRIVE)
            
            if not sources:
                sources = [SearchSource.AUTO]
            
            request = SearchRequest(
                query=query,
                max_results=max_results,
                user_id=user_id,
                sources=sources,
                include_content=True
            )
            
            response = self.orchestrator.search(request)
            
            return {
                "success": True,
                "results": response.results,
                "total_results": response.total_results,
                "sources_searched": response.sources_searched,
                "query_interpretation": response.query_interpretation,
                "performance": response.performance_metrics,
                "hybrid_search": True
            }
            
        except Exception as e:
            logger.error(f"❌ Hybrid unified search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "total_results": 0,
                "hybrid_search": True
            }



    def test_connectivity(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Test connectivity to search services"""
        return self.orchestrator.test_connectivity(user_id)


# Global adapter instance
_search_adapter = None


def get_search_adapter() -> SearchAdapter:
    """Get singleton SearchAdapter instance"""
    global _search_adapter
    
    if _search_adapter is None:
        _search_adapter = SearchAdapter()
    
    return _search_adapter


# Compatibility functions that maintain exact signatures
def search_files(query: str, 
                folder_filter: Optional[str] = None,
                file_type_filter: Optional[str] = None,
                max_results: int = 10,
                user_id: Optional[str] = None,
                use_semantic_search: bool = True) -> List[Dict[str, Any]]:
    """GoogleDriveSearchService.search_files() compatibility"""
    adapter = get_search_adapter()
    return adapter.search_files(
        query, folder_filter, file_type_filter, max_results, user_id, use_semantic_search
    )


def search_emails(query: str, user_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """SemanticEmailSearch.search_emails() compatibility"""
    adapter = get_search_adapter()
    return adapter.search_emails(query, user_id, max_results)


def unified_search(query: str, 
                  max_results: int = 25, 
                  user_id: Optional[str] = None) -> Dict[str, Any]:
    """Unified search function"""
    adapter = get_search_adapter()
    return adapter.unified_search(query, max_results, user_id)
