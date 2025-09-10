"""
Hybrid Reranker for Gmail and Drive Search Results
Deterministic reranking with lexical overlap + recency half-life + diacritic support
"""

import logging
import math
import re
import unicodedata
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from .gmail_client import GmailMessage
from .drive_client import DriveFile

logger = logging.getLogger(__name__)


@dataclass
class RankingResult:
    """Result with ranking score"""
    item: Union[GmailMessage, DriveFile]
    score: float
    score_breakdown: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        result = self.item.to_dict()
        result.update({
            "ranking_score": self.score,
            "score_breakdown": self.score_breakdown
        })
        return result


class HybridReranker:
    """
    Production-grade reranker with configurable scoring components
    """
    
    def __init__(self, 
                 recency_halflife_days: int = 30,
                 lexical_weight: float = 0.6,
                 recency_weight: float = 0.4,
                 diacritic_insensitive: bool = True):
        """
        Initialize reranker with configurable weights
        
        Args:
            recency_halflife_days: Days for recency score to halve
            lexical_weight: Weight for lexical similarity (0-1)
            recency_weight: Weight for recency score (0-1) 
            diacritic_insensitive: Whether to ignore Romanian diacritics
        """
        self.recency_halflife_days = recency_halflife_days
        self.lexical_weight = lexical_weight
        self.recency_weight = recency_weight
        self.diacritic_insensitive = diacritic_insensitive
        
        # Normalize weights
        total_weight = lexical_weight + recency_weight
        if total_weight > 0:
            self.lexical_weight = lexical_weight / total_weight
            self.recency_weight = recency_weight / total_weight
        
        logger.info(f"🎯 HybridReranker initialized: lexical={self.lexical_weight:.2f}, "
                   f"recency={self.recency_weight:.2f}, halflife={recency_halflife_days}d")

    def rerank_results(self, 
                      results: List[Union[GmailMessage, DriveFile]], 
                      query_terms: List[str],
                      language: str = "auto") -> List[RankingResult]:
        """
        Rerank search results using hybrid scoring
        
        Args:
            results: List of Gmail or Drive results
            query_terms: Original query terms for lexical matching
            language: Query language for diacritic expansion
            
        Returns:
            List of RankingResult objects sorted by score (highest first)
        """
        logger.info(f"🎯 Reranking {len(results)} results with {len(query_terms)} query terms")
        
        if not results:
            return []
        
        # Expand query terms for diacritic matching
        expanded_terms = self._expand_query_terms(query_terms, language)
        
        # Score all results
        ranking_results = []
        for result in results:
            score, breakdown = self._calculate_score(result, expanded_terms)
            ranking_results.append(RankingResult(
                item=result,
                score=score,
                score_breakdown=breakdown
            ))
        
        # Sort by score (highest first)
        ranking_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"✅ Reranking completed: scores range {ranking_results[-1].score:.3f} - {ranking_results[0].score:.3f}")
        
        return ranking_results

    def _expand_query_terms(self, query_terms: List[str], language: str) -> List[str]:
        """Expand query terms with diacritic variants for Romanian"""
        expanded = []
        
        for term in query_terms:
            expanded.append(term.lower())
            
            if self.diacritic_insensitive and language == "ro":
                stripped = self._strip_diacritics(term.lower())
                if stripped != term.lower():
                    expanded.append(stripped)
        
        return expanded

    def _calculate_score(self, 
                        result: Union[GmailMessage, DriveFile], 
                        expanded_terms: List[str]) -> tuple[float, Dict[str, float]]:
        """Calculate hybrid score for a single result"""
        # Calculate individual component scores
        lexical_score = self._calculate_lexical_score(result, expanded_terms)
        recency_score = self._calculate_recency_score(result)
        
        # Calculate weighted total
        total_score = (
            self.lexical_weight * lexical_score +
            self.recency_weight * recency_score
        )
        
        breakdown = {
            "lexical": lexical_score,
            "recency": recency_score,
            "total": total_score,
            "lexical_weight": self.lexical_weight,
            "recency_weight": self.recency_weight
        }
        
        return total_score, breakdown

    def _calculate_lexical_score(self, 
                                result: Union[GmailMessage, DriveFile], 
                                expanded_terms: List[str]) -> float:
        """Calculate lexical overlap score"""
        if not expanded_terms:
            return 0.0
        
        # Get searchable text from result
        searchable_text = self._get_searchable_text(result).lower()
        
        # Count term matches
        matches = 0
        total_terms = len(expanded_terms)
        
        for term in expanded_terms:
            if term in searchable_text:
                matches += 1
        
        # Calculate overlap ratio
        overlap_ratio = matches / total_terms if total_terms > 0 else 0.0
        
        # Apply TF-like boost for multiple occurrences
        boosted_score = self._apply_frequency_boost(searchable_text, expanded_terms, overlap_ratio)
        
        return min(boosted_score, 1.0)  # Cap at 1.0

    def _get_searchable_text(self, result: Union[GmailMessage, DriveFile]) -> str:
        """Extract searchable text from result"""
        if isinstance(result, GmailMessage):
            # For Gmail: subject + sender + snippet + content
            parts = [
                result.subject,
                result.sender,
                result.snippet,
                result.content
            ]
        else:  # DriveFile
            # For Drive: name + description + folder_path
            parts = [
                result.name,
                result.description or "",
                result.folder_path
            ]
        
        return " ".join(part for part in parts if part)

    def _apply_frequency_boost(self, 
                              text: str, 
                              terms: List[str], 
                              base_score: float) -> float:
        """Apply frequency-based boost to lexical score"""
        if base_score == 0:
            return 0.0
        
        # Count total occurrences of all terms
        total_occurrences = sum(text.count(term) for term in terms)
        
        # Apply logarithmic boost for frequency
        frequency_boost = 1 + math.log(1 + total_occurrences) * 0.1
        
        return base_score * frequency_boost

    def _calculate_recency_score(self, result: Union[GmailMessage, DriveFile]) -> float:
        """Calculate recency score using exponential decay"""
        try:
            # Get the relevant date
            if isinstance(result, GmailMessage):
                item_date = result.date
            else:  # DriveFile
                item_date = result.modified_time
            
            # Calculate age in days
            now = datetime.now(item_date.tzinfo) if item_date.tzinfo else datetime.now()
            age_days = (now - item_date).total_seconds() / (24 * 3600)
            
            # Apply exponential decay with configurable half-life
            # Score = 0.5^(age_days / halflife_days)
            recency_score = 0.5 ** (age_days / self.recency_halflife_days)
            
            return recency_score
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate recency score: {e}")
            return 0.5  # Default moderate score

    def _strip_diacritics(self, text: str) -> str:
        """Strip Romanian diacritics for matching"""
        # Romanian diacritic mappings
        diacritic_map = {
            'ș': 's', 'ş': 's', 'Ș': 'S', 'Ş': 'S',
            'ț': 't', 'ţ': 't', 'Ț': 'T', 'Ţ': 'T',
            'ă': 'a', 'Ă': 'A',
            'â': 'a', 'Â': 'A', 
            'î': 'i', 'Î': 'I'
        }
        
        result = text
        for diacritic, replacement in diacritic_map.items():
            result = result.replace(diacritic, replacement)
        
        return result

    def get_score_statistics(self, ranking_results: List[RankingResult]) -> Dict[str, Any]:
        """Get statistical summary of ranking scores"""
        if not ranking_results:
            return {}
        
        scores = [r.score for r in ranking_results]
        lexical_scores = [r.score_breakdown["lexical"] for r in ranking_results]
        recency_scores = [r.score_breakdown["recency"] for r in ranking_results]
        
        return {
            "total_results": len(ranking_results),
            "score_range": {
                "min": min(scores),
                "max": max(scores),
                "mean": sum(scores) / len(scores),
                "median": sorted(scores)[len(scores) // 2]
            },
            "lexical_range": {
                "min": min(lexical_scores),
                "max": max(lexical_scores),
                "mean": sum(lexical_scores) / len(lexical_scores)
            },
            "recency_range": {
                "min": min(recency_scores),
                "max": max(recency_scores),
                "mean": sum(recency_scores) / len(recency_scores)
            },
            "weights": {
                "lexical": self.lexical_weight,
                "recency": self.recency_weight
            }
        }

    def filter_by_score_threshold(self, 
                                 ranking_results: List[RankingResult], 
                                 min_score: float = 0.1) -> List[RankingResult]:
        """Filter results by minimum score threshold"""
        filtered = [r for r in ranking_results if r.score >= min_score]
        
        logger.info(f"🎯 Score filtering: {len(filtered)}/{len(ranking_results)} results above {min_score}")
        
        return filtered

    def diversify_results(self, 
                         ranking_results: List[RankingResult], 
                         max_per_source: int = 10) -> List[RankingResult]:
        """Diversify results to balance Gmail vs Drive sources"""
        gmail_results = []
        drive_results = []
        
        # Separate by source
        for result in ranking_results:
            if isinstance(result.item, GmailMessage):
                gmail_results.append(result)
            else:
                drive_results.append(result)
        
        # Take top N from each source
        top_gmail = gmail_results[:max_per_source]
        top_drive = drive_results[:max_per_source]
        
        # Merge and re-sort by score
        diversified = top_gmail + top_drive
        diversified.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"🎯 Diversified results: {len(top_gmail)} Gmail + {len(top_drive)} Drive")
        
        return diversified


# Factory function for easy instantiation
def create_reranker(recency_halflife_days: Optional[int] = None,
                   lexical_weight: Optional[float] = None,
                   recency_weight: Optional[float] = None) -> HybridReranker:
    """
    Create reranker with optional custom parameters
    
    Args:
        recency_halflife_days: Override default recency half-life
        lexical_weight: Override default lexical weight
        recency_weight: Override default recency weight
        
    Returns:
        Configured HybridReranker instance
    """
    import os
    
    # Use environment variables or defaults
    halflife = recency_halflife_days or int(os.getenv('RECENCY_HALFLIFE_DAYS', '30'))
    lex_weight = lexical_weight or float(os.getenv('LEXICAL_WEIGHT', '0.6'))
    rec_weight = recency_weight or float(os.getenv('RECENCY_WEIGHT', '0.4'))
    
    return HybridReranker(
        recency_halflife_days=halflife,
        lexical_weight=lex_weight,
        recency_weight=rec_weight
    )
