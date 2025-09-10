"""
ClickUp Authentication Service
Handles OAuth2 flow and token management for ClickUp API integration
"""

import os
import json
import logging
import secrets
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from Utils.config import Config

logger = logging.getLogger(__name__)


class ClickUpAuthService:
    """Handles ClickUp OAuth2 authentication and token management"""
    
    # OAuth2 scopes for ClickUp - starting minimal as per requirements
    SCOPES = [
        'read'  # Minimal scope for authentication and basic profile access
    ]
    
    # ClickUp OAuth endpoints (corrected format as specified by user)
    AUTH_URL = 'https://app.clickup.com/api'
    TOKEN_URL = 'https://api.clickup.com/api/v2/oauth/token'
    
    def __init__(self):
        """Initialize ClickUp OAuth service"""
        self.config = Config()
        self.client_id = os.getenv('CLICKUP_CLIENT_ID')
        self.client_secret = os.getenv('CLICKUP_CLIENT_SECRET')
        self.redirect_uri = os.getenv('CLICKUP_REDIRECT_URI', 'http://localhost:3001/clickup/callback')
        
        # Validate required configuration
        if not self.client_id or not self.client_secret:
            logger.error("ClickUp OAuth credentials not configured. Please set CLICKUP_CLIENT_ID and CLICKUP_CLIENT_SECRET")
        
        logger.info("ClickUp OAuth service initialized")
    
    def get_authorization_url(self, user_id: str) -> Optional[str]:
        """
        Generate ClickUp OAuth authorization URL for a user
        
        Args:
            user_id: User identifier for state tracking
            
        Returns:
            Authorization URL string or None if configuration missing
        """
        if not self.client_id:
            logger.error("ClickUp Client ID not configured")
            return None
        
        # Generate secure state parameter for CSRF protection (working version uses this)
        state = secrets.token_urlsafe(32)
        
        # Debug: Log the redirect URI being used
        logger.info(f"ClickUp OAuth Config - Client ID: {self.client_id[:10]}..., Redirect URI: {self.redirect_uri}")
        
        # ClickUp OAuth only supports client_id and redirect_uri parameters (as specified by user)
        auth_params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri
        }
        
        auth_url = f"{self.AUTH_URL}?{urlencode(auth_params)}"
        
        logger.info(f"Generated ClickUp authorization URL for user {user_id}: {auth_url}")
        return auth_url
    
    def exchange_code_for_token(self, code: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from ClickUp callback
            user_id: User identifier
            
        Returns:
            Token data dictionary or None if exchange failed
        """
        if not self.client_id or not self.client_secret:
            logger.error("ClickUp OAuth credentials not configured")
            return None
        
        try:
            # Prepare token exchange request
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            # Make token exchange request
            response = requests.post(
                self.TOKEN_URL,
                data=token_data,
                timeout=30
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Add metadata
                token_info['retrieved_at'] = datetime.utcnow().isoformat()
                token_info['user_id'] = user_id
                
                logger.info(f"Successfully exchanged code for token for user {user_id}")
                return token_info
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Refresh ClickUp access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            user_id: User identifier
            
        Returns:
            New token data dictionary or None if refresh failed
        """
        if not self.client_id or not self.client_secret:
            logger.error("ClickUp OAuth credentials not configured")
            return None
        
        try:
            # Prepare token refresh request
            refresh_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            # Make token refresh request
            response = requests.post(
                self.TOKEN_URL,
                data=refresh_data,
                timeout=30
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Add metadata
                token_info['retrieved_at'] = datetime.utcnow().isoformat()
                token_info['user_id'] = user_id
                
                logger.info(f"Successfully refreshed token for user {user_id}")
                return token_info
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error during token refresh: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            return None
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate ClickUp access token by making a test API call
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Make a simple API call to validate token
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://api.clickup.com/api/v2/user',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("ClickUp token validation successful")
                return True
            else:
                logger.warning(f"ClickUp token validation failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Network error during token validation: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            return False


# Create singleton instance
clickup_auth_service = ClickUpAuthService()
