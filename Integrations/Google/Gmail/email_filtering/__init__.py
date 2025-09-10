"""
Email Filtering Package
=======================

Two-stage email filtering system for business-relevant email classification:
- Stage 1: Rule-based filtering (fast spam/promotional removal)
- Stage 2: ML-based heuristic classification
- Whitelist management for trusted sources
- Comprehensive audit logging
"""

try:
    from Integrations.Google.Gmail.email_filtering.pipeline import EmailFilteringPipeline
    from Integrations.Google.Gmail.email_filtering.filters import RuleBasedFilter
    from Integrations.Google.Gmail.email_filtering.classifier import EmailRelevanceClassifier
    from Integrations.Google.Gmail.email_filtering.whitelist import WhitelistManager
    from Integrations.Google.Gmail.email_filtering.audit_log import FilteringAuditLogger, FilteringDecision
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Integrations.Google.Gmail.email_filtering.pipeline import EmailFilteringPipeline
    from Integrations.Google.Gmail.email_filtering.filters import RuleBasedFilter
    from Integrations.Google.Gmail.email_filtering.classifier import EmailRelevanceClassifier
    from Integrations.Google.Gmail.email_filtering.whitelist import WhitelistManager
    from Integrations.Google.Gmail.email_filtering.audit_log import FilteringAuditLogger, FilteringDecision

__all__ = [
    'EmailFilteringPipeline',
    'RuleBasedFilter', 
    'EmailRelevanceClassifier',
    'WhitelistManager',
    'FilteringAuditLogger',
    'FilteringDecision'
]

__version__ = '2.0.0' 