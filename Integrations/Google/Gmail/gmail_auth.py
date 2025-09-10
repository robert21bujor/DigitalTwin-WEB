"""
Gmail Authentication Service
Handles OAuth2 flow and token management for Gmail API integration
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Utils.config import Config

logger = logging.getLogger(__name__)


class GmailAuthService:
    """Handles Gmail OAuth2 authentication and token management"""
    
    # OAuth2 scopes for Gmail and future Google Workspace integrations
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/calendar.readonly',  # Future-proofing
        'https://www.googleapis.com/auth/drive.readonly',     # Future-proofing
        'https://www.googleapis.com/auth/drive',              # Google adds this automatically
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'  # Google adds this automatically
    ]
    
    REDIRECT_URI = 'http://localhost:3001/auth/gmail/callback'
    
    def __init__(self):
        """Initialize Gmail Auth Service"""
        self.client_config = self._load_client_config()
        self.credentials_cache = {}
        
    def _load_client_config(self) -> Dict[str, Any]:
        """Load Google OAuth2 client configuration"""
        try:
            config = Config.get_google_config()
            
            if not config or not config.get('client_id') or not config.get('client_secret'):
                logger.error("Google OAuth2 credentials not found in config")
                return {}
                
            return {
                "web": {
                    "client_id": config['client_id'],
                    "client_secret": config['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.REDIRECT_URI]
                }
            }
        except Exception as e:
            logger.error(f"Failed to load Google client config: {e}")
            return {}
    
    def get_authorization_url(self, user_id: str, state: Optional[str] = None) -> Optional[str]:
        """
        Generate OAuth2 authorization URL for Gmail access
        
        Args:
            user_id: User identifier for state management
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL or None if failed
        """
        try:
            if not self.client_config:
                logger.error("Google client config not available")
                return None
                
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.REDIRECT_URI
            )
            
            # Generate unique state for CSRF protection
            auth_state = state or f"user_{user_id}_{os.urandom(16).hex()}"
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                state=auth_state,
                prompt='consent'  # Force consent to get refresh token
            )
            
            logger.info(f"Generated Gmail auth URL for user {user_id}")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            return None
    
    def exchange_code_for_tokens(self, authorization_code: str, state: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access tokens"""
        try:
            # Validate configuration first
            config = Config.get_google_config()
            if not config:
                logger.error("Google configuration not found")
                return None
                
            # Check for missing credentials
            missing_credentials = []
            if not config.get('client_id'):
                missing_credentials.append('GOOGLE_CLIENT_ID')
            if not config.get('client_secret'):
                missing_credentials.append('GOOGLE_CLIENT_SECRET')
            if not config.get('project_id'):
                missing_credentials.append('GOOGLE_PROJECT_ID')
                
            if missing_credentials:
                logger.error(f"Missing Google OAuth credentials: {', '.join(missing_credentials)}")
                logger.error("Please set the following environment variables:")
                for cred in missing_credentials:
                    logger.error(f"  export {cred}='your-{cred.lower().replace('_', '-')}-here'")
                return None
            
            # Basic state validation (check if state exists and is not empty)
            if not state or len(state) < 10:
                logger.error("Invalid OAuth state parameter")
                return None
            
            logger.info(f"Attempting token exchange with client_id: {config['client_id'][:10]}...")
            logger.info(f"Using redirect_uri: {self.REDIRECT_URI}")
            logger.info(f"Authorization code length: {len(authorization_code)}")
            logger.info(f"State parameter: {state[:20]}...")
            
            # Try primary method with Google Flow
            client_config = {
                "web": {
                    "client_id": config['client_id'],
                    "client_secret": config['client_secret'],
                    "auth_uri": config['auth_uri'],
                    "token_uri": config['token_uri'],
                    "redirect_uris": [self.REDIRECT_URI]
                }
            }
            
            flow = Flow.from_client_config(
                client_config=client_config,
                scopes=self.SCOPES
            )
            flow.redirect_uri = self.REDIRECT_URI
            
            # Exchange code for credentials
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Validate credentials
            if not credentials or not credentials.token:
                logger.error("Invalid credentials received from Google")
                return None
            
            # Get user info
            user_info = self._get_user_info(credentials)
            
            token_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes) if credentials.scopes else self.SCOPES,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                'user_info': user_info
            }
            
            logger.info(f"Successfully exchanged code for tokens for user {user_info.get('email', 'unknown')}")
            return token_data
            
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            # Try fallback method
            fallback_result = self._exchange_code_manually(authorization_code)
            if fallback_result:
                return fallback_result
            else:
                logger.error("Both primary and fallback token exchange methods failed")
                return None
    
    def _exchange_code_manually(self, authorization_code: str) -> Optional[Dict[str, Any]]:
        """
        Manual token exchange as fallback when Flow fails
        """
        try:
            config = Config.get_google_config()
            if not config:
                return None
                
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'code': authorization_code,
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'redirect_uri': self.REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Create credentials object
                credentials = Credentials(
                    token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=config['client_id'],
                    client_secret=config['client_secret'],
                    scopes=self.SCOPES
                )
                
                # Get user info
                user_info = self._get_user_info(credentials)
                
                return {
                    'access_token': token_data.get('access_token'),
                    'refresh_token': token_data.get('refresh_token'),
                    'token_uri': "https://oauth2.googleapis.com/token",
                    'client_id': config['client_id'],
                    'client_secret': config['client_secret'],
                    'scopes': self.SCOPES,
                    'expiry': None,
                    'user_info': user_info
                }
            else:
                logger.error(f"Manual token exchange failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Manual token exchange error: {e}")
            return None
    
    def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get user information from Google API"""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'id': user_info.get('id')
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {}
    
    def refresh_access_token(self, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Refresh expired access token using refresh token
        
        Args:
            token_data: Existing token data with refresh_token
            
        Returns:
            Updated token data or None if failed
        """
        try:
            credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            # Update token data
            updated_token_data = token_data.copy()
            updated_token_data.update({
                'access_token': credentials.token,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            })
            
            logger.info("Successfully refreshed access token")
            return updated_token_data
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None
    
    def get_credentials(self, token_data: Dict[str, Any], user_id: str = None) -> Optional[Credentials]:
        """
        Create Credentials object from token data with automatic refresh and database update
        
        Args:
            token_data: Token data from database
            user_id: User ID to update database when tokens are refreshed
            
        Returns:
            Google Credentials object or None if invalid
        """
        try:
            # Parse expiry string to datetime object for Google Credentials
            expiry_datetime = None
            expiry_str = token_data.get('expiry')
            if expiry_str:
                try:
                    from datetime import datetime
                    expiry_datetime = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    # Convert to naive datetime for Google Credentials compatibility
                    expiry_datetime = expiry_datetime.replace(tzinfo=None)
                except Exception as e:
                    logger.warning(f"Failed to parse expiry time: {e}")
            
            credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes'),
                expiry=expiry_datetime  # Add expiry datetime
            )
            
            # Check if token needs refresh
            if credentials.expired and credentials.refresh_token:
                logger.info("🔄 Access token expired, refreshing automatically...")
                credentials.refresh(Request())
                
                # 🔥 AUTO-SAVE: Update database with refreshed tokens for infinite login
                if user_id:
                    try:
                        from Integrations.Google.Gmail.gmail_database import gmail_database
                        updated_token_data = {
                            'access_token': credentials.token,
                            'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                            'refresh_token': credentials.refresh_token  # Keep refresh token
                        }
                        
                        logger.info(f"🔄 Updating database with new token expiry: {updated_token_data.get('expiry')}")
                        success = gmail_database.update_gmail_tokens(user_id, updated_token_data)
                        if success:
                            logger.info("✅ Auto-saved refreshed tokens to database - staying logged in!")
                        else:
                            logger.error("❌ Failed to save refreshed tokens to database")
                            # Try to debug what went wrong
                            logger.error(f"Update data: {updated_token_data}")
                    except Exception as e:
                        logger.error(f"❌ Error auto-saving refreshed tokens: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.warning("⚠️ No user_id provided - cannot auto-save refreshed tokens")
                
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to create credentials: {e}")
            return None
    
    def test_gmail_connection(self, token_data: Dict[str, Any]) -> bool:
        """
        Test Gmail API connection with provided tokens
        
        Args:
            token_data: Token data to test
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            credentials = self.get_credentials(token_data)
            if not credentials:
                return False
                
            # Try to access Gmail API
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            
            logger.info(f"Gmail connection test successful for {profile.get('emailAddress')}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error during connection test: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to test Gmail connection: {e}")
            return False
    
    def revoke_tokens(self, token_data: Dict[str, Any]) -> bool:
        """
        Revoke Gmail access tokens
        
        Args:
            token_data: Token data to revoke
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            credentials = self.get_credentials(token_data)
            if not credentials:
                return False
                
            # Revoke the token using requests library
            revoke_url = f"https://oauth2.googleapis.com/revoke?token={credentials.token}"
            response = requests.post(revoke_url)
            
            if response.status_code == 200:
                logger.info("Successfully revoked Gmail tokens")
                return True
            else:
                logger.warning(f"Token revocation returned status {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to revoke tokens: {e}")
            return False


# Create global instance
gmail_auth_service = GmailAuthService() 