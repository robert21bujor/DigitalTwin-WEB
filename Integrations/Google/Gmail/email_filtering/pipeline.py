"""
Two-Stage Email Filtering Pipeline
=================================

Main orchestrator for the email filtering system.
Coordinates rule-based filtering, ML classification, whitelist checking, and audit logging.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .filters import RuleBasedFilter
from .classifier import EmailRelevanceClassifier
from .whitelist import WhitelistManager
from .audit_log import FilteringAuditLogger

logger = logging.getLogger(__name__)

class EmailFilteringPipeline:
    """Main two-stage email filtering pipeline"""
    
    def __init__(self, organization_domain: str = None, user_id: str = None):
        """
        Initialize the filtering pipeline
        
        Args:
            organization_domain: Domain for internal email detection (e.g., 'repsmate.com')
            user_id: User ID for audit logging and personalization
        """
        self.organization_domain = organization_domain
        self.user_id = user_id
        
        # Initialize filtering components
        self.rule_filter = RuleBasedFilter()
        self.ml_classifier = EmailRelevanceClassifier(organization_domain)
        self.whitelist = WhitelistManager()
        self.audit_logger = FilteringAuditLogger()
        
        # Configuration
        self.config = {
            'ml_threshold': 0.4,         # Minimum score for ML classification
            'review_threshold_low': 0.2,  # Below this goes to review queue
            'review_threshold_high': 0.6, # Above this gets approved
            'enable_whitelist': True,
            'enable_audit_logging': True,
            'organization_bypass': True   # Always allow internal emails
        }
        
        logger.info(f"Initialized email filtering pipeline for organization: {organization_domain}")
    
    def process_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of emails through the filtering pipeline
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Dictionary with processing results
        """
        
        results = {
            'total_processed': len(emails),
            'allowed': [],
            'filtered': [],
            'whitelisted': [],
            'review_queue': [],
            'errors': [],
            'statistics': {
                'stage1_filtered': 0,
                'stage2_filtered': 0,
                'whitelist_allowed': 0,
                'ml_allowed': 0,
                'organization_bypass': 0
            }
        }
        
        logger.info(f"🔄 Processing {len(emails)} emails through filtering pipeline")
        
        for i, email_data in enumerate(emails, 1):
            try:
                logger.debug(f"📧 Processing email {i}/{len(emails)}: {email_data.get('subject', '')[:50]}...")
                
                # Process single email
                decision = self.process_single_email(email_data)
                
                # Categorize result
                if decision['final_decision'] == 'whitelisted':
                    results['whitelisted'].append({**email_data, **decision})
                    results['statistics']['whitelist_allowed'] += 1
                elif decision['final_decision'] == 'allowed':
                    results['allowed'].append({**email_data, **decision})
                    if decision.get('bypass_reason') == 'organization':
                        results['statistics']['organization_bypass'] += 1
                    else:
                        results['statistics']['ml_allowed'] += 1
                elif decision['final_decision'] == 'filtered':
                    results['filtered'].append({**email_data, **decision})
                    if decision.get('filtered_stage') == 'stage1':
                        results['statistics']['stage1_filtered'] += 1
                    else:
                        results['statistics']['stage2_filtered'] += 1
                elif decision['final_decision'] == 'review':
                    results['review_queue'].append({**email_data, **decision})
                    # Add to audit logger's review queue
                    if self.config['enable_audit_logging']:
                        self.audit_logger.add_to_review_queue(email_data, decision.get('reason', 'uncertain'))
                
            except Exception as e:
                error_msg = f"Error processing email {i}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append({
                    'email_index': i,
                    'error': error_msg,
                    'subject': email_data.get('subject', 'Unknown')
                })
        
        # Log summary
        logger.info(f"✅ Filtering complete: {len(results['allowed'])} allowed, "
                   f"{len(results['filtered'])} filtered, {len(results['whitelisted'])} whitelisted, "
                   f"{len(results['review_queue'])} for review")
        
        return results
    
    def process_single_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single email through the complete filtering pipeline
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with filtering decision and details
        """
        
        decision = {
            'timestamp': datetime.now().isoformat(),
            'email_id': email_data.get('message_id', ''),
            'stages_processed': [],
            'final_decision': None,
            'confidence': 0.0,
            'reasoning': []
        }
        
        try:
            # Stage 0: Whitelist Check (highest priority)
            if self.config['enable_whitelist']:
                whitelist_result = self.whitelist.is_whitelisted(email_data)
                decision['stages_processed'].append('whitelist')
                
                if whitelist_result['whitelisted']:
                    decision['final_decision'] = 'whitelisted'
                    decision['confidence'] = 1.0
                    decision['reason'] = whitelist_result['reason']
                    decision['details'] = whitelist_result['details']
                    
                    # Log decision
                    if self.config['enable_audit_logging']:
                        self.audit_logger.log_email_decision(
                            email_data, whitelist_result, 'whitelist', self.user_id
                        )
                    
                    return decision
            
            # Organization bypass - always allow internal emails
            if self.config['organization_bypass'] and self.organization_domain:
                sender_email = email_data.get('sender_email', '').lower()
                if self.organization_domain in sender_email:
                    decision['final_decision'] = 'allowed'
                    decision['confidence'] = 0.9
                    decision['reason'] = 'organization_internal'
                    decision['details'] = f"Internal email from {self.organization_domain}"
                    decision['bypass_reason'] = 'organization'
                    
                    # Log decision
                    if self.config['enable_audit_logging']:
                        org_result = {'is_business_relevant': True, 'reason': 'organization_internal'}
                        self.audit_logger.log_email_decision(
                            email_data, org_result, 'organization_bypass', self.user_id
                        )
                    
                    return decision
            
            # Stage 1: Rule-Based Filtering
            stage1_result = self.rule_filter.should_exclude_email(email_data)
            decision['stages_processed'].append('stage1_rules')
            
            if stage1_result['exclude']:
                decision['final_decision'] = 'filtered'
                decision['confidence'] = 0.8
                decision['reason'] = stage1_result['reason']
                decision['details'] = stage1_result['details']
                decision['filtered_stage'] = 'stage1'
                
                # Log decision
                if self.config['enable_audit_logging']:
                    self.audit_logger.log_email_decision(
                        email_data, stage1_result, 'stage1_rules', self.user_id
                    )
                
                return decision
            
            # Stage 2: ML-Based Classification
            stage2_result = self.ml_classifier.classify_relevance(email_data)
            decision['stages_processed'].append('stage2_ml')
            decision['confidence'] = stage2_result['confidence_score']
            decision['ml_details'] = stage2_result['scoring_details']
            
            # Decision logic based on ML confidence
            if stage2_result['is_business_relevant']:
                if stage2_result['confidence_score'] >= self.config['review_threshold_high']:
                    # High confidence - allow
                    decision['final_decision'] = 'allowed'
                    decision['reason'] = f"ML classified as {stage2_result['relevance_level']} relevance"
                    decision['details'] = f"Confidence: {stage2_result['confidence_score']:.2f}"
                elif stage2_result['confidence_score'] >= self.config['review_threshold_low']:
                    # Medium confidence - review queue
                    decision['final_decision'] = 'review'
                    decision['reason'] = 'ml_uncertain'
                    decision['details'] = f"Uncertain classification, confidence: {stage2_result['confidence_score']:.2f}"
                else:
                    # Low confidence - filter
                    decision['final_decision'] = 'filtered'
                    decision['reason'] = 'ml_low_confidence'
                    decision['details'] = f"Low business relevance, confidence: {stage2_result['confidence_score']:.2f}"
                    decision['filtered_stage'] = 'stage2'
            else:
                # Not business relevant
                decision['final_decision'] = 'filtered'
                decision['reason'] = 'ml_not_relevant'
                decision['details'] = f"Not business relevant, confidence: {stage2_result['confidence_score']:.2f}"
                decision['filtered_stage'] = 'stage2'
            
            # Log decision
            if self.config['enable_audit_logging']:
                self.audit_logger.log_email_decision(
                    email_data, stage2_result, 'stage2_ml', self.user_id
                )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in filtering pipeline: {e}")
            # Default to review queue on errors
            decision['final_decision'] = 'review'
            decision['reason'] = 'pipeline_error'
            decision['details'] = f"Error in filtering: {str(e)}"
            return decision
    
    def update_configuration(self, new_config: Dict[str, Any]):
        """Update pipeline configuration"""
        self.config.update(new_config)
        logger.info(f"Updated pipeline configuration: {new_config}")
    
    def update_organization_domain(self, domain: str):
        """Update organization domain for internal email detection"""
        self.organization_domain = domain
        self.ml_classifier.update_organization_domain(domain)
        logger.info(f"Updated organization domain to: {domain}")
    
    def get_filtering_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive filtering statistics"""
        if not self.config['enable_audit_logging']:
            return {'error': 'Audit logging is disabled'}
        
        return self.audit_logger.get_filtering_statistics(days)
    
    def add_whitelist_domain(self, domain: str) -> bool:
        """Add a domain to the whitelist"""
        return self.whitelist.add_trusted_domain(domain)
    
    def add_whitelist_sender(self, sender_email: str) -> bool:
        """Add a sender to the whitelist"""
        return self.whitelist.add_trusted_sender(sender_email)
    
    def submit_feedback(self, email_id: str, correct_decision: str, feedback: str = None) -> bool:
        """Submit feedback for improving the filtering system"""
        if not self.config['enable_audit_logging']:
            return False
        
        return self.audit_logger.update_review_item(email_id, correct_decision, feedback)
    
    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Get items in the review queue"""
        if not self.config['enable_audit_logging']:
            return []
        
        return self.audit_logger.get_review_queue()
    
    def export_filtering_decisions(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Export filtering decisions for analysis"""
        if not self.config['enable_audit_logging']:
            return []
        
        return self.audit_logger.export_audit_data(start_date, end_date)
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the current pipeline configuration"""
        return {
            'organization_domain': self.organization_domain,
            'user_id': self.user_id,
            'configuration': self.config,
            'components': {
                'rule_filter_stats': self.rule_filter.get_filter_stats(),
                'ml_classifier_stats': self.ml_classifier.get_classification_stats(),
                'whitelist_stats': self.whitelist.get_whitelist_stats()
            },
            'pipeline_version': '2.0',
            'stages': ['whitelist', 'organization_bypass', 'stage1_rules', 'stage2_ml']
        } 