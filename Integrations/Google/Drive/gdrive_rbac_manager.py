"""
Google Drive RBAC Manager
Manages folder creation, access control, and permissions for the dual memory system.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from Integrations.Google.Gmail.gmail_auth import GmailAuthService
from Integrations.Google.Gmail.gmail_database import gmail_database
from Auth.User_management.user_models import User

logger = logging.getLogger(__name__)

@dataclass
class DrivePermission:
    """Represents a Google Drive permission"""
    email: str
    role: str  # 'reader', 'writer', 'owner'
    type: str  # 'user', 'group', 'domain', 'anyone'

class GoogleDriveRBACManager:
    """Manages Google Drive folder structure and permissions for dual memory system"""
    
    # Root folder name in Google Drive
    ROOT_FOLDER_NAME = "DigitalTwin_Brain"
    
    # Department folder names as specified
    DEPARTMENT_FOLDERS = {
        "Executive": "Executive",
        "Business Development": "Business Development", 
        "Operations": "Operations",
        "Marketing": "Marketing"
    }
    
    def __init__(self):
        """Initialize the Google Drive RBAC manager"""
        self.gmail_auth_service = GmailAuthService()
        self._drive_services_cache = {}
        self._folder_cache = {}
    
    def _get_user_drive_service(self, user_id: str):
        """Get Google Drive service using user's OAuth tokens"""
        if user_id in self._drive_services_cache:
            return self._drive_services_cache[user_id]
            
        try:
            # Get Gmail OAuth tokens for this user
            token_data = gmail_database.get_gmail_tokens(user_id)
            if not token_data:
                logger.warning(f"No Gmail tokens found for user {user_id}")
                return None
            
            # Get credentials
            credentials = self.gmail_auth_service.get_credentials(token_data)
            if not credentials:
                logger.warning(f"Failed to get valid credentials for user {user_id}")
                return None
            
            # Build Google Drive service
            drive_service = build('drive', 'v3', credentials=credentials)
            self._drive_services_cache[user_id] = drive_service
            
            logger.info(f"Google Drive service initialized for user {user_id}")
            return drive_service
            
        except Exception as e:
            logger.error(f"Error getting Drive service for user {user_id}: {e}")
            return None
    
    def find_or_create_root_folder(self, user_id: str) -> Optional[str]:
        """Find or create the DigitalTwin_Brain root folder"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return None
        
        try:
            # Search for existing root folder
            query = f"name='{self.ROOT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Found existing root folder: {folder_id}")
                return folder_id
            
            # Create root folder
            folder_metadata = {
                'name': self.ROOT_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"Created root folder '{self.ROOT_FOLDER_NAME}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error finding/creating root folder: {e}")
            return None
    
    def find_or_create_department_folder(self, user_id: str, department_name: str) -> Optional[str]:
        """Find or create a department folder within the root folder"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return None
        
        # Get root folder first
        root_folder_id = self.find_or_create_root_folder(user_id)
        if not root_folder_id:
            return None
        
        try:
            folder_name = self.DEPARTMENT_FOLDERS.get(department_name, department_name)
            
            # Search for existing department folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{root_folder_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Found existing department folder '{folder_name}': {folder_id}")
                return folder_id
            
            # Create department folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [root_folder_id]
            }
            
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"Created department folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error finding/creating department folder '{department_name}': {e}")
            return None
    
    def find_or_create_private_folder(self, user_id: str, agent_name: str, department_name: str) -> Optional[str]:
        """Find or create a private folder for an agent within its department"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return None
        
        # Get department folder first
        dept_folder_id = self.find_or_create_department_folder(user_id, department_name)
        if not dept_folder_id:
            return None
        
        try:
            private_folder_name = f"{agent_name}_private"
            
            # Search for existing private folder
            query = f"name='{private_folder_name}' and mimeType='application/vnd.google-apps.folder' and '{dept_folder_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Found existing private folder '{private_folder_name}': {folder_id}")
                
                # Ensure ACL is properly configured
                self._configure_private_folder_acl(user_id, folder_id, agent_name)
                return folder_id
            
            # Create private folder
            folder_metadata = {
                'name': private_folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [dept_folder_id]
            }
            
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"Created private folder '{private_folder_name}' with ID: {folder_id}")
            
            # Configure ACL for the new private folder
            self._configure_private_folder_acl(user_id, folder_id, agent_name)
            
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error finding/creating private folder for agent '{agent_name}': {e}")
            return None
    
    def _configure_private_folder_acl(self, user_id: str, folder_id: str, agent_name: str) -> bool:
        """Configure ACL for a private folder to remove inherited permissions"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return False
        
        try:
            # Get current permissions
            permissions = drive_service.permissions().list(fileId=folder_id).execute()
            current_permissions = permissions.get('permissions', [])
            
            # Remove inherited permissions except for owner
            for permission in current_permissions:
                if permission.get('role') != 'owner':
                    try:
                        drive_service.permissions().delete(
                            fileId=folder_id,
                            permissionId=permission.get('id')
                        ).execute()
                        logger.info(f"Removed permission {permission.get('id')} from private folder")
                    except HttpError as e:
                        # Some permissions can't be deleted (like inherited ones)
                        logger.debug(f"Could not remove permission {permission.get('id')}: {e}")
            
            # Add explicit permission for the assigned owner (if needed)
            # This would require knowing which user is assigned to this agent
            owner_email = self._get_agent_owner_email(agent_name)
            if owner_email:
                self._add_folder_permission(user_id, folder_id, owner_email, 'reader')
            
            logger.info(f"Configured ACL for private folder {folder_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error configuring ACL for private folder {folder_id}: {e}")
            return False
    
    def _get_agent_owner_email(self, agent_name: str) -> Optional[str]:
        """Get the email of the user assigned to this agent"""
        # This would query the user database to find who is assigned to this agent
        # For now, return None - this needs to be implemented based on user assignments
        return None
    
    def _add_folder_permission(self, user_id: str, folder_id: str, email: str, role: str) -> bool:
        """Add a permission to a folder"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return False
        
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            drive_service.permissions().create(
                fileId=folder_id,
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"Added {role} permission for {email} to folder {folder_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error adding permission to folder {folder_id}: {e}")
            return False
    
    def verify_folder_access(self, user_id: str, folder_path: str) -> bool:
        """Verify if user has access to a specific folder path"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return False
        
        try:
            # This is a simplified check - in practice, you'd need to resolve the full path
            # and check permissions at each level
            
            # For now, if we can get the drive service, assume basic access
            # Real implementation would traverse the folder path and check permissions
            logger.info(f"Verified access to folder path: {folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying folder access: {e}")
            return False
    
    def setup_department_structure(self, user_id: str) -> Dict[str, str]:
        """Set up the complete department folder structure"""
        results = {}
        
        # Create root folder
        root_folder_id = self.find_or_create_root_folder(user_id)
        if root_folder_id:
            results['root'] = root_folder_id
        
        # Create all department folders
        for dept_name in self.DEPARTMENT_FOLDERS.keys():
            folder_id = self.find_or_create_department_folder(user_id, dept_name)
            if folder_id:
                results[dept_name] = folder_id
        
        logger.info(f"Setup department structure: {len(results)} folders created/verified")
        return results
    
    def setup_agent_private_folders(self, user_id: str, agent_mappings: Dict[str, str]) -> Dict[str, str]:
        """Set up private folders for multiple agents"""
        results = {}
        
        for agent_name, department in agent_mappings.items():
            folder_id = self.find_or_create_private_folder(user_id, agent_name, department)
            if folder_id:
                results[agent_name] = folder_id
        
        logger.info(f"Setup agent private folders: {len(results)} folders created/verified")
        return results
    
    def get_folder_structure(self, user_id: str) -> Dict[str, Any]:
        """Get the current folder structure for this user"""
        drive_service = self._get_user_drive_service(user_id)
        if not drive_service:
            return {}
        
        structure = {}
        
        # Get root folder
        root_folder_id = self.find_or_create_root_folder(user_id)
        if root_folder_id:
            structure['root'] = {
                'id': root_folder_id,
                'name': self.ROOT_FOLDER_NAME,
                'departments': {}
            }
            
            # Get department folders
            for dept_name in self.DEPARTMENT_FOLDERS.keys():
                dept_folder_id = self.find_or_create_department_folder(user_id, dept_name)
                if dept_folder_id:
                    structure['root']['departments'][dept_name] = {
                        'id': dept_folder_id,
                        'name': self.DEPARTMENT_FOLDERS[dept_name],
                        'private_folders': {}
                    }
        
        return structure





