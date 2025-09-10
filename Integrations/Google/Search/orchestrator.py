"""
Hybrid Search Orchestrator
Coordinates Gmail and Drive search with bilingual support and unified results
"""

import logging
import time
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .query_interpreter import QueryInterpreter, SearchSpec, SearchSource
from .gmail_client import GmailClient, GmailMessage
from .drive_client import DriveClient, DriveFile
from .reranker import HybridReranker, RankingResult, create_reranker

logger = logging.getLogger(__name__)


@dataclass
class SearchRequest:
    """Unified search request"""
    query: str
    max_results: int = 25
    user_id: Optional[str] = None
    sources: List[SearchSource] = None
    include_content: bool = False
    folder_filter: Optional[str] = None


@dataclass
class SearchResponse:
    """Unified search response"""
    results: List[Dict[str, Any]]
    total_results: int
    sources_searched: List[str]
    query_interpretation: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    request_id: str


class HybridSearchOrchestrator:
    """
    Production-grade search orchestrator for Gmail and Drive
    Supports bilingual queries, parallel execution, and unified ranking
    """
    
    def __init__(self, 
                 max_workers: int = 2,
                 default_max_results: int = 25,
                 enable_parallel_search: bool = True):
        """
        Initialize orchestrator
        
        Args:
            max_workers: Number of parallel search workers
            default_max_results: Default max results per search
            enable_parallel_search: Whether to search Gmail/Drive in parallel
        """
        self.max_workers = max_workers
        self.default_max_results = default_max_results
        self.enable_parallel_search = enable_parallel_search
        
        # Initialize components
        self.query_interpreter = QueryInterpreter()
        self.reranker = create_reranker()
        
        # Performance tracking
        self._search_count = 0
        self._total_search_time = 0.0
        
        logger.info(f"🚀 HybridSearchOrchestrator initialized: "
                   f"parallel={enable_parallel_search}, max_workers={max_workers}")

    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute unified search across Gmail and Drive
        
        Args:
            request: SearchRequest with query and parameters
            
        Returns:
            SearchResponse with unified, ranked results
        """
        import uuid
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger.info(f"🔍 [{request_id}] Search request: '{request.query}' "
                   f"(max: {request.max_results}, user: {request.user_id})")
        
        try:
            # Step 1: Interpret query
            spec = self.query_interpreter.interpret_query(request.query)
            logger.info(f"🧠 [{request_id}] Query interpreted: source={spec.source.value}, "
                       f"language={spec.language}, operators={len(spec.operators)}")
            
            # Step 2: Determine sources to search
            sources_to_search = self._determine_sources(spec, request.sources)
            
            # Step 3: Execute searches
            gmail_results, drive_results = self._execute_searches(
                spec, sources_to_search, request, request_id
            )
            
            # Step 4: Combine and rerank results
            combined_results = gmail_results + drive_results
            ranked_results = self._rerank_results(combined_results, spec, request_id)
            
            # Step 5: Apply final filtering and limits
            final_results = self._apply_final_filters(ranked_results, request)
            
            # Step 6: Build response
            duration = time.time() - start_time
            response = self._build_response(
                final_results, spec, sources_to_search, duration, request_id
            )
            
            # Update performance metrics
            self._update_metrics(duration)
            
            logger.info(f"✅ [{request_id}] Search completed: {len(final_results)} results in {duration:.2f}s")
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [{request_id}] Search failed after {duration:.2f}s: {e}")
            
            # Return error response
            return SearchResponse(
                results=[],
                total_results=0,
                sources_searched=[],
                query_interpretation={"error": str(e)},
                performance_metrics={"duration": duration, "error": True},
                request_id=request_id
            )

    def _determine_sources(self, 
                          spec: SearchSpec, 
                          requested_sources: Optional[List[SearchSource]]) -> List[SearchSource]:
        """Determine which sources to search based on query and request"""
        if requested_sources:
            return requested_sources
        
        if spec.source == SearchSource.AUTO:
            # Search both sources for auto-detected queries
            return [SearchSource.GMAIL, SearchSource.DRIVE]
        else:
            return [spec.source]

    def _execute_searches(self, 
                         spec: SearchSpec, 
                         sources: List[SearchSource], 
                         request: SearchRequest,
                         request_id: str) -> tuple[List[GmailMessage], List[DriveFile]]:
        """Execute searches across specified sources"""
        gmail_results = []
        drive_results = []
        
        if self.enable_parallel_search and len(sources) > 1:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_source = {}
                
                if SearchSource.GMAIL in sources:
                    future_to_source[executor.submit(
                        self._search_gmail, spec, request, request_id
                    )] = SearchSource.GMAIL
                
                if SearchSource.DRIVE in sources:
                    future_to_source[executor.submit(
                        self._search_drive, spec, request, request_id
                    )] = SearchSource.DRIVE
                
                # Collect results
                for future in as_completed(future_to_source):
                    source = future_to_source[future]
                    try:
                        results = future.result()
                        if source == SearchSource.GMAIL:
                            gmail_results = results
                        else:
                            drive_results = results
                    except Exception as e:
                        logger.error(f"❌ [{request_id}] {source.value} search failed: {e}")
        else:
            # Sequential execution
            if SearchSource.GMAIL in sources:
                gmail_results = self._search_gmail(spec, request, request_id)
            
            if SearchSource.DRIVE in sources:
                drive_results = self._search_drive(spec, request, request_id)
        
        return gmail_results, drive_results

    def _search_gmail(self, 
                     spec: SearchSpec, 
                     request: SearchRequest, 
                     request_id: str) -> List[GmailMessage]:
        """Execute Gmail search"""
        try:
            gmail_client = GmailClient(request.user_id)
            query = gmail_client.build_query_from_spec(spec)
            
            logger.info(f"📧 [{request_id}] Gmail query: '{query}'")
            
            results = gmail_client.search_messages(
                query=query,
                max_results=request.max_results,
                include_content=request.include_content
            )
            
            logger.info(f"📧 [{request_id}] Gmail results: {len(results)} messages")
            return results
            
        except Exception as e:
            logger.error(f"❌ [{request_id}] Gmail search error: {e}")
            return []

    def _search_drive(self, 
                     spec: SearchSpec, 
                     request: SearchRequest, 
                     request_id: str) -> List[DriveFile]:
        """Execute Drive search"""
        try:
            drive_client = DriveClient(request.user_id)
            query = drive_client.build_query_from_spec(spec)
            
            logger.info(f"📁 [{request_id}] Drive query: '{query}'")
            
            results = drive_client.search_files(
                query=query,
                max_results=request.max_results,
                folder_filter=request.folder_filter
            )
            
            logger.info(f"📁 [{request_id}] Drive results: {len(results)} files")
            return results
            
        except Exception as e:
            logger.error(f"❌ [{request_id}] Drive search error: {e}")
            return []

    def _rerank_results(self, 
                       results: List[Union[GmailMessage, DriveFile]], 
                       spec: SearchSpec, 
                       request_id: str) -> List[RankingResult]:
        """Rerank combined results using hybrid scoring"""
        if not results:
            return []
        
        logger.info(f"🎯 [{request_id}] Reranking {len(results)} combined results")
        
        # Rerank using query terms and language
        ranked_results = self.reranker.rerank_results(
            results=results,
            query_terms=spec.free_text_terms,
            language=spec.language
        )
        
        # Log score statistics
        stats = self.reranker.get_score_statistics(ranked_results)
        logger.info(f"🎯 [{request_id}] Ranking stats: "
                   f"range {stats['score_range']['min']:.3f}-{stats['score_range']['max']:.3f}, "
                   f"mean {stats['score_range']['mean']:.3f}")
        
        return ranked_results

    def _apply_final_filters(self, 
                           ranked_results: List[RankingResult], 
                           request: SearchRequest) -> List[RankingResult]:
        """Apply final filtering and result limits"""
        # Filter by minimum score threshold
        min_score_threshold = float(os.getenv('MIN_SCORE_THRESHOLD', '0.05'))
        filtered_results = self.reranker.filter_by_score_threshold(
            ranked_results, min_score_threshold
        )
        
        # Apply diversification if needed
        max_per_source = max(1, request.max_results // 2)
        diversified_results = self.reranker.diversify_results(
            filtered_results, max_per_source
        )
        
        # Apply final limit
        final_results = diversified_results[:request.max_results]
        
        return final_results

    def _build_response(self, 
                       final_results: List[RankingResult], 
                       spec: SearchSpec, 
                       sources_searched: List[SearchSource], 
                       duration: float, 
                       request_id: str) -> SearchResponse:
        """Build final search response"""
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in final_results]
        
        # Build query interpretation summary
        query_interpretation = {
            "original_query": spec.original_query,
            "processed_query": spec.query_text,
            "language": spec.language,
            "detected_source": spec.source.value,
            "operators": spec.operators,
            "free_text_terms": spec.free_text_terms
        }
        
        # Build performance metrics
        performance_metrics = {
            "duration_seconds": duration,
            "results_returned": len(final_results),
            "sources_searched": [s.value for s in sources_searched],
            "parallel_execution": self.enable_parallel_search,
            "request_id": request_id
        }
        
        return SearchResponse(
            results=result_dicts,
            total_results=len(final_results),
            sources_searched=[s.value for s in sources_searched],
            query_interpretation=query_interpretation,
            performance_metrics=performance_metrics,
            request_id=request_id
        )

    def _update_metrics(self, duration: float):
        """Update internal performance metrics"""
        self._search_count += 1
        self._total_search_time += duration

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get orchestrator performance statistics"""
        avg_time = self._total_search_time / self._search_count if self._search_count > 0 else 0
        
        return {
            "total_searches": self._search_count,
            "total_time_seconds": self._total_search_time,
            "average_time_seconds": avg_time,
            "parallel_enabled": self.enable_parallel_search,
            "max_workers": self.max_workers
        }

    def test_connectivity(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Test connectivity to all search services"""
        logger.info("🔧 Testing search service connectivity...")
        
        results = {
            "gmail": False,
            "drive": False,
            "overall": False
        }
        
        try:
            # Test Gmail
            gmail_client = GmailClient(user_id)
            results["gmail"] = gmail_client.test_connectivity()
        except Exception as e:
            logger.error(f"❌ Gmail connectivity test failed: {e}")
        
        try:
            # Test Drive
            drive_client = DriveClient(user_id)
            results["drive"] = drive_client.test_connectivity()
        except Exception as e:
            logger.error(f"❌ Drive connectivity test failed: {e}")
        
        results["overall"] = results["gmail"] or results["drive"]
        
        if results["overall"]:
            logger.info("✅ Search service connectivity OK")
        else:
            logger.error("❌ No search services available")
        
        return results


# Global orchestrator instance
_orchestrator = None
_orchestrator_lock = None


def get_search_orchestrator() -> HybridSearchOrchestrator:
    """Get singleton HybridSearchOrchestrator instance"""
    global _orchestrator, _orchestrator_lock
    
    if _orchestrator_lock is None:
        import threading
        _orchestrator_lock = threading.Lock()
    
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                # Configure from environment
                max_workers = int(os.getenv('SEARCH_MAX_WORKERS', '2'))
                max_results = int(os.getenv('SEARCH_MAX_RESULTS', '25'))
                parallel_enabled = os.getenv('SEARCH_PARALLEL', 'true').lower() == 'true'
                
                _orchestrator = HybridSearchOrchestrator(
                    max_workers=max_workers,
                    default_max_results=max_results,
                    enable_parallel_search=parallel_enabled
                )
    
    return _orchestrator


# Convenience functions for backward compatibility
def search(query: str, 
          max_results: int = 25, 
          user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple search interface for backward compatibility
    
    Args:
        query: Search query string
        max_results: Maximum results to return
        user_id: Optional user ID
        
    Returns:
        Search results as dictionary
    """
    orchestrator = get_search_orchestrator()
    
    request = SearchRequest(
        query=query,
        max_results=max_results,
        user_id=user_id
    )
    
    response = orchestrator.search(request)
    
    return {
        "success": len(response.results) > 0,
        "results": response.results,
        "total_results": response.total_results,
        "query_interpretation": response.query_interpretation,
        "performance": response.performance_metrics
    }
