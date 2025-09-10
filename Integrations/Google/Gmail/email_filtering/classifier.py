"""
Stage 2: ML-Based Email Relevance Classification
===============================================

Heuristic-based classification for emails that passed Stage 1 rule-based filtering.
Uses content analysis and sender patterns to determine business relevance.
Supports English and Romanian language filtering.
"""

import logging
import re
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
import email.utils

logger = logging.getLogger(__name__)

class EmailRelevanceClassifier:
    """Stage 2: ML-based email relevance classification using heuristics with multi-language support"""
    
    def __init__(self, organization_domain: str = None):
        self.organization_domain = organization_domain or "repsmate.com"
        
        # Business relevance indicators (positive signals) - English
        self.business_keywords_en = {
            'high_priority': [
                'meeting', 'call', 'project', 'deadline', 'urgent', 'asap',
                'contract', 'agreement', 'proposal', 'invoice', 'payment',
                'client', 'customer', 'delivery', 'implementation', 'support'
            ],
            'medium_priority': [
                'schedule', 'appointment', 'follow-up', 'update', 'status',
                'review', 'feedback', 'discussion', 'collaboration', 'partnership',
                'opportunity', 'requirements', 'specification', 'analysis'
            ],
            'low_priority': [
                'information', 'notification', 'announcement', 'newsletter',
                'report', 'summary', 'documentation', 'training', 'event'
            ]
        }
        
        # Business relevance indicators - Romanian
        self.business_keywords_ro = {
            'high_priority': [
                'întâlnire', 'apel', 'proiect', 'termen', 'urgent', 'cât mai repede',
                'contract', 'acord', 'propunere', 'factură', 'plată', 'plați',
                'client', 'clienți', 'customer', 'livrare', 'implementare', 'suport'
            ],
            'medium_priority': [
                'programare', 'programarea', 'urmărire', 'actualizare', 'status', 'stare',
                'revizuire', 'feedback', 'discuție', 'colaborare', 'parteneriat',
                'oportunitate', 'cerințe', 'specificație', 'analiză', 'analize'
            ],
            'low_priority': [
                'informație', 'informații', 'notificare', 'anunț', 'newsletter',
                'raport', 'rezumat', 'documentație', 'training', 'antrenament', 'eveniment'
            ]
        }
        
        # Combined business keywords for compatibility
        self.business_keywords = self._merge_keywords(self.business_keywords_en, self.business_keywords_ro)
        
        # Client/business sender indicators
        self.business_sender_patterns = [
            r'\b(sales|support|info|contact|business|admin)@',
            r'\b(manager|director|ceo|cto|vp|lead)[\w.]*@',
            r'@(company|corp|inc|ltd|llc)\.',
            r'@[a-z]+\.(com|org|net|co\.|de|uk|ro)$'  # Added .ro for Romanian domains
        ]
        
        # Internal collaboration indicators - English & Romanian
        self.collaboration_indicators = [
            # English
            'shared', 'document', 'file', 'link', 'access', 'permission',
            'google drive', 'dropbox', 'onedrive', 'confluence', 'jira',
            'github', 'gitlab', 'slack', 'teams', 'zoom', 'meet',
            # Romanian
            'partajat', 'document', 'fișier', 'link', 'acces', 'permisiune',
            'drive', 'confluence', 'github', 'gitlab', 'slack', 'teams'
        ]
        
        # Romanian language detection patterns
        self.romanian_patterns = [
            r'\b(și|să|cu|în|la|de|pe|pentru|din|prin|către|după|înainte)\b',
            r'\b(este|sunt|era|erau|va|vor|poate|trebuie|astfel)\b',
            r'\b(acesta|aceasta|acestea|acest|această|aceste)\b',
            r'\b(îți|îmi|își|își|vă|ne|le)\b',
            r'\b(mulțumesc|mulțumim|vă rog|te rog)\b',
            r'[ăâîșțĂÂÎȘȚ]',  # Romanian diacritics
        ]
        
        # Compile patterns
        self.compiled_sender_patterns = [re.compile(pattern, re.IGNORECASE) 
                                       for pattern in self.business_sender_patterns]
        self.compiled_romanian_patterns = [re.compile(pattern, re.IGNORECASE)
                                         for pattern in self.romanian_patterns]
        
        # Relevance thresholds
        self.relevance_thresholds = {
            'high': 0.8,      # Definitely business relevant
            'medium': 0.5,    # Likely business relevant  
            'low': 0.2        # Possibly business relevant
        }
    
    def _merge_keywords(self, keywords_en: Dict, keywords_ro: Dict) -> Dict:
        """Merge English and Romanian keywords"""
        merged = {}
        for category in keywords_en:
            merged[category] = keywords_en[category] + keywords_ro.get(category, [])
        return merged
    
    def detect_language(self, text: str) -> str:
        """Detect if text is Romanian or English"""
        if not text:
            return 'unknown'
        
        # Count Romanian language indicators
        romanian_score = 0
        text_lower = text.lower()
        
        for pattern in self.compiled_romanian_patterns:
            matches = len(pattern.findall(text_lower))
            romanian_score += matches
        
        # Simple threshold-based detection
        # If we find Romanian patterns, consider it Romanian
        if romanian_score >= 3:  # At least 3 Romanian indicators
            return 'romanian'
        elif romanian_score > 0:
            return 'mixed'  # Some Romanian elements
        else:
            return 'english'  # Default to English
    
    def classify_relevance(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify email business relevance using heuristic analysis with language support
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with classification results
        """
        
        subject = email_data.get('subject', '').lower()
        sender_email = email_data.get('sender_email', '').lower()
        body = email_data.get('body', '').lower()
        timestamp = email_data.get('timestamp')
        
        # Detect language
        combined_text = f"{subject} {body[:500]}"
        detected_language = self.detect_language(combined_text)
        
        # Calculate relevance score
        score = 0.0
        scoring_details = []
        
        # Factor 1: Sender analysis (0-0.4 points)
        sender_score = self._analyze_sender(sender_email)
        score += sender_score
        if sender_score > 0:
            scoring_details.append(f"Sender: +{sender_score:.2f}")
        
        # Factor 2: Content analysis (0-0.4 points)  
        content_score = self._analyze_content(subject, body, detected_language)
        score += content_score
        if content_score > 0:
            scoring_details.append(f"Content: +{content_score:.2f}")
        
        # Factor 3: Recency bonus (0-0.1 points)
        recency_score = self._analyze_recency(timestamp)
        score += recency_score
        if recency_score > 0:
            scoring_details.append(f"Recency: +{recency_score:.2f}")
        
        # Factor 4: Thread/conversation analysis (0-0.1 points)
        thread_score = self._analyze_thread_context(email_data)
        score += thread_score
        if thread_score > 0:
            scoring_details.append(f"Thread: +{thread_score:.2f}")
        
        # Factor 5: Language bonus for Romanian business emails
        if detected_language == 'romanian':
            score += 0.05  # Small bonus for Romanian business emails
            scoring_details.append("Language: +0.05 (Romanian)")
        
        # Determine relevance level
        if score >= self.relevance_thresholds['high']:
            relevance = 'high'
            is_business_relevant = True
        elif score >= self.relevance_thresholds['medium']:
            relevance = 'medium'
            is_business_relevant = True
        elif score >= self.relevance_thresholds['low']:
            relevance = 'low'
            is_business_relevant = True
        else:
            relevance = 'irrelevant'
            is_business_relevant = False
        
        return {
            'is_business_relevant': is_business_relevant,
            'relevance_level': relevance,
            'confidence_score': min(score, 1.0),  # Cap at 1.0
            'scoring_details': scoring_details,
            'detected_language': detected_language,
            'classification_method': 'heuristic_ml_multilang'
        }
    
    def _analyze_sender(self, sender_email: str) -> float:
        """Analyze sender for business relevance indicators"""
        score = 0.0
        
        # Internal emails (same organization)
        if self.organization_domain and self.organization_domain in sender_email:
            score += 0.3  # High score for internal emails
        
        # Business sender patterns
        for pattern in self.compiled_sender_patterns:
            if pattern.search(sender_email):
                score += 0.2
                break
        
        # Professional domains vs. personal domains
        domain = sender_email.split('@')[1] if '@' in sender_email else ''
        if domain:
            personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
            if domain not in personal_domains:
                score += 0.1  # Professional domain bonus
        
        return min(score, 0.4)  # Cap sender score at 0.4
    
    def _analyze_content(self, subject: str, body: str, language: str = 'english') -> float:
        """Analyze email content for business relevance with language awareness"""
        score = 0.0
        
        # Combine subject and first 1000 chars of body for analysis
        content = f"{subject} {body[:1000]}"
        
        # Choose appropriate keyword set based on detected language
        if language == 'romanian':
            keywords = self.business_keywords_ro
            # Higher weight for Romanian keywords when language is detected as Romanian
            multiplier = 1.2
        else:
            keywords = self.business_keywords_en
            multiplier = 1.0
        
        # High priority keywords
        high_matches = sum(1 for keyword in keywords['high_priority'] 
                          if keyword in content)
        score += high_matches * 0.15 * multiplier
        
        # Medium priority keywords  
        medium_matches = sum(1 for keyword in keywords['medium_priority']
                           if keyword in content)
        score += medium_matches * 0.08 * multiplier
        
        # Low priority keywords
        low_matches = sum(1 for keyword in keywords['low_priority']
                         if keyword in content)
        score += low_matches * 0.03 * multiplier
        
        # Collaboration indicators
        collab_matches = sum(1 for keyword in self.collaboration_indicators
                           if keyword in content)
        score += collab_matches * 0.05
        
        return min(score, 0.4)  # Cap content score at 0.4
    
    def _analyze_recency(self, timestamp) -> float:
        """Give bonus points for recent emails"""
        if not timestamp:
            return 0.0
        
        try:
            if isinstance(timestamp, str):
                email_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                email_date = timestamp
            
            days_ago = (datetime.now() - email_date.replace(tzinfo=None)).days
            
            if days_ago <= 1:
                return 0.1  # Very recent
            elif days_ago <= 7:
                return 0.05  # Recent
            else:
                return 0.0  # Older emails
                
        except Exception:
            return 0.0
    
    def _analyze_thread_context(self, email_data: Dict[str, Any]) -> float:
        """Analyze thread context for conversation indicators"""
        score = 0.0
        
        subject = email_data.get('subject', '').lower()
        
        # Check for reply/forward indicators
        if any(prefix in subject for prefix in ['re:', 'fwd:', 'fw:']):
            score += 0.05  # Part of ongoing conversation
        
        # Check for thread_id (indicates conversation)
        if email_data.get('thread_id'):
            score += 0.02
        
        return min(score, 0.1)  # Cap thread score at 0.1
    
    def update_organization_domain(self, domain: str):
        """Update the organization domain for internal email detection"""
        self.organization_domain = domain
        logger.info(f"Updated organization domain to: {domain}")
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about the classifier configuration"""
        return {
            'organization_domain': self.organization_domain,
            'business_keywords_total': sum(len(keywords) for keywords in self.business_keywords.values()),
            'collaboration_indicators': len(self.collaboration_indicators),
            'business_sender_patterns': len(self.business_sender_patterns),
            'relevance_thresholds': self.relevance_thresholds
        } 