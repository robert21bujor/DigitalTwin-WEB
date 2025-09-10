"""
ClickUp Integration Manager
Coordinates OAuth flow, token management, and connection status for ClickUp integration
"""

import logging
from typing import Optional, Dict, Any

from .clickup_auth import clickup_auth_service
from .clickup_database import clickup_database

logger = logging.getLogger(__name__)


class ClickUpIntegrationManager:
    """
    Main manager for ClickUp OAuth integration
    Provides high-level interface for authentication and connection management
    """
    
    def __init__(self):
        """Initialize ClickUp Integration Manager"""
        self.auth_service = clickup_auth_service
        self.database_service = clickup_database
        logger.info("ClickUp Integration Manager initialized")
    
    def get_auth_url(self, user_id: str) -> Optional[str]:
        """
        Get ClickUp OAuth authorization URL for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Authorization URL string or None if failed
        """
        try:
            auth_url = self.auth_service.get_authorization_url(user_id)
            
            if auth_url:
                logger.info(f"Generated ClickUp auth URL for user {user_id}")
                return auth_url
            else:
                logger.error(f"Failed to generate ClickUp auth URL for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting ClickUp auth URL: {e}")
            return None
    
    def handle_callback(self, code: str, user_id: str) -> Dict[str, Any]:
        """
        Handle ClickUp OAuth callback
        
        Args:
            code: Authorization code from ClickUp
            user_id: User identifier (passed from frontend)
            
        Returns:
            Dictionary with success status and details
        """
        try:
            if not user_id:
                logger.error("User ID is required for OAuth callback")
                return {"success": False, "error": "User ID is required"}
            
            # Exchange code for tokens
            token_data = self.auth_service.exchange_code_for_token(code, user_id)
            
            if not token_data:
                logger.error(f"Failed to exchange code for tokens for user {user_id}")
                return {"success": False, "error": "Token exchange failed"}
            
            # Store tokens securely
            storage_success = self.database_service.store_token(user_id, token_data)
            
            if not storage_success:
                logger.error(f"Failed to store tokens for user {user_id}")
                return {"success": False, "error": "Token storage failed"}
            
            logger.info(f"Successfully completed ClickUp OAuth for user {user_id}")
            return {
                "success": True,
                "user_id": user_id,
                "message": "ClickUp connection successful"
            }
            
        except Exception as e:
            logger.error(f"Error handling ClickUp callback: {e}")
            return {"success": False, "error": str(e)}
    
    def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get ClickUp connection status for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with connection status and details
        """
        try:
            is_connected = self.database_service.is_user_connected(user_id)
            
            if is_connected:
                token_data = self.database_service.get_token(user_id)
                
                # Validate token by making a test API call
                if token_data:
                    is_valid = self.auth_service.validate_token(token_data['access_token'])
                    
                    if is_valid:
                        return {
                            "connected": True,
                            "status": "active",
                            "message": "ClickUp connection is active and valid"
                        }
                    else:
                        # Try to refresh token
                        if token_data.get('refresh_token'):
                            new_token_data = self.auth_service.refresh_access_token(
                                token_data['refresh_token'], 
                                user_id
                            )
                            
                            if new_token_data:
                                # Store refreshed tokens
                                self.database_service.store_token(user_id, new_token_data)
                                
                                return {
                                    "connected": True,
                                    "status": "refreshed",
                                    "message": "ClickUp token refreshed successfully"
                                }
                        
                        return {
                            "connected": False,
                            "status": "expired",
                            "message": "ClickUp token expired and refresh failed"
                        }
                else:
                    return {
                        "connected": False,
                        "status": "error",
                        "message": "Token data corrupted"
                    }
            else:
                return {
                    "connected": False,
                    "status": "not_connected",
                    "message": "User has not connected ClickUp"
                }
                
        except Exception as e:
            logger.error(f"Error checking ClickUp connection status: {e}")
            return {
                "connected": False,
                "status": "error",
                "message": f"Error checking connection: {str(e)}"
            }
    
    def disconnect_user(self, user_id: str) -> Dict[str, Any]:
        """
        Disconnect user from ClickUp
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with success status and message
        """
        try:
            success = self.database_service.revoke_token(user_id)
            
            if success:
                logger.info(f"Successfully disconnected ClickUp for user {user_id}")
                return {
                    "success": True,
                    "message": "ClickUp disconnected successfully"
                }
            else:
                logger.error(f"Failed to disconnect ClickUp for user {user_id}")
                return {
                    "success": False,
                    "error": "Failed to disconnect ClickUp"
                }
            
        except Exception as e:
            logger.error(f"Error disconnecting ClickUp for user {user_id}: {e}")
            return {
                "success": False,
                "error": f"Error disconnecting: {str(e)}"
            }
    
    def get_user_access_token(self, user_id: str) -> Optional[str]:
        """
        Get valid access token for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Valid access token or None if not available
        """
        try:
            connection_status = self.get_connection_status(user_id)
            
            if connection_status["connected"] and connection_status["status"] in ["active", "refreshed"]:
                token_data = self.database_service.get_token(user_id)
                return token_data.get('access_token') if token_data else None
            else:
                logger.warning(f"Cannot get access token for user {user_id}: {connection_status['message']}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token for user {user_id}: {e}")
            return None


# Create singleton instance
clickup_manager = ClickUpIntegrationManager()