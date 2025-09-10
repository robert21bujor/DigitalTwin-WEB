"""
Stage 1: Rule-Based Email Filtering
==================================

Fast, deterministic filtering to remove obvious spam, marketing, and non-business emails.
Uses pattern matching and sender analysis for quick decisions.
Supports English and Romanian language filtering.
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RuleBasedFilter:
    """Stage 1: Rule-based email filtering for obvious spam/marketing removal with multi-language support"""
    
    def __init__(self):
        # Excluded Gmail labels (system/promotional)
        self.excluded_labels = {
            'SPAM', 'TRASH', 'PROMOTIONS', 'SOCIAL', 'UPDATES', 
            'FORUMS', 'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL',
            'CATEGORY_UPDATES', 'CATEGORY_FORUMS'
        }
        
        # Marketing/spam subject patterns - English & Romanian
        self.spam_patterns = [
            # English patterns
            r'\b(unsubscribe|newsletter|marketing|promotion)\b',
            r'\b(deal|offer|discount|sale|free)\b',
            r'\b(limited time|act now|click here)\b',
            r'\b(congratulations|winner|claim|prize)\b',
            r'\b(viagra|casino|loan|debt|mortgage)\b',
            r'\$\d+.*\boff\b',  # "$50 off" patterns
            r'\b\d+%\s*(off|discount)\b',  # "50% off" patterns
            r'\[.*promotional.*\]',
            r'\bno[-\s]?reply\b',
            
            # Romanian patterns
            r'\b(dezabonare|dezabonează|newsletter|marketing|promoție|reclamă)\b',
            r'\b(ofertă|reducere|discount|vânzare|gratuit|gratis)\b',
            r'\b(timp limitat|acționează acum|click aici|clic aici)\b',
            r'\b(felicitări|câștigător|revendică|premiu|câștig)\b',
            r'\b(casino|împrumut|datorie|ipotecă|medicament)\b',
            r'\b\d+\s*(lei|ron|euro|eur).*\b(reducere|off)\b',  # "50 lei reducere"
            r'\b\d+%\s*(reducere|discount|off)\b',  # "50% reducere"
            r'\[.*promoțional.*\]',
            r'\b(nu[-\s]?răspunde|no[-\s]?reply|fără[-\s]?răspuns)\b'
        ]
        
        # Promotional sender patterns - English & Romanian
        self.promotional_senders = {
            # English
            'noreply@', 'no-reply@', 'donotreply@', 'do-not-reply@',
            'notifications@', 'newsletter@', 'marketing@', 'promotions@',
            'deals@', 'offers@', 'sales@', 'support@twitter.com',
            'support@linkedin.com', 'support@facebook.com',
            
            # Romanian
            'fara-raspuns@', 'fararaspuns@', 'nu-raspunde@', 'nuraspunde@',
            'notificari@', 'notificare@', 'newsletter@', 'oferte@',
            'promotii@', 'promotie@', 'vanzari@', 'marketing@'
        }
        
        # Auto-generated/system email patterns - English & Romanian
        self.system_patterns = [
            # English
            r'\b(automated|auto[-\s]?generated|do not reply)\b',
            r'\b(calendar|meeting) (invitation|reminder)\b',
            r'\bdelivery (failure|notification)\b',
            r'\bsecurity (alert|notification)\b',
            
            # Romanian
            r'\b(automatizat|auto[-\s]?generat|nu răspunde|fără răspuns)\b',
            r'\b(calendar|întâlnire) (invitație|invitație|reminder|reamintire)\b',
            r'\blivrare (eșuată|notificare|eșec)\b',
            r'\bsecuritate (alertă|notificare|avertisment)\b',
            r'\b(confirmare|confirmă) (cont|contul|email|e-mail)\b',  # Account confirmations
            r'\b(resetare|resetează) (parolă|parola)\b'  # Password resets
        ]
        
        # Romanian promotional keywords for body scanning
        self.romanian_promotional_keywords = [
            'cumpără acum', 'comandă acum', 'profită acum', 'doar astăzi',
            'ofertă limitată', 'promoție specială', 'reducere masivă',
            'cel mai mic preț', 'transport gratuit', 'livrare gratuită',
            'ultima șansă', 'stoc limitat', 'nu rata', 'exclusiv pentru tine'
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_spam_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.spam_patterns]
        self.compiled_system_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.system_patterns]
        self.compiled_romanian_promotional = [re.compile(pattern, re.IGNORECASE) 
                                             for pattern in self.romanian_promotional_keywords]

    def should_exclude_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if email should be excluded based on rules with multi-language support
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with decision and reasoning
        """
        
        subject = email_data.get('subject', '').strip()
        sender_email = email_data.get('sender_email', '').lower()
        body = email_data.get('body', '')
        labels = email_data.get('labels', [])
        
        # Check 1: Gmail labels
        if any(label in self.excluded_labels for label in labels):
            return {
                'exclude': True,
                'reason': 'gmail_label',
                'details': f"Gmail labeled as: {[l for l in labels if l in self.excluded_labels]}"
            }
        
        # Check 2: Promotional sender patterns (English & Romanian)
        for pattern in self.promotional_senders:
            if pattern in sender_email:
                return {
                    'exclude': True,
                    'reason': 'promotional_sender',
                    'details': f"Sender matches promotional pattern: {pattern}"
                }
        
        # Check 3: Marketing/spam subject patterns (English & Romanian)
        for pattern in self.compiled_spam_patterns:
            if pattern.search(subject):
                return {
                    'exclude': True,
                    'reason': 'spam_subject',
                    'details': f"Subject matches spam pattern: {pattern.pattern}"
                }
        
        # Check 4: Marketing patterns in email body (first 500 chars) - English & Romanian
        body_sample = body[:500].lower()
        for pattern in self.compiled_spam_patterns:
            if pattern.search(body_sample):
                return {
                    'exclude': True,
                    'reason': 'spam_body',
                    'details': f"Body matches spam pattern: {pattern.pattern}"
                }
        
        # Check 5: Romanian promotional keywords in body
        for pattern in self.compiled_romanian_promotional:
            if pattern.search(body_sample):
                return {
                    'exclude': True,
                    'reason': 'romanian_promotional',
                    'details': f"Body matches Romanian promotional pattern: {pattern.pattern}"
                }
        
        # Check 6: System/automated email patterns (English & Romanian)
        combined_text = f"{subject} {body_sample}"
        for pattern in self.compiled_system_patterns:
            if pattern.search(combined_text):
                return {
                    'exclude': True,
                    'reason': 'automated_system',
                    'details': f"Content matches system pattern: {pattern.pattern}"
                }
        
        # If none of the exclusion criteria are met, allow the email to proceed
        return {
            'exclude': False,
            'reason': 'passed_stage1',
            'details': 'Email passed all stage 1 rule-based filters'
        }
    
    def get_filter_stats(self) -> Dict[str, int]:
        """Get statistics about the filter configuration"""
        return {
            'spam_patterns': len(self.spam_patterns),
            'promotional_senders': len(self.promotional_senders),
            'system_patterns': len(self.system_patterns),
            'romanian_promotional_keywords': len(self.romanian_promotional_keywords),
            'excluded_labels': len(self.excluded_labels)
        }
    
    def is_likely_romanian(self, text: str) -> bool:
        """Quick check if text contains Romanian language elements"""
        if not text:
            return False
        
        # Check for Romanian diacritics and common words
        romanian_indicators = [
            r'[ăâîșțĂÂÎȘȚ]',  # Romanian diacritics
            r'\b(și|să|cu|în|la|de|pe|pentru|din|prin)\b',
            r'\b(este|sunt|mulțumesc|vă rog)\b'
        ]
        
        text_lower = text.lower()
        romanian_count = 0
        
        for pattern in romanian_indicators:
            if re.search(pattern, text_lower, re.IGNORECASE):
                romanian_count += 1
        
        return romanian_count >= 2  # At least 2 indicators suggest Romanian 