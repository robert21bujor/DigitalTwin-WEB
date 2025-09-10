"""
Gmail Service with Advanced Email Filtering
==========================================

Enhanced Gmail service that uses a sophisticated two-stage filtering pipeline:
- Stage 1: Rule-based filtering (fast, deterministic)  
- Stage 2: ML-based relevance classification (heuristic)
- Whitelist exceptions for trusted sources
- Comprehensive audit logging
"""

import base64
import html2text
import logging
import re
import email.utils
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from Integrations.Google.Gmail import gmail_auth_service
    from Integrations.Google.Gmail.email_filtering import EmailFilteringPipeline
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Integrations.Google.Gmail import gmail_auth_service
    from Integrations.Google.Gmail.email_filtering import EmailFilteringPipeline

logger = logging.getLogger(__name__)

class EmailData:
    """Email data structure with robust timestamp handling"""
    def __init__(self, data: Dict[str, Any]):
        self.message_id = data.get('message_id', '')
        self.thread_id = data.get('thread_id', '')
        self.sender = data.get('sender', '')
        self.sender_email = data.get('sender_email', '')
        self.subject = data.get('subject', '')
        
        # Handle timestamps robustly
        timestamp_raw = data.get('timestamp')
        self.timestamp = self._safe_parse_timestamp(timestamp_raw)
        
        self.body = data.get('body', '')
        self.labels = data.get('labels', [])
        self.headers = data.get('headers', {})
        self.client_info = data.get('client_info', {})
        self.is_business_relevant = data.get('is_business_relevant', False)
    
    def _safe_parse_timestamp(self, timestamp_raw) -> Optional[str]:
        """
        Safely parse and normalize timestamp to ISO string format
        
        Args:
            timestamp_raw: Raw timestamp (string, datetime, or None)
            
        Returns:
            ISO format string or None
        """
        if not timestamp_raw:
            return None
            
        try:
            if isinstance(timestamp_raw, str):
                # Already a string - validate it's parseable
                try:
                    # Try parsing to ensure it's valid
                    if 'Z' in timestamp_raw:
                        datetime.fromisoformat(timestamp_raw.replace('Z', '+00:00'))
                    else:
                        datetime.fromisoformat(timestamp_raw)
                    return timestamp_raw  # Valid ISO string
                except:
                    # Try parsing with email.utils for other string formats
                    try:
                        parsed = email.utils.parsedate_to_datetime(timestamp_raw)
                        return parsed.isoformat()
                    except:
                        logger.warning(f"Could not parse timestamp string: {timestamp_raw}")
                        return datetime.now().isoformat()
                        
            elif hasattr(timestamp_raw, 'isoformat'):
                # Datetime object
                return timestamp_raw.isoformat()
            else:
                # Unknown type
                logger.warning(f"Unknown timestamp type: {type(timestamp_raw)}")
                return datetime.now().isoformat()
                
        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_raw}: {e}")
            return datetime.now().isoformat()


