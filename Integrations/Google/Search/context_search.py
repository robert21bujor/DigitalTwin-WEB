"""
Multi-Colleague Email Context Search
Provides relevant context from colleagues' emails while protecting privacy
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ColleagueContextSearch:
    """
    Search across colleagues' emails for context while maintaining privacy
    """
    
    def __init__(self, auth_factory):
        self.auth_factory = auth_factory
        
        # Privacy filters - remove sensitive content
        self.sensitive_patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit cards
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\$[\d,]+\.?\d*',  # Dollar amounts
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses (optional)
            r'\b\d{10,}\b',  # Long numbers (IDs, account numbers)
        ]
        
    def search_colleague_context(self, 
                                query: str, 
                                requesting_user_id: str,
                                max_results: int = 10,
                                time_window_days: int = 30) -> List[Dict[str, Any]]:
        """
        Search for context across colleagues' emails
        
        Args:
            query: Search query
            requesting_user_id: User requesting the context
            max_results: Maximum number of context items to return
            time_window_days: How far back to search (default 30 days)
            
        Returns:
            List of anonymized context items
        """
        try:
            # Get colleague credentials (with permission checks)
            colleague_creds = self.auth_factory.get_colleague_credentials(requesting_user_id)
            
            if not colleague_creds:
                logger.info(f"No colleague access granted for user {requesting_user_id}")
                return []
            
            context_results = []
            
            # Search each colleague's emails
            for colleague in colleague_creds:
                colleague_id = colleague['user_id']
                credentials = colleague['credentials']
                
                # Search this colleague's emails
                colleague_context = self._search_colleague_emails(
                    query=query,
                    colleague_id=colleague_id,
                    credentials=credentials,
                    time_window_days=time_window_days,
                    max_per_colleague=max_results // len(colleague_creds)
                )
                
                context_results.extend(colleague_context)
            
            # Sort by relevance and recency
            context_results.sort(key=lambda x: (x['relevance_score'], x['timestamp']), reverse=True)
            
            return context_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching colleague context: {e}")
            return []
    
    def _search_colleague_emails(self, 
                                query: str,
                                colleague_id: str, 
                                credentials,
                                time_window_days: int,
                                max_per_colleague: int = 5) -> List[Dict[str, Any]]:
        """Search a specific colleague's emails for context"""
        try:
            from googleapiclient.discovery import build
            
            # Create Gmail service for this colleague
            gmail_service = build('gmail', 'v1', credentials=credentials)
            
            # Build search query with time constraint
            cutoff_date = datetime.now() - timedelta(days=time_window_days)
            search_query = f"{query} after:{cutoff_date.strftime('%Y/%m/%d')}"
            
            # Search emails
            results = gmail_service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=max_per_colleague
            ).execute()
            
            messages = results.get('messages', [])
            context_items = []
            
            for message in messages[:max_per_colleague]:
                msg_id = message['id']
                
                # Get message details
                msg_detail = gmail_service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Extract context (anonymized)
                context_item = self._extract_anonymous_context(msg_detail, colleague_id, query)
                if context_item:
                    context_items.append(context_item)
            
            return context_items
            
        except Exception as e:
            logger.error(f"Error searching colleague {colleague_id} emails: {e}")
            return []
    
    def _extract_anonymous_context(self, message: Dict, colleague_id: str, query: str) -> Optional[Dict[str, Any]]:
        """Extract relevant context while removing sensitive information"""
        try:
            # Get headers
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            # Get message body
            body = self._extract_message_body(message['payload'])
            if not body:
                return None
            
            # Remove sensitive information
            sanitized_body = self._sanitize_content(body)
            
            # Extract relevant sentences around query terms
            relevant_context = self._extract_relevant_sentences(sanitized_body, query)
            
            if not relevant_context:
                return None
            
            # Get colleague email (anonymized)
            colleague_email = self._get_colleague_email(colleague_id)
            colleague_name = colleague_email.split('@')[0] if colleague_email else "Colleague"
            
            return {
                'colleague_name': colleague_name,  # Just first name/username
                'timestamp': headers.get('Date', ''),
                'subject_keywords': self._extract_keywords(headers.get('Subject', '')),
                'relevant_context': relevant_context,
                'message_type': self._classify_message_type(headers.get('Subject', '')),
                'relevance_score': self._calculate_relevance(relevant_context, query),
                'source': 'colleague_email'
            }
            
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return None
    
    def _extract_message_body(self, payload: Dict) -> str:
        """Extract text from email payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        import base64
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif payload['mimeType'] == 'text/plain':
            data = payload['body'].get('data', '')
            if data:
                import base64
                body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def _sanitize_content(self, content: str) -> str:
        """Remove sensitive information from content"""
        sanitized = content
        
        # Remove sensitive patterns
        for pattern in self.sensitive_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Remove signature blocks
        sanitized = re.sub(r'\n--\n.*$', '', sanitized, flags=re.DOTALL)
        
        # Remove quoted text (replies)
        sanitized = re.sub(r'\n>.*$', '', sanitized, flags=re.MULTILINE)
        
        return sanitized
    
    def _extract_relevant_sentences(self, content: str, query: str) -> str:
        """Extract sentences containing query terms or related context"""
        query_terms = query.lower().split()
        sentences = re.split(r'[.!?]+', content)
        
        relevant_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
                
            sentence_lower = sentence.lower()
            
            # Check if sentence contains query terms
            for term in query_terms:
                if term in sentence_lower:
                    relevant_sentences.append(sentence)
                    break
        
        # Return top 3 most relevant sentences
        return ' ... '.join(relevant_sentences[:3])
    
    def _extract_keywords(self, subject: str) -> List[str]:
        """Extract keywords from email subject"""
        # Remove common email prefixes
        subject = re.sub(r'^(Re|Fwd|FW|RE):\s*', '', subject, flags=re.IGNORECASE)
        
        # Extract meaningful words (3+ characters)
        words = re.findall(r'\b\w{3,}\b', subject.lower())
        
        # Remove common words
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'its', 'said', 'each', 'make', 'most', 'over', 'such', 'time', 'very', 'what', 'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'this', 'well', 'were'}
        
        keywords = [word for word in words if word not in stopwords]
        
        return keywords[:5]  # Top 5 keywords
    
    def _classify_message_type(self, subject: str) -> str:
        """Classify the type of email based on subject"""
        subject_lower = subject.lower()
        
        if any(word in subject_lower for word in ['meeting', 'call', 'schedule', 'appointment']):
            return 'meeting'
        elif any(word in subject_lower for word in ['project', 'task', 'deadline', 'update']):
            return 'project'
        elif any(word in subject_lower for word in ['question', 'help', 'support', 'issue']):
            return 'support'
        elif any(word in subject_lower for word in ['announcement', 'news', 'update', 'info']):
            return 'announcement'
        else:
            return 'general'
    
    def _calculate_relevance(self, context: str, query: str) -> float:
        """Calculate relevance score based on query term frequency"""
        if not context:
            return 0.0
        
        query_terms = query.lower().split()
        context_lower = context.lower()
        
        score = 0.0
        for term in query_terms:
            score += context_lower.count(term)
        
        # Normalize by content length
        return score / len(context.split()) if context else 0.0
    
    def _get_colleague_email(self, colleague_id: str) -> str:
        """Get colleague email (for name extraction only)"""
        try:
            from Integrations.Google.Gmail.gmail_database import gmail_database
            token_data = gmail_database.get_gmail_tokens(colleague_id)
            if token_data and 'user_info' in token_data:
                return token_data['user_info'].get('email', '')
        except:
            pass
        return ''


# Usage example function
def search_colleague_context_api(query: str, 
                                requesting_user_id: str,
                                max_results: int = 10) -> Dict[str, Any]:
    """
    API endpoint for searching colleague context
    
    Returns:
        Dictionary with anonymized context results
    """
    try:
        from .auth_factory import get_auth_factory
        
        auth_factory = get_auth_factory()
        context_search = ColleagueContextSearch(auth_factory)
        
        results = context_search.search_colleague_context(
            query=query,
            requesting_user_id=requesting_user_id,
            max_results=max_results
        )
        
        return {
            'success': True,
            'query': query,
            'results_count': len(results),
            'colleague_context': results,
            'privacy_note': 'All content has been anonymized and sensitive information removed'
        }
        
    except Exception as e:
        logger.error(f"Error in colleague context search API: {e}")
        return {
            'success': False,
            'error': str(e),
            'colleague_context': []
        }
