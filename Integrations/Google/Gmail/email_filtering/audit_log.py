"""
Audit Logging System
====================

Comprehensive audit logging for email filtering decisions.
Tracks all filtering decisions for analysis, debugging, and system improvement.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FilteringDecision:
    """Represents a single email filtering decision"""
    timestamp: str
    email_id: str
    thread_id: str
    sender_email: str
    subject: str
    decision: str  # 'allowed', 'filtered', 'whitelisted'
    stage: str     # 'stage1_rules', 'stage2_ml', 'whitelist'
    reason: str
    details: str
    confidence_score: Optional[float] = None
    user_id: Optional[str] = None

class FilteringAuditLogger:
    """Manages audit logging for email filtering decisions"""
    
    def __init__(self, log_dir: str = "Gmail/email_filtering"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate log files for different types of decisions
        self.audit_log_file = self.log_dir / "audit_log.jsonl"
        self.review_queue_file = self.log_dir / "review_queue.json"
        
        # In-memory cache for quick statistics
        self.decision_cache = []
        self.cache_max_size = 1000
        
        # Load recent decisions for statistics
        self._load_recent_decisions()
    
    def log_decision(self, decision: FilteringDecision):
        """Log a filtering decision to the audit file"""
        try:
            # Add to cache
            self.decision_cache.append(decision)
            if len(self.decision_cache) > self.cache_max_size:
                self.decision_cache.pop(0)  # Remove oldest
            
            # Write to file (JSONL format for easy processing)
            with open(self.audit_log_file, 'a') as f:
                json.dump(asdict(decision), f)
                f.write('\n')
                
        except Exception as e:
            logger.error(f"Error logging filtering decision: {e}")
    
    def log_email_decision(self, email_data: Dict[str, Any], decision_result: Dict[str, Any], 
                          stage: str, user_id: str = None):
        """
        Log an email filtering decision
        
        Args:
            email_data: Original email data
            decision_result: Result from filtering stage
            stage: Which filtering stage made the decision
            user_id: User ID for multi-user scenarios
        """
        
        # Determine final decision
        if decision_result.get('whitelisted'):
            decision = 'whitelisted'
            reason = decision_result.get('reason', 'whitelist')
        elif decision_result.get('exclude') or not decision_result.get('is_business_relevant', True):
            decision = 'filtered'
            reason = decision_result.get('reason', 'filtered')
        else:
            decision = 'allowed'
            reason = decision_result.get('reason', 'passed_filters')
        
        # Create decision record
        filtering_decision = FilteringDecision(
            timestamp=datetime.now().isoformat(),
            email_id=email_data.get('message_id', ''),
            thread_id=email_data.get('thread_id', ''),
            sender_email=email_data.get('sender_email', ''),
            subject=email_data.get('subject', '')[:100],  # Truncate long subjects
            decision=decision,
            stage=stage,
            reason=reason,
            details=decision_result.get('details', ''),
            confidence_score=decision_result.get('confidence_score'),
            user_id=user_id
        )
        
        self.log_decision(filtering_decision)
    
    def add_to_review_queue(self, email_data: Dict[str, Any], reason: str):
        """Add an email to the review queue for manual evaluation"""
        try:
            review_item = {
                'timestamp': datetime.now().isoformat(),
                'email_id': email_data.get('message_id', ''),
                'sender_email': email_data.get('sender_email', ''),
                'subject': email_data.get('subject', ''),
                'reason': reason,
                'status': 'pending',  # pending, reviewed, approved, rejected
                'body_preview': email_data.get('body', '')[:500]  # First 500 chars
            }
            
            # Load existing queue
            review_queue = self._load_review_queue()
            review_queue.append(review_item)
            
            # Keep only last 100 items
            if len(review_queue) > 100:
                review_queue = review_queue[-100:]
            
            # Save updated queue
            with open(self.review_queue_file, 'w') as f:
                json.dump(review_queue, f, indent=2)
                
            logger.info(f"Added email to review queue: {email_data.get('subject', '')[:50]}")
            
        except Exception as e:
            logger.error(f"Error adding email to review queue: {e}")
    
    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Get current review queue items"""
        return self._load_review_queue()
    
    def update_review_item(self, email_id: str, status: str, feedback: str = None):
        """Update the status of a review queue item"""
        try:
            review_queue = self._load_review_queue()
            
            for item in review_queue:
                if item['email_id'] == email_id:
                    item['status'] = status
                    item['review_timestamp'] = datetime.now().isoformat()
                    if feedback:
                        item['feedback'] = feedback
                    break
            
            with open(self.review_queue_file, 'w') as f:
                json.dump(review_queue, f, indent=2)
                
            logger.info(f"Updated review item {email_id} to status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating review item: {e}")
            return False
    
    def get_filtering_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get filtering statistics for the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Filter recent decisions
            recent_decisions = [
                decision for decision in self.decision_cache
                if datetime.fromisoformat(decision.timestamp) > cutoff_date
            ]
            
            # Calculate statistics
            total_emails = len(recent_decisions)
            if total_emails == 0:
                return {'total_emails': 0, 'message': 'No recent filtering activity'}
            
            allowed = sum(1 for d in recent_decisions if d.decision == 'allowed')
            filtered = sum(1 for d in recent_decisions if d.decision == 'filtered')
            whitelisted = sum(1 for d in recent_decisions if d.decision == 'whitelisted')
            
            # Stage breakdown
            stage1_decisions = sum(1 for d in recent_decisions if d.stage == 'stage1_rules')
            stage2_decisions = sum(1 for d in recent_decisions if d.stage == 'stage2_ml')
            whitelist_decisions = sum(1 for d in recent_decisions if d.stage == 'whitelist')
            
            # Reason breakdown
            reason_counts = {}
            for decision in recent_decisions:
                reason = decision.reason
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            return {
                'period_days': days,
                'total_emails': total_emails,
                'decisions': {
                    'allowed': allowed,
                    'filtered': filtered,
                    'whitelisted': whitelisted
                },
                'percentages': {
                    'allowed_pct': (allowed / total_emails) * 100,
                    'filtered_pct': (filtered / total_emails) * 100,
                    'whitelisted_pct': (whitelisted / total_emails) * 100
                },
                'stage_breakdown': {
                    'stage1_rules': stage1_decisions,
                    'stage2_ml': stage2_decisions,
                    'whitelist': whitelist_decisions
                },
                'top_reasons': sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
        except Exception as e:
            logger.error(f"Error calculating filtering statistics: {e}")
            return {'error': str(e)}
    
    def export_audit_data(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Export audit data for analysis"""
        try:
            decisions = []
            
            # Read all decisions from file
            if self.audit_log_file.exists():
                with open(self.audit_log_file, 'r') as f:
                    for line in f:
                        try:
                            decision_data = json.loads(line.strip())
                            
                            # Filter by date range if provided
                            if start_date or end_date:
                                decision_time = datetime.fromisoformat(decision_data['timestamp'])
                                
                                if start_date and decision_time < datetime.fromisoformat(start_date):
                                    continue
                                if end_date and decision_time > datetime.fromisoformat(end_date):
                                    continue
                            
                            decisions.append(decision_data)
                            
                        except json.JSONDecodeError:
                            continue  # Skip malformed lines
            
            logger.info(f"Exported {len(decisions)} audit records")
            return decisions
            
        except Exception as e:
            logger.error(f"Error exporting audit data: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove audit logs older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            if not self.audit_log_file.exists():
                return
            
            # Read and filter logs
            kept_logs = []
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        decision_data = json.loads(line.strip())
                        decision_time = datetime.fromisoformat(decision_data['timestamp'])
                        
                        if decision_time > cutoff_date:
                            kept_logs.append(line.strip())
                            
                    except (json.JSONDecodeError, ValueError):
                        continue  # Skip malformed lines
            
            # Rewrite file with filtered logs
            with open(self.audit_log_file, 'w') as f:
                for log_line in kept_logs:
                    f.write(log_line + '\n')
            
            removed_count = len(self.decision_cache) - len(kept_logs)
            logger.info(f"Cleaned up {removed_count} old audit log entries")
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
    
    def _load_recent_decisions(self):
        """Load recent decisions into cache for quick statistics"""
        try:
            if not self.audit_log_file.exists():
                return
            
            recent_decisions = []
            cutoff_date = datetime.now() - timedelta(days=7)  # Last 7 days
            
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        decision_data = json.loads(line.strip())
                        decision_time = datetime.fromisoformat(decision_data['timestamp'])
                        
                        if decision_time > cutoff_date:
                            recent_decisions.append(FilteringDecision(**decision_data))
                            
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue  # Skip malformed lines
            
            # Keep most recent decisions in cache
            self.decision_cache = recent_decisions[-self.cache_max_size:]
            
        except Exception as e:
            logger.error(f"Error loading recent decisions: {e}")
    
    def _load_review_queue(self) -> List[Dict[str, Any]]:
        """Load review queue from file"""
        try:
            if self.review_queue_file.exists():
                with open(self.review_queue_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading review queue: {e}")
            return [] 