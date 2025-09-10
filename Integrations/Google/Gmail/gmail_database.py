"""
Gmail Database Service
Handles secure storage of Gmail tokens and related data using Supabase
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from supabase import Client
from Utils.config import Config

logger = logging.getLogger(__name__)


class GmailDatabaseService:
    """Service for managing Gmail data in Supabase database"""
    
    def __init__(self):
        """Initialize Gmail Database Service"""
        self.supabase_client: Optional[Client] = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Initialize Supabase client with service role for token operations"""
        try:
            from supabase import create_client
            config = Config.get_supabase_config()
            
            supabase_url = config.get("url")
            # Use service role key to bypass RLS for token operations
            supabase_key = config.get("service_role_key") or config.get("key")
            
            if not supabase_url or not supabase_key:
                logger.error("Supabase credentials not found")
                return
                
            self.supabase_client = create_client(supabase_url, supabase_key)
            logger.info("Gmail database service initialized with Supabase")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    
    def store_gmail_tokens(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """
        Store Gmail OAuth tokens for a user
        
        Args:
            user_id: User identifier
            token_data: Token data from OAuth flow
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            if not self.supabase_client:
                logger.error("Supabase client not available")
                return False
            
            # 🔗 AUTO-LINK TO PLATFORM USER ACCOUNT
            platform_user_id = None
            gmail_email = token_data.get('user_info', {}).get('email')
            
            if gmail_email:
                try:
                    # Check if there's a platform user with this email in user_profiles
                    platform_user = self.supabase_client.table('user_profiles').select('username').eq('email', gmail_email).execute()
                    if platform_user.data:
                        platform_user_id = platform_user.data[0]['username']  # Use username as platform_user_id
                        logger.info(f"🔗 Auto-linking Gmail tokens to platform user: {platform_user_id}")
                    else:
                        logger.warning(f"⚠️ No platform user found for Gmail email: {gmail_email}")
                except Exception as e:
                    logger.error(f"❌ Error checking platform user: {e}")
            
            # Prepare token record
            token_record = {
                'user_id': user_id,
                'platform_user_id': platform_user_id,  # Link to platform user
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_uri': token_data.get('token_uri'),
                'client_id': token_data.get('client_id'),
                'client_secret': token_data.get('client_secret'),
                'scopes': json.dumps(token_data.get('scopes', [])),
                'expiry': token_data.get('expiry'),
                'gmail_email': gmail_email,
                'gmail_name': token_data.get('user_info', {}).get('name'),
                'gmail_user_id': token_data.get('user_info', {}).get('id'),
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Check if record already exists
            existing = self.supabase_client.table("gmail_tokens").select("*").eq("user_id", user_id).execute()
            
            if existing.data:
                # Update existing record
                result = self.supabase_client.table("gmail_tokens").update(token_record).eq("user_id", user_id).execute()
            else:
                # Insert new record
                result = self.supabase_client.table("gmail_tokens").insert(token_record).execute()
            
            if result.data:
                logger.info(f"Successfully stored Gmail tokens for user {user_id}")
                return True
            else:
                logger.error(f"Failed to store Gmail tokens for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing Gmail tokens: {e}")
            return False
    
    def get_gmail_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve Gmail tokens for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Token data dictionary or None if not found
        """
        try:
            if not self.supabase_client:
                logger.error("Supabase client not available")
                return None
            
            result = self.supabase_client.table("gmail_tokens").select("*").eq("user_id", user_id).eq("is_active", True).execute()
            
            if result.data and len(result.data) > 0:
                token_record = result.data[0]
                
                # Convert back to token format
                token_data = {
                    'access_token': token_record['access_token'],
                    'refresh_token': token_record['refresh_token'],
                    'token_uri': token_record['token_uri'],
                    'client_id': token_record['client_id'],
                    'client_secret': token_record['client_secret'],
                    'scopes': json.loads(token_record.get('scopes', '[]')),
                    'expiry': token_record.get('expiry'),
                    'user_info': {
                        'email': token_record.get('gmail_email'),
                        'name': token_record.get('gmail_name'),
                        'id': token_record.get('gmail_user_id')
                    }
                }
                
                logger.info(f"Retrieved Gmail tokens for user {user_id}")
                return token_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving Gmail tokens: {e}")
            return None
    
    def update_gmail_tokens(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """
        Update Gmail tokens for a user (e.g., after refresh)
        
        Args:
            user_id: User identifier
            token_data: Updated token data
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if not self.supabase_client:
                logger.error("Supabase client not available")
                return False
            
            update_data = {
                'access_token': token_data.get('access_token'),
                'expiry': token_data.get('expiry'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Only update refresh token if provided (it might not change)
            if token_data.get('refresh_token'):
                update_data['refresh_token'] = token_data['refresh_token']
            
            result = self.supabase_client.table("gmail_tokens").update(update_data).eq("user_id", user_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated Gmail tokens for user {user_id}")
                return True
            else:
                logger.error(f"Failed to update Gmail tokens for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Gmail tokens: {e}")
            return False
    
    def revoke_gmail_tokens(self, user_id: str) -> bool:
        """
        Revoke/deactivate Gmail tokens for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            if not self.supabase_client:
                logger.error("Supabase client not available")
                return False
            
            update_data = {
                'is_active': False,
                'access_token': None,
                'refresh_token': None,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase_client.table("gmail_tokens").update(update_data).eq("user_id", user_id).execute()
            
            if result.data:
                logger.info(f"Successfully revoked Gmail tokens for user {user_id}")
                return True
            else:
                logger.error(f"Failed to revoke Gmail tokens for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking Gmail tokens: {e}")
            return False
    
    def get_gmail_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get Gmail connection status for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with connection status information
        """
        try:
            if not self.supabase_client:
                return {
                    'connected': False,
                    'error': 'Database not available'
                }
            
            result = self.supabase_client.table("gmail_tokens").select("*").eq("user_id", user_id).eq("is_active", True).execute()
            
            if result.data and len(result.data) > 0:
                token_record = result.data[0]
                
                # Check if token is expired
                expiry_str = token_record.get('expiry')
                is_expired = False
                
                if expiry_str:
                    try:
                        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        # Ensure both times are timezone-aware for proper comparison
                        from datetime import timezone
                        current_time = datetime.now(timezone.utc)
                        is_expired = expiry_time <= current_time
                    except Exception:
                        is_expired = True
                
                return {
                    'connected': True,
                    'gmail_email': token_record.get('gmail_email'),
                    'gmail_name': token_record.get('gmail_name'),
                    'connected_at': token_record.get('created_at'),
                    'last_updated': token_record.get('updated_at'),
                    'is_expired': is_expired,
                    'expiry': expiry_str
                }
            
            return {
                'connected': False,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error getting Gmail connection status: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def store_processed_email(self, user_id: str, email_data: Dict[str, Any]) -> bool:
        """
        Store processed email metadata in the database
        
        Args:
            user_id: User identifier
            email_data: Processed email data
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            if not self.supabase_client:
                logger.error("No Supabase client available")
                return False
            
            # Prepare data for database
            processed_email_data = {
                'user_id': user_id,
                'message_id': email_data.get('message_id'),
                'thread_id': email_data.get('thread_id'),
                'sender_email': email_data.get('sender_email'),
                'subject': email_data.get('subject'),
                'timestamp': email_data.get('timestamp'),
                'client_name': email_data.get('client_info', {}).get('name', 'Unknown'),
                'client_domain': email_data.get('client_info', {}).get('domain', ''),
                'folder_path': email_data.get('client_info', {}).get('folder_path', 'Uncategorized'),
                'category': email_data.get('client_info', {}).get('category', 'unknown'),
                'confidence': email_data.get('client_info', {}).get('confidence', 'none'),
                'detection_method': email_data.get('client_info', {}).get('detection_method', 'none'),
                'is_business_relevant': email_data.get('is_business_relevant', False),
                'processed_at': datetime.utcnow().isoformat(),
                # Document information (only store document_path which exists in schema)
                'document_path': email_data.get('document_path')
            }
            
            # Insert into processed_emails table
            result = self.supabase_client.table("processed_emails").insert(processed_email_data).execute()
            
            if result.data:
                logger.info(f"Successfully stored processed email {email_data.get('message_id')} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to store processed email {email_data.get('message_id')} for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing processed email: {e}")
            return False
    
    def check_processed_emails(self, user_id: str, message_ids: List[str]) -> List[str]:
        """
        Check which message IDs have already been processed for a user
        
        Args:
            user_id: User identifier
            message_ids: List of Gmail message IDs to check
            
        Returns:
            List of message IDs that have already been processed
        """
        try:
            if not self.supabase_client:
                logger.error("No Supabase client available")
                return []
            
            if not message_ids:
                return []
            
            # Query for existing processed emails
            result = self.supabase_client.table("processed_emails").select("message_id").eq(
                "user_id", user_id
            ).in_("message_id", message_ids).execute()
            
            if result.data:
                existing_message_ids = [row['message_id'] for row in result.data]
                logger.info(f"Found {len(existing_message_ids)} already processed emails for user {user_id}")
                return existing_message_ids
            
            return []
            
        except Exception as e:
            logger.error(f"Error checking processed emails: {e}")
            return []


# Create global instance
gmail_database = GmailDatabaseService() 