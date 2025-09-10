"""
Google Authentication Factory
Centralized Google OAuth and Service Account management with domain-wide delegation support
"""

# CRITICAL: Import config first to load .env file
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from Utils.config import Config  # This loads .env file

import os
import json
import logging
from typing import Optional, Dict, Any, List
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleAuthFactory:
    """
    Centralized factory for Google API authentication
    Supports OAuth, Service Account, and Domain-wide delegation
    """
    
    # Google API scopes
    GMAIL_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.search'
    ]
    
    DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]
    
    ALL_SCOPES = GMAIL_SCOPES + DRIVE_SCOPES
    
    def __init__(self):
        self._clients_cache = {}
        self._credentials_cache = {}
        self._lock = threading.Lock()
        
        # Load configuration
        oauth_secrets_env = os.getenv('GOOGLE_OAUTH_CLIENT_SECRETS')
        # Make path absolute to avoid working directory issues
        if oauth_secrets_env and not os.path.isabs(oauth_secrets_env):
            # Get project root (4 levels up from this file)
            project_root = Path(__file__).parent.parent.parent.parent
            self.oauth_client_secrets_path = str(project_root / oauth_secrets_env)
        else:
            self.oauth_client_secrets_path = oauth_secrets_env
            
        self.service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.delegate_subject = os.getenv('GOOGLE_DELEGATE_SUBJECT')
        
        logger.info("🔑 GoogleAuthFactory initialized")
        if self.oauth_client_secrets_path:
            logger.info(f"📄 OAuth client secrets: {self.oauth_client_secrets_path}")
        if self.service_account_path:
            logger.info(f"🔧 Service account: {self.service_account_path}")
        if self.delegate_subject:
            logger.info(f"👤 Delegate subject: {self.delegate_subject}")

    def get_gmail_service(self, user_id: Optional[str] = None) -> Any:
        """
        Get authenticated Gmail service
        
        Args:
            user_id: Optional user ID for user-specific OAuth tokens
            
        Returns:
            Gmail service instance
        """
        cache_key = f"gmail_{user_id or 'default'}"
        
        with self._lock:
            if cache_key in self._clients_cache:
                return self._clients_cache[cache_key]
            
            try:
                credentials = self._get_credentials(self.GMAIL_SCOPES, user_id)
                service = build('gmail', 'v1', credentials=credentials)
                self._clients_cache[cache_key] = service
                logger.info(f"✅ Gmail service created for user: {user_id or 'default'}")
                return service
                
            except Exception as e:
                logger.error(f"❌ Failed to create Gmail service for {user_id}: {e}")
                raise

    def get_drive_service(self, user_id: Optional[str] = None) -> Any:
        """
        Get authenticated Drive service
        
        Args:
            user_id: Optional user ID for user-specific OAuth tokens
            
        Returns:
            Drive service instance  
        """
        cache_key = f"drive_{user_id or 'default'}"
        
        with self._lock:
            if cache_key in self._clients_cache:
                return self._clients_cache[cache_key]
            
            try:
                credentials = self._get_credentials(self.DRIVE_SCOPES, user_id)
                service = build('drive', 'v3', credentials=credentials)
                self._clients_cache[cache_key] = service
                logger.info(f"✅ Drive service created for user: {user_id or 'default'}")
                return service
                
            except Exception as e:
                logger.error(f"❌ Failed to create Drive service for {user_id}: {e}")
                raise

    def _get_credentials(self, scopes: List[str], user_id: Optional[str] = None) -> Credentials:
        """
        Get credentials with appropriate method (OAuth vs Service Account)
        
        Args:
            scopes: Required OAuth scopes
            user_id: Optional user ID for OAuth tokens
            
        Returns:
            Google credentials object
        """
        cache_key = f"creds_{hash(tuple(scopes))}_{user_id or 'default'}"
        
        if cache_key in self._credentials_cache:
            creds = self._credentials_cache[cache_key]
            if creds and creds.valid:
                return creds
        
        # Try service account with domain-wide delegation first
        if self.service_account_path and self.delegate_subject:
            try:
                creds = self._get_service_account_credentials(scopes, self.delegate_subject)
                if creds:
                    self._credentials_cache[cache_key] = creds
                    logger.info(f"✅ Using service account with delegation for: {user_id or 'default'}")
                    return creds
            except Exception as e:
                logger.warning(f"⚠️ Service account delegation failed: {e}")
        
        # Get credentials from existing Supabase OAuth system
        creds = self._get_supabase_credentials(user_id)
        
        if creds:
            self._credentials_cache[cache_key] = creds
            logger.info(f"✅ Using OAuth credentials for: {user_id or 'default'}")
            return creds
        
        raise Exception(f"Failed to obtain credentials for scopes: {scopes}")

    def _get_service_account_credentials(self, scopes: List[str], subject: str) -> Optional[Credentials]:
        """Get service account credentials with domain-wide delegation"""
        if not self.service_account_path or not os.path.exists(self.service_account_path):
            return None
        
        try:
            credentials = ServiceAccountCredentials.from_service_account_file(
                self.service_account_path, scopes=scopes
            )
            # Create delegated credentials for the subject
            delegated_credentials = credentials.with_subject(subject)
            
            logger.debug(f"🔧 Service account credentials created for subject: {subject}")
            return delegated_credentials
            
        except Exception as e:
            logger.error(f"❌ Service account credential creation failed: {e}")
            return None

    def _get_oauth_credentials(self, scopes: List[str], user_id: str) -> Optional[Credentials]:
        """Get OAuth credentials for specific user"""
        # Try to load existing token for this user
        token_file = self._get_user_token_path(user_id)
        
        creds = None
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), scopes)
                logger.debug(f"📄 Loaded existing token for user: {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load token for {user_id}: {e}")
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_user_token(creds, user_id)
                logger.debug(f"🔄 Refreshed token for user: {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Token refresh failed for {user_id}: {e}")
                creds = None
        
        # If no valid credentials, initiate OAuth flow
        if not creds or not creds.valid:
            creds = self._initiate_oauth_flow(scopes, user_id)
        
        return creds

    def _get_default_oauth_credentials(self, scopes: List[str]) -> Optional[Credentials]:
        """Get default OAuth credentials"""
        return self._get_oauth_credentials(scopes, "default")

    def _get_supabase_credentials(self, user_id: Optional[str] = None) -> Optional[Credentials]:
        """Get credentials from existing Supabase OAuth system"""
        if not user_id:
            logger.warning("⚠️ No user_id provided for Supabase credentials")
            return None
            
        try:
            # Import existing Gmail system
            from Integrations.Google.Gmail.gmail_database import gmail_database
            from Integrations.Google.Gmail.gmail_auth import GmailAuthService
            
            # Get tokens from Supabase
            token_data = gmail_database.get_gmail_tokens(user_id)
            if not token_data:
                logger.warning(f"⚠️ No Gmail tokens found in Supabase for user {user_id}")
                return None
            
            # Convert to Google credentials using existing auth service
            auth_service = GmailAuthService()
            credentials = auth_service.get_credentials(token_data, user_id)
            
            if credentials:
                logger.info(f"✅ Successfully loaded credentials from Supabase for user {user_id}")
                return credentials
            else:
                logger.warning(f"⚠️ Failed to create credentials from Supabase tokens for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting Supabase credentials for {user_id}: {e}")
            return None

    def get_colleague_credentials(self, requesting_user_id: str) -> List[Credentials]:
        """Get credentials for all colleagues that granted access to requesting user"""
        try:
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            # Get list of colleagues who granted access to this user
            colleague_access = self._get_colleague_permissions(requesting_user_id)
            
            credentials_list = []
            for colleague_user_id in colleague_access:
                creds = self._get_supabase_credentials(colleague_user_id)
                if creds:
                    credentials_list.append({
                        'user_id': colleague_user_id,
                        'credentials': creds
                    })
                    
            logger.info(f"✅ Loaded {len(credentials_list)} colleague credentials for {requesting_user_id}")
            return credentials_list
            
        except Exception as e:
            logger.error(f"❌ Error getting colleague credentials: {e}")
            return []
    
    def _get_colleague_permissions(self, user_id: str) -> List[str]:
        """Get list of colleague user_ids who granted access to this user"""
        try:
            # Import Supabase client from existing Gmail system
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            if not gmail_database.supabase_client:
                logger.warning("⚠️ Supabase client not available for colleague permissions")
                return []
            
            # Query colleague_permissions table
            # If table doesn't exist yet, we'll get an empty result
            try:
                response = gmail_database.supabase_client.table('colleague_permissions').select('granting_user_id').eq('requesting_user_id', user_id).execute()
                
                colleague_ids = [row['granting_user_id'] for row in response.data]
                logger.info(f"📋 Found {len(colleague_ids)} colleague permissions for user {user_id}")
                return colleague_ids
                
            except Exception as e:
                # Table might not exist yet - create it or return empty for now
                logger.info(f"ℹ️ Colleague permissions table not found: {e}")
                
                # For demo purposes, let's check if Hoang has granted permission
                # This simulates the permission system
                return self._get_demo_colleague_permissions(user_id)
                
        except Exception as e:
            logger.error(f"❌ Error getting colleague permissions: {e}")
            return []
    
    def _get_demo_colleague_permissions(self, requesting_user_id: str) -> List[str]:
        """Demo colleague permissions - checks if colleagues exist in Gmail tokens"""
        try:
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            # Get all users who have Gmail tokens (potential colleagues)
            if not gmail_database.supabase_client:
                return []
            
            try:
                # Get all Gmail token records to find potential colleagues
                response = gmail_database.supabase_client.table('gmail_tokens').select('user_id, gmail_email').execute()
                
                colleague_users = []
                for row in response.data:
                    colleague_user_id = row.get('user_id')
                    colleague_email = row.get('gmail_email', '')
                    
                    # Skip self
                    if colleague_user_id == requesting_user_id:
                        continue
                    
                    # For demo: auto-grant permission if colleague has "hoang" in email
                    if colleague_email and 'hoang' in colleague_email.lower():
                        colleague_users.append(colleague_user_id)
                        logger.info(f"🤝 Demo permission: {colleague_email} granted access to {requesting_user_id}")
                
                return colleague_users
                
            except Exception as e:
                logger.warning(f"⚠️ Could not check for demo colleagues: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in demo colleague permissions: {e}")
            return []

    def _get_user_token_path(self, user_id: str) -> Path:
        """Get path for user's token file"""
        # Store tokens in project's Auth directory
        auth_dir = Path(__file__).parent.parent.parent.parent / "Auth" / "tokens"
        auth_dir.mkdir(parents=True, exist_ok=True)
        return auth_dir / f"google_token_{user_id}.json"

    def _save_user_token(self, credentials: Credentials, user_id: str):
        """Save user token to file"""
        try:
            token_file = self._get_user_token_path(user_id)
            with open(token_file, 'w') as f:
                f.write(credentials.to_json())
            logger.debug(f"💾 Saved token for user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save token for {user_id}: {e}")

    def clear_cache(self):
        """Clear all cached clients and credentials"""
        with self._lock:
            self._clients_cache.clear()
            self._credentials_cache.clear()
            logger.info("🧹 Auth cache cleared")

    def test_connectivity(self, user_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Test connectivity to Google services
        
        Args:
            user_id: Optional user ID to test
            
        Returns:
            Dict with service connectivity status
        """
        results = {
            "gmail": False,
            "drive": False
        }
        
        # Test Gmail
        try:
            gmail = self.get_gmail_service(user_id)
            # Simple API call to test
            gmail.users().getProfile(userId='me').execute()
            results["gmail"] = True
            logger.info("✅ Gmail connectivity test passed")
        except Exception as e:
            logger.error(f"❌ Gmail connectivity test failed: {e}")
        
        # Test Drive
        try:
            drive = self.get_drive_service(user_id)
            # Simple API call to test
            drive.about().get(fields="user").execute()
            results["drive"] = True
            logger.info("✅ Drive connectivity test passed")
        except Exception as e:
            logger.error(f"❌ Drive connectivity test failed: {e}")
        
        return results


# Global factory instance
_auth_factory = None
_auth_factory_lock = threading.Lock()


def get_auth_factory() -> GoogleAuthFactory:
    """Get singleton GoogleAuthFactory instance"""
    global _auth_factory
    
    if _auth_factory is None:
        with _auth_factory_lock:
            if _auth_factory is None:
                _auth_factory = GoogleAuthFactory()
    
    return _auth_factory
