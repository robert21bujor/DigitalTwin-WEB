"""
Gmail Integration Manager
Main coordinator for Gmail integration functionality
"""

import logging
from typing import Dict, Any, List, Optional

try:
    from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
    from Integrations.Google.Gmail.gmail_service import EnhancedGmailService, EmailData
    from Integrations.Google.Gmail.document_service import document_service
    from Integrations.Google.Gmail.gmail_database import gmail_database
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
    from Integrations.Google.Gmail.gmail_service import EnhancedGmailService, EmailData
    from Integrations.Google.Gmail.document_service import document_service
    from Integrations.Google.Gmail.gmail_database import gmail_database

logger = logging.getLogger(__name__)


class GmailIntegrationManager:
    """Main manager for Gmail integration functionality with modular organization support"""
    
    def __init__(self):
        """Initialize Gmail Integration Manager"""
        self.auth_service = gmail_auth_service
        self.document_service = document_service
        self.database_service = gmail_database
        self._user_services = {}  # Cache for user-specific Gmail services
        
        logger.info("Gmail Integration Manager initialized with modular organization support")
    
    def _get_user_gmail_service(self, user_id: str) -> EnhancedGmailService:
        """
        Get or create a user-specific Gmail service with their organization context
        
        Args:
            user_id: User identifier
            
        Returns:
            User-specific EnhancedGmailService instance
        """
        # Check if we already have a service for this user
        if user_id in self._user_services:
            return self._user_services[user_id]
        
        # Get user's email from their Gmail tokens
        user_email = None
        try:
            token_data = self.database_service.get_gmail_tokens(user_id)
            if token_data:
                # Email is stored in user_info field
                if 'user_info' in token_data and 'email' in token_data['user_info']:
                    user_email = token_data['user_info']['email']
                    logger.info(f"Creating Gmail service for {user_email}")
                elif 'email' in token_data:
                    # Fallback to direct email field (legacy support)
                    user_email = token_data['email']
                    logger.info(f"Creating Gmail service for {user_email}")
                else:
                    logger.warning(f"No email found in tokens for user {user_id}")
            else:
                logger.warning(f"No tokens found for user {user_id}")
        except Exception as e:
            logger.error(f"Error getting user email for {user_id}: {e}")
        
        # Create user-specific service with their organization context and user_id
        user_service = EnhancedGmailService(user_email=user_email, user_id=user_id)
        
        # Cache the service for future use
        self._user_services[user_id] = user_service
        
        return user_service
    
    def get_auth_url(self, user_id: str) -> Optional[str]:
        """
        Get OAuth2 authorization URL for Gmail access
        
        Args:
            user_id: User identifier
            
        Returns:
            Authorization URL or None if failed
        """
        try:
            auth_url = self.auth_service.get_authorization_url(user_id)
            if auth_url:
                logger.info(f"Generated Gmail auth URL for user {user_id}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None
    
    def complete_oauth_flow(self, user_id: str, authorization_code: str, state: str) -> Dict[str, Any]:
        """
        Complete OAuth flow and store tokens
        
        Args:
            user_id: User identifier
            authorization_code: OAuth2 authorization code
            state: State parameter for validation
            
        Returns:
            Dictionary with success status and user info
        """
        try:
            # Exchange code for tokens
            token_data = self.auth_service.exchange_code_for_tokens(authorization_code, state)
            
            if not token_data:
                return {
                    'success': False,
                    'error': 'Failed to exchange authorization code for tokens'
                }
            
            # Store tokens in database
            stored = self.database_service.store_gmail_tokens(user_id, token_data)
            
            if not stored:
                return {
                    'success': False,
                    'error': 'Failed to store Gmail tokens'
                }
            
            # Test connection
            connection_test = self.auth_service.test_gmail_connection(token_data)
            
            if not connection_test:
                return {
                    'success': False,
                    'error': 'Gmail connection test failed'
                }
            
            logger.info(f"Successfully completed Gmail OAuth flow for user {user_id}")
            return {
                'success': True,
                'user_info': token_data.get('user_info', {}),
                'gmail_email': token_data.get('user_info', {}).get('email')
            }
            
        except Exception as e:
            logger.error(f"Error completing OAuth flow: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get Gmail connection status for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with connection status information
        """
        try:
            return self.database_service.get_gmail_connection_status(user_id)
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def disconnect_gmail(self, user_id: str) -> Dict[str, Any]:
        """
        Disconnect Gmail integration for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with success status
        """
        try:
            # Get current tokens
            token_data = self.database_service.get_gmail_tokens(user_id)
            
            if token_data:
                # Revoke tokens with Google
                self.auth_service.revoke_tokens(token_data)
            
            # Deactivate tokens in database
            revoked = self.database_service.revoke_gmail_tokens(user_id)
            
            if revoked:
                logger.info(f"Successfully disconnected Gmail for user {user_id}")
                return {
                    'success': True,
                    'message': 'Gmail account disconnected successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to revoke Gmail tokens'
                }
                
        except Exception as e:
            logger.error(f"Error disconnecting Gmail: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_emails(self, user_id: str, days_back: int = 30, max_results: int = 100,
                   auto_cleanup: bool = True, progress_callback=None) -> Dict[str, Any]:
        """
        Sync Gmail emails and store business-relevant ones as documents
        
        Args:
            user_id: User identifier
            days_back: Number of days to look back for emails
            max_results: Maximum number of emails to process
            auto_cleanup: Whether to automatically clean up orphaned database entries first (default: True)
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with sync results
        """
        try:
            import time
            start_time = time.time()
            logger.info(f"🔄 Starting Gmail sync for user {user_id} (days: {days_back}, max: {max_results})")
            
            # Helper function for progress updates
            def update_progress(stage: str, message: str, progress: int):
                if progress_callback:
                    progress_callback(stage, message, progress)
            
            update_progress("Initializing", "Starting Gmail sync...", 5)
            
            # Optional: Clean up orphaned database entries first
            cleanup_results = None
            if auto_cleanup:
                update_progress("Cleanup", "Running Google Drive cleanup...", 10)
                logger.info("🧹 Running automatic Google Drive-Database cleanup...")
                cleanup_start = time.time()
                cleanup_results = self.sync_database_with_google_drive(user_id, cleanup_orphaned=True)
                cleanup_time = time.time() - cleanup_start
                
                if cleanup_results.get('removed_from_db', 0) > 0:
                    logger.info(f"✅ Cleaned up {cleanup_results['removed_from_db']} orphaned database entries ({cleanup_time:.1f}s)")
                else:
                    logger.info(f"✅ Database cleanup completed ({cleanup_time:.1f}s)")
            
            # Get Gmail tokens
            update_progress("Authentication", "Retrieving Gmail tokens...", 15)
            logger.info("🔑 Retrieving Gmail authentication tokens...")
            token_data = self.database_service.get_gmail_tokens(user_id)
            if not token_data:
                logger.error("❌ No Gmail tokens found for user")
                return {
                    'success': False,
                    'error': 'No Gmail tokens found for user'
                }
            
            # Add user_id to token_data for organization bypass in filtering pipeline
            token_data['user_id'] = user_id
            
            # Get user-specific Gmail service instance
            update_progress("Connecting", "Initializing Gmail service...", 20)
            logger.info("📧 Initializing Gmail service...")
            user_gmail_service = self._get_user_gmail_service(user_id)
            if not user_gmail_service:
                logger.error("❌ Failed to initialize Gmail service")
                return {
                    'success': False,
                    'error': 'Failed to initialize Gmail service'
                }
            
            # Retrieve emails using two-stage filtering
            update_progress("Fetching", "Retrieving emails from Gmail...", 30)
            logger.info(f"🔍 Retrieving emails with two-stage filtering...")
            email_start = time.time()
            business_emails = user_gmail_service.get_business_emails(
                token_data, 
                days_back=days_back, 
                max_results=max_results
            )
            email_time = time.time() - email_start
            logger.info(f"📊 Retrieved {len(business_emails)} business-relevant emails ({email_time:.1f}s)")
            
            if not business_emails:
                update_progress("Completed", "No business-relevant emails found", 100)
                logger.info("📭 No business-relevant emails found")
                return {
                    'success': True,
                    'total_processed': 0,
                    'new_documents': 0,
                    'skipped_duplicates': 0,
                    'processing_time_seconds': time.time() - start_time,
                    'filtering_used': 'two_stage_pipeline'
                }
            
            update_progress("Processing", f"Found {len(business_emails)} business emails", 40)
            
            # Debug: Log sample email data for troubleshooting
            if business_emails:
                sample_email = business_emails[0]
                logger.debug(f"📝 Sample email data:")
                logger.debug(f"   Subject: {sample_email.subject[:50]}...")
                logger.debug(f"   Timestamp type: {type(sample_email.timestamp)}")
                logger.debug(f"   Timestamp value: {sample_email.timestamp}")
                logger.debug(f"   Sender: {sample_email.sender_email}")
                logger.debug(f"   Business relevant: {sample_email.is_business_relevant}")
            
            # Check for duplicates  
            update_progress("Checking", "Checking for duplicate emails...", 50)
            logger.info("🔍 Checking for duplicates...")
            duplicate_start = time.time()
            message_ids = [email.message_id for email in business_emails]
            existing_ids = self.database_service.check_processed_emails(user_id, message_ids)
            
            # Filter out duplicates
            new_emails = [email for email in business_emails if email.message_id not in existing_ids]
            skipped_duplicates = len(business_emails) - len(new_emails)
            duplicate_time = time.time() - duplicate_start
            
            logger.info(f"📧 Found {len(new_emails)} new emails, skipped {skipped_duplicates} duplicates ({duplicate_time:.1f}s)")
            
            if not new_emails:
                update_progress("Completed", "All emails already processed", 100)
                logger.info("✅ All emails already processed")
                return {
                    'success': True,
                    'total_processed': len(business_emails),
                    'new_documents': 0,
                    'skipped_duplicates': skipped_duplicates,
                    'processing_time_seconds': time.time() - start_time,
                    'filtering_used': 'two_stage_pipeline'
                }
            
            # Process emails to documents (Google Drive)
            update_progress("Creating Documents", f"Processing {len(new_emails)} emails to documents...", 60)
            logger.info(f"📄 Processing {len(new_emails)} emails to documents...")
            doc_start = time.time()
            document_results = self.document_service.process_emails_to_documents(new_emails, user_id)
            doc_time = time.time() - doc_start
            logger.info(f"📊 Document processing completed ({doc_time:.1f}s)")
            
            # Create a mapping of email message_id to document info
            email_document_map = {}
            if document_results and 'clients' in document_results:
                for client_name, client_data in document_results['clients'].items():
                    for doc in client_data.get('documents', []):
                        # Find the email that matches this document by subject and timestamp
                        for email in new_emails:
                            if (email.subject == doc.get('subject') and 
                                self._safe_timestamp_isoformat(email.timestamp) == doc.get('timestamp')):
                                email_document_map[email.message_id] = {
                                    'document_path': doc.get('path'),
                                    'file_id': doc.get('file_id'),
                                    'web_link': doc.get('web_link'),
                                    'storage_type': doc.get('storage_type', 'google_drive')
                                }
                                break
            
            # Store processed email records with document information
            update_progress("Saving Records", "Storing email processing records...", 80)
            logger.info("💾 Storing email processing records with document paths...")
            db_start = time.time()
            for i, email in enumerate(new_emails, 1):
                if hasattr(email, 'message_id'):
                    # Update progress for each email being processed
                    current_progress = 80 + (i / len(new_emails)) * 15  # Progress from 80 to 95
                    update_progress("Saving Records", f"Storing email {i}/{len(new_emails)}", int(current_progress))
                    
                    logger.debug(f"💾 Storing email {i}/{len(new_emails)}: {email.subject[:50]}...")
                    
                    # Safely handle timestamp conversion
                    timestamp_str = self._safe_timestamp_isoformat(email.timestamp)
                    
                    # Get document information if available
                    doc_info = email_document_map.get(email.message_id, {})
                    
                    email_data = {
                        'message_id': email.message_id,
                        'thread_id': email.thread_id,
                        'sender_email': email.sender_email,
                        'subject': email.subject,
                        'timestamp': timestamp_str,
                        'client_info': email.client_info,
                        'is_business_relevant': email.is_business_relevant,
                        # Add document information (only document_path exists in current schema)
                        'document_path': doc_info.get('document_path')
                    }
                    
                    if doc_info:
                        logger.debug(f"   📄 Document: {doc_info.get('document_path', 'N/A')}")
                    else:
                        logger.warning(f"   ⚠️ No document created for email {email.message_id}")
                    
                    # Store with graceful duplicate handling
                    try:
                        self.database_service.store_processed_email(user_id, email_data)
                        logger.debug(f"   ✅ Stored successfully")
                    except Exception as e:
                        # Log but don't fail on duplicate key errors
                        if 'duplicate key' in str(e):
                            logger.info(f"📧 Email {email.message_id} already exists in database (race condition)")
                        else:
                            logger.error(f"❌ Error storing processed email {email.message_id}: {e}")
            
            db_time = time.time() - db_start
            total_time = time.time() - start_time
            logger.info(f"💾 Database records stored ({db_time:.1f}s)")
            logger.info(f"🎉 Gmail sync completed for user {user_id} (total: {total_time:.1f}s)")
            
            return {
                'success': True,
                'total_processed': len(business_emails),
                'new_documents': len(new_emails),
                'skipped_duplicates': skipped_duplicates,
                'processing_time_seconds': total_time,
                'document_results': document_results,
                'cleanup_results': cleanup_results,
                'filtering_used': 'two_stage_pipeline'
            }
            
        except Exception as e:
            logger.error(f"❌ Error syncing emails: {e}")
            # Add more detailed error logging
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_database_with_google_drive(self, user_id: str, cleanup_orphaned: bool = True) -> Dict[str, Any]:
        """
        Synchronize database with Google Drive to remove orphaned entries
        
        This resolves the "duplicate" confusion when users delete documents from Google Drive
        but they remain in the database, causing the system to skip re-processing them.
        
        Args:
            user_id: User ID to sync for
            cleanup_orphaned: Whether to actually remove orphaned database entries
            
        Returns:
            Dictionary with sync results
        """
        try:
            logger.info(f"Starting Google Drive-Database sync for user {user_id}")
            
            # Verify user has Gmail tokens
            token_data = self.database_service.get_gmail_tokens(user_id)
            if not token_data:
                return {
                    'success': False,
                    'error': 'No Gmail tokens found for user'
                }
            
            # Call the document service sync method
            sync_results = self.document_service.sync_database_with_google_drive(user_id, cleanup_orphaned)
            
            # Add success indicator
            sync_results['success'] = len(sync_results.get('errors', [])) == 0
            
            if sync_results['success']:
                logger.info(f"Google Drive-Database sync completed successfully for user {user_id}")
            else:
                logger.warning(f"Google Drive-Database sync completed with errors for user {user_id}")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Error in Google Drive-Database sync: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_checked': 0,
                'existing_files': 0,
                'missing_files': 0,
                'removed_from_db': 0
            }
    
    # Filtering and Organization-Aware Methods
    
    def get_filtering_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get filtering statistics for a user's organization"""
        try:
            user_service = self._get_user_gmail_service(user_id)
            return user_service.get_filtering_statistics()
        except Exception as e:
            logger.error(f"Error getting filtering statistics for user {user_id}: {e}")
            return {'error': str(e)}
    
    def add_whitelist_domain(self, user_id: str, domain: str, reason: str = "User request") -> bool:
        """Add domain to whitelist for a user's organization"""
        try:
            user_service = self._get_user_gmail_service(user_id)
            return user_service.add_whitelist_domain(domain, reason)
        except Exception as e:
            logger.error(f"Error adding whitelist domain for user {user_id}: {e}")
            return False
    
    def add_feedback(self, user_id: str, message_id: str, feedback: str, comment: str = "") -> bool:
        """Add feedback for email filtering for a user's organization"""
        try:
            user_service = self._get_user_gmail_service(user_id)
            return user_service.add_feedback(message_id, feedback, comment)
        except Exception as e:
            logger.error(f"Error adding feedback for user {user_id}: {e}")
            return False
    
    def get_review_queue(self, user_id: str, max_items: int = 50) -> List[Dict[str, Any]]:
        """Get review queue items for a user's organization"""
        try:
            user_service = self._get_user_gmail_service(user_id)
            return user_service.get_review_queue(max_items)
        except Exception as e:
            logger.error(f"Error getting review queue for user {user_id}: {e}")
            return []
    
    def export_filtering_decisions(self, user_id: str, output_path: str, output_format: str = "json") -> bool:
        """Export filtering decisions for a user's organization"""
        try:
            user_service = self._get_user_gmail_service(user_id)
            return user_service.export_filtering_decisions(output_path, output_format)
        except Exception as e:
            logger.error(f"Error exporting filtering decisions for user {user_id}: {e}")
            return False
    
    def get_sync_statistics(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Get email sync statistics for a user
        
        Args:
            user_id: User identifier
            days_back: Number of days to look back
            
        Returns:
            Dictionary with sync statistics
        """
        try:
            stats = self.database_service.get_processing_statistics(user_id, days_back)
            
            # Add document statistics
            doc_summary = self.document_service.get_client_summary()
            stats['document_summary'] = doc_summary
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {'error': str(e)}
    
    def get_client_documents(self) -> Dict[str, Any]:
        """
        Get summary of all client documents
        
        Returns:
            Dictionary with client document information
        """
        try:
            return self.document_service.get_client_summary()
        except Exception as e:
            logger.error(f"Error getting client documents: {e}")
            return {'error': str(e)}
    
    def cleanup_old_data(self, days_old: int = 90) -> Dict[str, Any]:
        """
        Clean up old emails and documents
        
        Args:
            days_old: Number of days after which to consider data old
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            # Cleanup database records
            db_cleanup = self.database_service.cleanup_old_records(days_old)
            
            # Cleanup documents
            doc_cleanup = self.document_service.cleanup_old_documents(days_old)
            
            logger.info(f"Cleanup completed: {db_cleanup.get('deleted_count', 0)} records, {doc_cleanup.get('deleted_count', 0)} documents")
            
            return {
                'success': True,
                'database_cleanup': db_cleanup,
                'document_cleanup': doc_cleanup
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _needs_token_refresh(self, token_data: Dict[str, Any]) -> bool:
        """
        Check if tokens need to be refreshed
        
        Args:
            token_data: Token data to check
            
        Returns:
            True if tokens need refresh, False otherwise
        """
        try:
            from datetime import datetime
            
            expiry_str = token_data.get('expiry')
            if not expiry_str:
                return False
            
            expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            
            # Refresh if expires within 5 minutes
            from datetime import timedelta, timezone
            refresh_threshold = datetime.now(timezone.utc) + timedelta(minutes=5)
            
            return expiry_time <= refresh_threshold
            
        except Exception:
            return False

    def get_email_content(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """
        Fetch individual email content by message ID
        
        Args:
            user_id: User identifier
            message_id: Gmail message ID
            
        Returns:
            Dict containing email content, subject, sender, etc.
        """
        try:
            logger.info(f"Fetching email content for message {message_id} for user {user_id}")
            
            # Check if user has Gmail authentication
            token_data = self.database_service.get_gmail_tokens(user_id)
            if not token_data:
                return {
                    "success": False,
                    "error": "Gmail not connected. Please authenticate first."
                }
            
            # Get Gmail service
            gmail_service = self.gmail_service.get_service(user_id)
            if not gmail_service:
                return {
                    "success": False,
                    "error": "Failed to get Gmail service"
                }
            
            # Fetch the specific email
            message = gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract email data
            headers = message.get('payload', {}).get('headers', [])
            
            # Get basic info
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract email body
            body = self._extract_email_body(message.get('payload', {}))
            
            return {
                "success": True,
                "content": body,
                "subject": subject,
                "sender_email": self._extract_email_from_sender(sender),
                "sender": sender,
                "date": date,
                "message_id": message_id
            }
            
        except Exception as e:
            logger.error(f"Error fetching email content for {message_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch email content: {str(e)}"
            }
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from Gmail payload"""
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data')
                        if data:
                            import base64
                            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    elif part.get('mimeType') == 'text/html':
                        data = part.get('body', {}).get('data')
                        if data:
                            import base64
                            import html2text
                            html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            return html2text.html2text(html_content)
            
            # Handle single part messages
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data')
                if data:
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif payload.get('mimeType') == 'text/html':
                data = payload.get('body', {}).get('data')
                if data:
                    import base64
                    import html2text
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    return html2text.html2text(html_content)
            
            return "No readable content found"
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return f"Error extracting email content: {str(e)}"
    
    def _extract_email_from_sender(self, sender: str) -> str:
        """Extract email address from sender string"""
        try:
            import email.utils
            parsed = email.utils.parseaddr(sender)
            return parsed[1] if parsed[1] else sender
        except:
            return sender
    
    def _safe_timestamp_isoformat(self, timestamp) -> Optional[str]:
        """Safely convert timestamp to ISO format string"""
        try:
            if timestamp is None:
                return None
            elif isinstance(timestamp, str):
                return timestamp
            elif hasattr(timestamp, 'isoformat'):
                return timestamp.isoformat()
            else:
                return str(timestamp)
        except Exception as e:
            logger.warning(f"Failed to convert timestamp {timestamp}: {e}")
            return None

    def process_approved_email(self, user_id: str, message_id: str, sender_email: str, 
                             subject: str, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Process a manually approved email into a Google Drive document
        
        Args:
            user_id: User identifier
            message_id: Gmail message ID
            sender_email: Email sender
            subject: Email subject
            timestamp: Email timestamp
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing approved email {message_id} for user {user_id}")
            
            # First, get the full email content
            email_content_result = self.get_email_content(user_id, message_id)
            if not email_content_result.get('success'):
                return {
                    "success": False,
                    "error": f"Failed to fetch email content: {email_content_result.get('error', 'Unknown error')}"
                }
            
            # Create EmailData object for document processing
            # EmailData already imported at top of file
            email_data = EmailData({
                'message_id': message_id,
                'sender_email': sender_email,
                'subject': subject,
                'body': email_content_result.get('content', ''),
                'timestamp': timestamp or email_content_result.get('date', ''),
                'is_business_relevant': True  # Already approved by user
            })
            
            # Process into document using document service
            from Integrations.Google.Gmail.document_service import DocumentService
            doc_service = DocumentService()
            
            # Create document
            doc_result = doc_service.create_email_document(email_data, user_id)
            
            if doc_result:
                logger.info(f"Successfully processed approved email {message_id} into document")
                
                # Store the processed email with document information in database
                try:
                    processed_email_data = {
                        'message_id': message_id,
                        'thread_id': message_id,  # Use message_id as thread_id if not available
                        'sender_email': sender_email,
                        'subject': subject,
                        'timestamp': self._safe_timestamp_isoformat(timestamp) or email_content_result.get('date', ''),
                        'client_info': email_data.client_info,
                        'is_business_relevant': True,
                        # Document information (only document_path exists in current schema)
                        'document_path': doc_result.get('path')
                    }
                    
                    self.database_service.store_processed_email(user_id, processed_email_data)
                    logger.info(f"Stored approved email {message_id} with document path in database")
                    
                except Exception as db_error:
                    logger.warning(f"Failed to store approved email {message_id} in database: {db_error}")
                    # Don't fail the whole operation if database storage fails
                
                return {
                    "success": True,
                    "message": "Email processed into Google Drive document successfully",
                    "document_path": doc_result.get('path'),
                    "document_url": doc_result.get('web_link'),
                    "file_id": doc_result.get('file_id'),
                    "storage_type": doc_result.get('storage_type')
                }
            else:
                logger.error(f"Failed to create document for approved email {message_id}")
                return {
                    "success": False,
                    "error": "Document creation failed"
                }
                
        except Exception as e:
            logger.error(f"Error processing approved email {message_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to process approved email: {str(e)}"
            }


# Create global instance
gmail_manager = GmailIntegrationManager() 