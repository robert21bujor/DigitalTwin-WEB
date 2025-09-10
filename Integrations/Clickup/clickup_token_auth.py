"""
ClickUp Personal Token Authentication Service
Alternative to OAuth when redirect URIs don't work
"""

import os
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ClickUpTokenAuthService:
    """Handles ClickUp Personal Token authentication"""
    
    def __init__(self):
        """Initialize ClickUp Token Auth Service"""
        self.base_url = "https://api.clickup.com/api/v2"
        
    def verify_token(self, personal_token: str) -> Dict[str, Any]:
        """
        Verify a ClickUp personal token and get user info
        
        Args:
            personal_token: ClickUp personal API token
            
        Returns:
            Dictionary with user info or error
        """
        try:
            headers = {
                'Authorization': personal_token,
                'Content-Type': 'application/json'
            }
            
            # Test the token by getting user info
            response = requests.get(
                f"{self.base_url}/user",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user_info = user_data.get('user', {})
                
                logger.info(f"ClickUp token verified for user: {user_info.get('username', 'unknown')}")
                
                return {
                    'success': True,
                    'user_info': {
                        'id': user_info.get('id'),
                        'username': user_info.get('username'),
                        'email': user_info.get('email'),
                        'color': user_info.get('color'),
                        'profile_picture': user_info.get('profilePicture')
                    },
                    'token_valid': True
                }
            else:
                logger.error(f"ClickUp token verification failed: {response.status_code}")
                return {
                    'success': False,
                    'error': f'Token verification failed: {response.status_code}',
                    'token_valid': False
                }
                
        except Exception as e:
            logger.error(f"Error verifying ClickUp token: {e}")
            return {
                'success': False,
                'error': str(e),
                'token_valid': False
            }
    
    def get_teams(self, personal_token: str) -> Dict[str, Any]:
        """
        Get user's teams to verify access
        
        Args:
            personal_token: ClickUp personal API token
            
        Returns:
            Dictionary with teams info
        """
        try:
            headers = {
                'Authorization': personal_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/team",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get('teams', [])
                
                logger.info(f"Retrieved {len(teams)} teams for user")
                
                return {
                    'success': True,
                    'teams': teams,
                    'teams_count': len(teams)
                }
            else:
                logger.error(f"Failed to get teams: {response.status_code}")
                return {
                    'success': False,
                    'error': f'Failed to get teams: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error getting teams: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance for easy import
clickup_token_auth = ClickUpTokenAuthService()