class EnhancedGmailService:
    """
    Enhanced Gmail service with two-stage email filtering
    
    Features:
    - Stage 1: Rule-based filtering (fast spam/promotional removal)
    - Stage 2: ML-based heuristic classification
    - Whitelist management for trusted sources
    - Comprehensive audit logging
    - Organization-aware filtering
    """
    
    def __init__(self, user_email: str = None, user_id: str = None):
        """
        Initialize the Enhanced Gmail Service with two-stage filtering
        
        Args:
            user_email: User's email address to determine their organization domain
            user_id: User identifier for filtering pipeline and audit logging
        """
        self.user_email = user_email
        self.user_id = user_id
        self.organization_domain = None
        self.organization_name = None
        
        if user_email:
            self.organization_domain, self.organization_name = self._extract_organization_info(user_email)
        
        # Initialize two-stage filtering pipeline with user_id
        self.filtering_pipeline = EmailFilteringPipeline(
            organization_domain=self.organization_domain,
            user_id=self.user_id
        )
        
        # Initialize html2text for email content processing
        self.h = html2text.HTML2Text()
        self.h.ignore_links = True
        self.h.ignore_images = True
        self.h.body_width = 0
        
        logger.info(f"🚀 Enhanced Gmail Service initialized with two-stage filtering")
        if self.organization_domain:
            logger.info(f"📧 Organization: {self.organization_name} ({self.organization_domain})")
    
    def get_business_emails(self, token_data: Dict[str, Any], days_back: int = 30, 
                           max_results: int = 100) -> List[EmailData]:
        """
        Retrieve and filter business-relevant emails using two-stage filtering
        
        Args:
            token_data: Gmail authentication token data
            days_back: Number of days to look back
            max_results: Maximum number of results to process
            
        Returns:
            List of EmailData objects for business-relevant emails
        """
        try:
            # Pass user_id for automatic token refresh
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            # Get user_id from token_data or current context
            user_id = None
            if hasattr(self, 'user_id') and self.user_id:
                user_id = self.user_id
            else:
                # Try to get user_id from database lookup
                try:
                    if self.supabase_client:
                        result = self.supabase_client.table('gmail_tokens').select('user_id').eq('access_token', token_data.get('access_token')).limit(1).execute()
                        if result.data:
                            user_id = result.data[0]['user_id']
                except:
                    pass
            
            credentials = gmail_auth_service.get_credentials(token_data, user_id)
            if not credentials:
                logger.error("Failed to get valid credentials")
                return []

            service = build('gmail', 'v1', credentials=credentials)
            
            # Build search query - get all emails (let filtering pipeline handle the rest)
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            query = f"-label:spam -label:trash after:{since_date}"
            
            logger.info(f"🔍 Searching Gmail with query: {query}")
            
            # Get message list
            messages_result = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = messages_result.get('messages', [])
            logger.info(f"📧 Found {len(messages)} emails to process")
            
            if not messages:
                return []
            
            # Extract email data for filtering
            email_data_list = []
            processed_count = 0
            
            for message in messages:
                try:
                    email_dict = self._extract_email_data(service, message['id'])
                    if email_dict:
                        email_data_list.append(email_dict)
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error extracting message {message.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"📊 Extracted {processed_count} emails for filtering")
            
            if not email_data_list:
                return []
            
            # Process through two-stage filtering pipeline
            try:
                user_id = token_data.get('user_id', 'unknown')
                filter_results = self.filtering_pipeline.process_emails(email_data_list)
                
                # Convert allowed emails to EmailData objects
                business_emails = []
                
                # Include whitelisted and allowed emails
                for email_dict in filter_results['whitelisted'] + filter_results['allowed']:
                    # Extract client info
                    client_info = self._detect_client(email_dict)
                    email_dict['client_info'] = client_info
                    email_dict['is_business_relevant'] = True
                    
                    business_emails.append(EmailData(email_dict))
                
                # Log filtering results
                stats = filter_results['statistics']
                logger.info(f"🎯 Filtering Results:")
                logger.info(f"   ✅ Allowed: {len(filter_results['allowed'])}")
                logger.info(f"   🏷️ Whitelisted: {len(filter_results['whitelisted'])}")
                logger.info(f"   🗑️ Filtered: {len(filter_results['filtered'])}")
                logger.info(f"   ⏸️ Review Queue: {len(filter_results['review_queue'])}")
                logger.info(f"   📊 Stage 1 Filtered: {stats['stage1_filtered']}")
                logger.info(f"   📊 Stage 2 Filtered: {stats['stage2_filtered']}")
                logger.info(f"   🏢 Organization Bypass: {stats['organization_bypass']}")
                
                return business_emails
                
            except Exception as e:
                logger.error(f"❌ Filtering pipeline failed: {e}")
                return []
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_business_emails: {e}")
            return []
    
    def _extract_email_data(self, service, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract email data in format expected by filtering pipeline
        
        Args:
            service: Gmail service instance
            message_id: Gmail message ID
            
        Returns:
            Dictionary with email data for filtering pipeline
        """
        try:
            # Get full message
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            payload = message.get('payload', {})
            
            for header in payload.get('headers', []):
                headers[header['name']] = header['value']
            
            # Extract basic info
            subject = headers.get('Subject', 'No Subject')
            sender_email = self._extract_email_from_field(headers.get('From', ''))
            timestamp = headers.get('Date', '')
            
            # Convert timestamp to ISO format
            try:
                if timestamp:
                    parsed_date = email.utils.parsedate_to_datetime(timestamp)
                    timestamp = parsed_date.isoformat()
                else:
                    timestamp = datetime.now().isoformat()
            except:
                timestamp = datetime.now().isoformat()
            
            # Extract body
            body = self._extract_body(payload)
            
            # Return in filtering pipeline format
            return {
                'message_id': message_id,
                'thread_id': message.get('threadId', message_id),
                'sender_email': sender_email,
                'subject': subject,
                'timestamp': timestamp,
                'body': body,
                'headers': headers
            }
            
        except Exception as e:
            logger.error(f"Error extracting email data: {e}")
            return None
    
    def _detect_client(self, email_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect the client (organization) from the email data
        
        Args:
            email_dict: Dictionary containing email information
            
        Returns:
            Dictionary with client information
        """
        try:
            sender_email = email_dict.get('sender_email', '').lower()
            subject = email_dict.get('subject', '').lower()
            body = email_dict.get('body', '').lower()
            
            # Extract domain from sender
            domain = ''
            if '@' in sender_email:
                domain = sender_email.split('@')[1]
            
            # Default client info
            client_info = {
                'name': 'Unknown',
                'domain': domain,
                'confidence': 0.5,
                'detection_method': 'domain_extraction',
                'folder_path': 'General',
                'category': 'General'
            }
            
            # Internal emails (same organization)
            if self.organization_domain and self.organization_domain in sender_email:
                client_info.update({
                    'name': self.organization_name or 'Internal Team',
                    'confidence': 0.9,
                    'detection_method': 'organization_internal',
                    'folder_path': 'Internal',
                    'category': 'Internal'
                })
                return client_info
            
            # Known business domains
            business_domains = {
                'microsoft.com': 'Microsoft',
                'google.com': 'Google',
                'github.com': 'GitHub',
                'gitlab.com': 'GitLab',
                'slack.com': 'Slack',
                'zoom.us': 'Zoom',
                'atlassian.com': 'Atlassian',
                'salesforce.com': 'Salesforce',
                'hubspot.com': 'HubSpot',
                'stripe.com': 'Stripe'
            }
            
            if domain in business_domains:
                client_info.update({
                    'name': business_domains[domain],
                    'confidence': 0.8,
                    'detection_method': 'known_domain',
                    'folder_path': 'Business',
                    'category': 'Business'
                })
                return client_info
            
            # Try to extract company name from sender display name or subject
            sender_display = email_dict.get('sender', '').lower()
            
            # Look for company indicators in sender or subject
            company_indicators = ['inc', 'corp', 'ltd', 'llc', 'gmbh', 'sa', 'bv', 'ag']
            for indicator in company_indicators:
                if indicator in sender_display or indicator in subject:
                    # Try to extract company name
                    if '@' in sender_display:
                        name_part = sender_display.split('@')[0].strip()
                        if name_part:
                            client_info.update({
                                'name': name_part.title(),
                                'confidence': 0.6,
                                'detection_method': 'company_indicator',
                                'folder_path': 'Clients',
                                'category': 'Client'
                            })
                            return client_info
            
            # Professional email patterns
            professional_patterns = [
                'sales@', 'support@', 'info@', 'contact@', 'admin@',
                'hello@', 'team@', 'noreply@', 'no-reply@'
            ]
            
            for pattern in professional_patterns:
                if pattern in sender_email:
                    # Extract domain name as company name
                    if domain:
                        company_name = domain.replace('.com', '').replace('.org', '').replace('.net', '').title()
                        client_info.update({
                            'name': company_name,
                            'confidence': 0.7,
                            'detection_method': 'professional_email',
                            'folder_path': 'Clients',
                            'category': 'Client'
                        })
                        return client_info
            
            # If we have a domain but no specific detection, use domain as name
            if domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                company_name = domain.replace('.com', '').replace('.org', '').replace('.net', '').title()
                client_info.update({
                    'name': company_name,
                    'confidence': 0.4,
                    'detection_method': 'domain_fallback',
                    'folder_path': 'General',
                    'category': 'General'
                })
            
            return client_info
            
        except Exception as e:
            logger.error(f"Error detecting client: {e}")
            return {
                'name': 'Unknown',
                'domain': 'unknown',
                'confidence': 0.0,
                'detection_method': 'error',
                'folder_path': 'General',
                'category': 'General'
            }
    
    def get_filtering_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        try:
            # Delegate to filtering pipeline
            return self.filtering_pipeline.get_filtering_statistics(days=7)
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def add_whitelist_domain(self, domain: str, reason: str):
        """Add domain to whitelist (filtering pipeline manages this)"""
        try:
            logger.info(f"Whitelist request: {domain} ({reason})")
            return self.filtering_pipeline.add_whitelist_domain(domain)
        except Exception as e:
            logger.error(f"Error adding whitelist domain: {e}")
            return False
    
    def add_feedback(self, feedback_data: Dict[str, Any]):
        """Submit feedback for filtering"""
        try:
            return self.filtering_pipeline.submit_feedback(
                feedback_data.get('email_id', ''),
                feedback_data.get('correct_decision', ''),
                feedback_data.get('feedback', '')
            )
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            return False
    
    def get_review_queue(self, max_items: int = 50):
        """Get items from filtering review queue"""
        try:
            queue = self.filtering_pipeline.get_review_queue()
            return queue[:max_items] if len(queue) > max_items else queue
        except Exception as e:
            logger.error(f"Error getting review queue: {e}")
            return []
    
    def export_filtering_decisions(self, output_file: str, format: str = 'csv'):
        """Export filtering audit data"""
        try:
            return self.filtering_pipeline.export_filtering_decisions()
        except Exception as e:
            logger.error(f"Error exporting filtering decisions: {e}")
            return []
    
    def update_user_context(self, user_email: str):
        """Update user context for organization-specific processing"""
        self.user_email = user_email
        if user_email:
            self.organization_domain, self.organization_name = self._extract_organization_info(user_email)
            logger.info(f"📧 Updated organization: {self.organization_name} ({self.organization_domain})")
    
    def _extract_organization_info(self, email: str) -> tuple:
        """Extract organization domain and name from email"""
        try:
            domain = email.split('@')[1].lower()
            # Generate a friendly organization name from domain
            name_parts = domain.split('.')
            if len(name_parts) >= 2:
                org_name = name_parts[0].replace('-', ' ').title()
            else:
                org_name = domain.title()
            return domain, org_name
        except:
            return None, None
    
    def _extract_email_from_field(self, field: str) -> str:
        """Extract email address from header field"""
        try:
            if '<' in field and '>' in field:
                return field.split('<')[1].split('>')[0].strip()
            elif '@' in field:
                return field.strip()
            else:
                return field
        except:
            return field
    
    def _extract_body(self, payload) -> str:
        """Extract email body content"""
        try:
            body = ""
            
            if 'parts' in payload:
                for part in payload['parts']:
                    body += self._extract_body(part)
            else:
                if payload.get('mimeType') == 'text/plain':
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif payload.get('mimeType') == 'text/html':
                    data = payload.get('body', {}).get('data', '')
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        body = self.h.handle(html_content)
            
            return body.strip()
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return "" 