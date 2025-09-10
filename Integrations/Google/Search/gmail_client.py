"""
Gmail Client for Hybrid Search
Native Gmail API client with pagination, retries, and query building
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64
from email.mime.text import MIMEText
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from googleapiclient.errors import HttpError

from .auth_factory import get_auth_factory
from .query_interpreter import SearchSpec

logger = logging.getLogger(__name__)


@dataclass
class GmailMessage:
    """Gmail message result"""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    snippet: str
    labels: List[str]
    has_attachments: bool
    content: str = ""
    url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "sender": self.sender,
            "recipient": self.recipient,
            "date": self.date.isoformat(),
            "snippet": self.snippet,
            "labels": self.labels,
            "has_attachments": self.has_attachments,
            "content": self.content,
            "url": self.url,
            "source": "gmail",
            "type": "email"
        }


class GmailClient:
    """
    Production-grade Gmail client with native query support
    """
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.auth_factory = get_auth_factory()
        self._service = None
        self.max_results_per_page = int(os.getenv('GMAIL_PAGE_SIZE', '50'))
        
    @property
    def service(self):
        """Lazy-loaded Gmail service"""
        if self._service is None:
            self._service = self.auth_factory.get_gmail_service(self.user_id)
        return self._service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True
    )
    def search_messages(self, 
                       query: str, 
                       max_results: int = 25,
                       include_content: bool = False) -> List[GmailMessage]:
        """
        Search Gmail messages with pagination and retries
        
        Args:
            query: Gmail search query string (with proper operators)
            max_results: Maximum number of results to return
            include_content: Whether to fetch full message content
            
        Returns:
            List of GmailMessage objects
        """
        logger.info(f"📧 Gmail search: '{query}' (max: {max_results})")
        start_time = time.time()
        
        try:
            messages = []
            next_page_token = None
            
            while len(messages) < max_results:
                # Calculate remaining results needed
                remaining = max_results - len(messages)
                page_size = min(remaining, self.max_results_per_page)
                
                # Execute search request
                search_result = self._execute_search_request(
                    query, page_size, next_page_token
                )
                
                if not search_result.get('messages'):
                    logger.info("📧 No more messages found")
                    break
                
                # Process batch of message IDs
                batch_ids = [msg['id'] for msg in search_result['messages']]
                batch_messages = self._fetch_message_batch(batch_ids, include_content)
                messages.extend(batch_messages)
                
                # Check for next page
                next_page_token = search_result.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Trim to exact count
            messages = messages[:max_results]
            
            duration = time.time() - start_time
            logger.info(f"✅ Gmail search completed: {len(messages)} messages in {duration:.2f}s")
            
            return messages
            
        except HttpError as e:
            error_code = e.resp.status
            error_detail = e.error_details[0].get('message', str(e)) if e.error_details else str(e)
            
            logger.error(f"❌ Gmail API error {error_code}: {error_detail}")
            
            if error_code == 400:
                logger.error(f"❌ Invalid query syntax: '{query}'")
            elif error_code == 403:
                logger.error("❌ Gmail API quota exceeded or access denied")
            elif error_code == 401:
                logger.error("❌ Gmail authentication failed")
            
            raise
            
        except Exception as e:
            logger.error(f"❌ Gmail search failed: {e}")
            raise

    def _execute_search_request(self, 
                               query: str, 
                               page_size: int, 
                               page_token: Optional[str] = None) -> Dict[str, Any]:
        """Execute single search request with proper error handling"""
        request_params = {
            'userId': 'me',
            'q': query,
            'maxResults': page_size
        }
        
        if page_token:
            request_params['pageToken'] = page_token
        
        logger.debug(f"📧 Gmail API request: {request_params}")
        
        return self.service.users().messages().list(**request_params).execute()

    def _fetch_message_batch(self, 
                            message_ids: List[str], 
                            include_content: bool = False) -> List[GmailMessage]:
        """Fetch batch of messages with parallel processing"""
        messages = []
        
        for msg_id in message_ids:
            try:
                message = self._fetch_single_message(msg_id, include_content)
                if message:
                    messages.append(message)
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch message {msg_id}: {e}")
                continue
        
        return messages

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=0.5, max=5),
        reraise=True
    )
    def _fetch_single_message(self, 
                             message_id: str, 
                             include_content: bool = False) -> Optional[GmailMessage]:
        """Fetch single message with metadata"""
        format_type = 'full' if include_content else 'metadata'
        metadata_headers = ['Message-ID', 'Subject', 'From', 'To', 'Date']
        
        msg_data = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format=format_type,
            metadataHeaders=metadata_headers
        ).execute()
        
        return self._parse_message_data(msg_data, include_content)

    def _parse_message_data(self, 
                           msg_data: Dict[str, Any], 
                           include_content: bool = False) -> Optional[GmailMessage]:
        """Parse Gmail API message data into GmailMessage object"""
        try:
            headers = {h['name'].lower(): h['value'] 
                      for h in msg_data.get('payload', {}).get('headers', [])}
            
            # Extract basic fields
            subject = headers.get('subject', '(No Subject)')
            sender = headers.get('from', '(Unknown Sender)')
            recipient = headers.get('to', '(Unknown Recipient)')
            
            # Parse date
            date_str = headers.get('date', '')
            try:
                # Gmail dates are in RFC 2822 format
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                date = datetime.now()
            
            # Extract snippet and labels
            snippet = msg_data.get('snippet', '')
            labels = msg_data.get('labelIds', [])
            
            # Check for attachments
            has_attachments = any(
                part.get('filename') 
                for part in self._get_message_parts(msg_data.get('payload', {}))
            )
            
            # Extract content if requested
            content = ""
            if include_content:
                content = self._extract_message_content(msg_data.get('payload', {}))
            
            # Build Gmail URL
            url = f"https://mail.google.com/mail/u/0/#inbox/{msg_data['id']}"
            
            return GmailMessage(
                id=msg_data['id'],
                thread_id=msg_data['threadId'],
                subject=subject,
                sender=sender,
                recipient=recipient,
                date=date,
                snippet=snippet,
                labels=labels,
                has_attachments=has_attachments,
                content=content,
                url=url
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse message {msg_data.get('id', 'unknown')}: {e}")
            return None

    def _get_message_parts(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recursively extract all message parts"""
        parts = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                parts.extend(self._get_message_parts(part))
        else:
            parts.append(payload)
        
        return parts

    def _extract_message_content(self, payload: Dict[str, Any]) -> str:
        """Extract text content from message payload"""
        content_parts = []
        
        for part in self._get_message_parts(payload):
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data')
                if body_data:
                    try:
                        # Decode base64 URL-safe content
                        decoded = base64.urlsafe_b64decode(body_data + '===').decode('utf-8')
                        content_parts.append(decoded)
                    except (UnicodeDecodeError, ValueError):
                        continue
        
        return '\n\n'.join(content_parts)

    def build_query_from_spec(self, spec: SearchSpec) -> str:
        """
        Build Gmail query from SearchSpec
        Delegates to QueryInterpreter but can add Gmail-specific optimizations
        """
        from .query_interpreter import QueryInterpreter
        interpreter = QueryInterpreter()
        return interpreter.build_gmail_query(spec)

    def test_connectivity(self) -> bool:
        """Test Gmail API connectivity"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info(f"✅ Gmail connectivity OK for: {profile.get('emailAddress', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Gmail connectivity failed: {e}")
            return False

    def get_user_profile(self) -> Dict[str, Any]:
        """Get Gmail user profile information"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                "email": profile.get('emailAddress'),
                "messages_total": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0),
                "history_id": profile.get('historyId')
            }
        except Exception as e:
            logger.error(f"❌ Failed to get Gmail profile: {e}")
            return {}


# For backward compatibility
def get_gmail_client(user_id: Optional[str] = None) -> GmailClient:
    """Factory function for Gmail client"""
    return GmailClient(user_id)
