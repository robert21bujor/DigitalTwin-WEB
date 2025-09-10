"""
ClickUp Database Service
Handles secure storage and retrieval of ClickUp tokens and configuration
"""

import json
import logging
import base64
import os
from datetime import datetime
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from supabase import Client
from Utils.config import Config

logger = logging.getLogger(__name__)


class ClickUpDatabase:
    """Handles ClickUp token storage and retrieval with encryption"""
    
    def __init__(self):
        """Initialize ClickUp database service"""
        self.config = Config()
        self.supabase_client = None
        self.encryption_key = None
        self.local_storage_path = "clickup_tokens.json"
        
        # Initialize Supabase client
        try:
            supabase_config = self.config.get_supabase_config()
            if supabase_config['url'] and supabase_config['anon_key']:
                from supabase import create_client
                self.supabase_client = create_client(
                    supabase_config['url'],
                    supabase_config['anon_key']
                )
                logger.info("ClickUp database service initialized with Supabase")
            else:
                logger.warning("Supabase configuration incomplete, using local file storage")
        except Exception as e:
            logger.warning(f"Supabase not available, using local file storage: {e}")
        
        # Initialize encryption
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption for token storage"""
        try:
            # Use a master password or generate one
            password = os.getenv('CLICKUP_ENCRYPTION_KEY', 'default-clickup-key').encode()
            salt = b'clickup-salt'  # In production, use random salt per user
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.encryption_key = Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to setup encryption: {e}")
            self.encryption_key = None
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.encryption_key:
            return data
        try:
            return self.encryption_key.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.encryption_key:
            return encrypted_data
        try:
            return self.encryption_key.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def _load_local_tokens(self) -> Dict[str, Any]:
        """Load tokens from local file"""
        try:
            if os.path.exists(self.local_storage_path):
                with open(self.local_storage_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading local tokens: {e}")
            return {}
    
    def _save_local_tokens(self, tokens: Dict[str, Any]) -> bool:
        """Save tokens to local file"""
        try:
            with open(self.local_storage_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving local tokens: {e}")
            return False
    
    def store_token(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """Store ClickUp token for a user"""
        if self.supabase_client:
            return self._store_token_supabase(user_id, token_data)
        else:
            return self._store_token_local(user_id, token_data)
    
    def _store_token_supabase(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """Store token using Supabase"""
        
        try:
            # Encrypt sensitive token data
            encrypted_access_token = self._encrypt_data(token_data.get('access_token', ''))
            encrypted_refresh_token = self._encrypt_data(token_data.get('refresh_token', ''))
            
            # Prepare data for storage
            storage_data = {
                'user_id': user_id,
                'access_token': encrypted_access_token,
                'refresh_token': encrypted_refresh_token,
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_in': token_data.get('expires_in'),
                'scope': token_data.get('scope', ''),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            # Upsert token data
            result = self.supabase_client.table('clickup_tokens').upsert(
                storage_data,
                on_conflict='user_id'
            ).execute()
            
            if result.data:
                logger.info(f"Successfully stored ClickUp token for user {user_id}")
                return True
            else:
                logger.error(f"Failed to store ClickUp token for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing ClickUp token: {e}")
            return False
    
    def _store_token_local(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """Store token using local file storage"""
        try:
            # Load existing tokens
            tokens = self._load_local_tokens()
            
            # Encrypt sensitive token data
            encrypted_access_token = self._encrypt_data(token_data.get('access_token', ''))
            encrypted_refresh_token = self._encrypt_data(token_data.get('refresh_token', ''))
            
            # Store token data
            tokens[user_id] = {
                'access_token': encrypted_access_token,
                'refresh_token': encrypted_refresh_token,
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_in': token_data.get('expires_in'),
                'scope': token_data.get('scope', ''),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            # Save to file
            success = self._save_local_tokens(tokens)
            if success:
                logger.info(f"Successfully stored ClickUp token locally for user {user_id}")
                return True
            else:
                logger.error(f"Failed to store ClickUp token locally for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing ClickUp token locally: {e}")
            return False
    
    def get_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ClickUp token for a user"""
        if self.supabase_client:
            return self._get_token_supabase(user_id)
        else:
            return self._get_token_local(user_id)
    
    def _get_token_supabase(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get token using Supabase"""
        
        try:
            result = self.supabase_client.table('clickup_tokens').select(
                '*'
            ).eq('user_id', user_id).eq('is_active', True).execute()
            
            if result.data:
                token_record = result.data[0]
                
                # Decrypt sensitive data
                token_data = {
                    'access_token': self._decrypt_data(token_record['access_token']),
                    'refresh_token': self._decrypt_data(token_record['refresh_token']),
                    'token_type': token_record['token_type'],
                    'expires_in': token_record['expires_in'],
                    'scope': token_record['scope'],
                    'created_at': token_record['created_at'],
                    'updated_at': token_record['updated_at']
                }
                
                logger.info(f"Successfully retrieved ClickUp token for user {user_id}")
                return token_data
            else:
                logger.info(f"No ClickUp token found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving ClickUp token: {e}")
            return None
    
    def _get_token_local(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get token using local file storage"""
        try:
            tokens = self._load_local_tokens()
            
            if user_id in tokens and tokens[user_id].get('is_active'):
                token_record = tokens[user_id]
                
                # Decrypt sensitive data
                token_data = {
                    'access_token': self._decrypt_data(token_record['access_token']),
                    'refresh_token': self._decrypt_data(token_record['refresh_token']),
                    'token_type': token_record['token_type'],
                    'expires_in': token_record['expires_in'],
                    'scope': token_record['scope'],
                    'created_at': token_record['created_at'],
                    'updated_at': token_record['updated_at']
                }
                
                logger.info(f"Successfully retrieved ClickUp token locally for user {user_id}")
                return token_data
            else:
                logger.info(f"No ClickUp token found locally for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving ClickUp token locally: {e}")
            return None
    
    def revoke_token(self, user_id: str) -> bool:
        """Revoke/deactivate ClickUp token for a user"""
        if self.supabase_client:
            return self._revoke_token_supabase(user_id)
        else:
            return self._revoke_token_local(user_id)
    
    def _revoke_token_supabase(self, user_id: str) -> bool:
        """Revoke token using Supabase"""
        
        try:
            result = self.supabase_client.table('clickup_tokens').update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).execute()
            
            if result.data:
                logger.info(f"Successfully revoked ClickUp token for user {user_id}")
                return True
            else:
                logger.error(f"Failed to revoke ClickUp token for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking ClickUp token: {e}")
            return False
    
    def _revoke_token_local(self, user_id: str) -> bool:
        """Revoke token using local file storage"""
        try:
            tokens = self._load_local_tokens()
            
            if user_id in tokens:
                tokens[user_id]['is_active'] = False
                tokens[user_id]['updated_at'] = datetime.utcnow().isoformat()
                
                success = self._save_local_tokens(tokens)
                if success:
                    logger.info(f"Successfully revoked ClickUp token locally for user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to revoke ClickUp token locally for user {user_id}")
                    return False
            else:
                logger.warning(f"No ClickUp token found to revoke for user {user_id}")
                return True  # Already revoked/doesn't exist
                
        except Exception as e:
            logger.error(f"Error revoking ClickUp token locally: {e}")
            return False
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has an active ClickUp connection"""
        token_data = self.get_token(user_id)
        return token_data is not None and token_data.get('access_token') is not None


# Create singleton instance
clickup_database = ClickUpDatabase()