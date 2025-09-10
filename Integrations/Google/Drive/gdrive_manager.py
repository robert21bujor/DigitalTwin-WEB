"""
Google Drive Manager for file operations and authentication
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import io
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file'  # Allow uploading files
]


class RateLimitHandler:
    """Handle Google Drive API rate limits"""
    
    def __init__(self, max_requests_per_minute: int = 100):
        self.max_requests = max_requests_per_minute
        self.request_times = []
        
    def wait_if_needed(self):
        """Wait if approaching rate limit"""
        import time
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        if len(self.request_times) >= self.max_requests:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit approached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.request_times.append(current_time)


class GoogleDriveManager:
    """Google Drive API manager for file operations"""
    
    def __init__(self, credentials_path: str, token_path: str):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.rate_limiter = RateLimitHandler()
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Credentials file not found: {self.credentials_path}")
                        return False
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def list_folder_contents(self, folder_id: str) -> List[Dict]:
        """Get all files in a Google Drive folder recursively"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return []
        
        try:
            all_files = []
            page_token = None
            
            while True:
                self.rate_limiter.wait_if_needed()
                
                results = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    pageSize=100,
                    fields="nextPageToken, files(id, name, parents, modifiedTime, size, mimeType)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                all_files.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            # Recursively get files from subfolders
            for item in items.copy():
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    subfolder_files = self.list_folder_contents(item['id'])
                    all_files.extend(subfolder_files)
            
            logger.info(f"Found {len(all_files)} files in folder {folder_id}")
            return all_files
            
        except HttpError as e:
            logger.error(f"Error listing folder contents: {str(e)}")
            return []
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Download file from Google Drive to local cache"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.rate_limiter.wait_if_needed()
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
            
            # Write the file to local path
            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Downloaded file {file_id} to {local_path}")
            return True
            
        except HttpError as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            return False
    
    def download_file_to_memory(self, file_id: str) -> Optional[bytes]:
        """Download file directly to memory without caching to disk"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return None
        
        try:
            self.rate_limiter.wait_if_needed()
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content = fh.getvalue()
            logger.info(f"Downloaded file {file_id} to memory ({len(file_content)} bytes)")
            return file_content
            
        except HttpError as e:
            logger.error(f"Error downloading file {file_id} to memory: {str(e)}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Dict:
        """Get file metadata (name, modified_time, size, etc.)"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return {}
        
        try:
            self.rate_limiter.wait_if_needed()
            
            metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, parents, modifiedTime, size, mimeType, md5Checksum"
            ).execute()
            
            return metadata
            
        except HttpError as e:
            logger.error(f"Error getting file metadata for {file_id}: {str(e)}")
            return {}
    
    def get_folder_structure(self, root_folder_id: str) -> Dict:
        """Get hierarchical folder structure for agent mapping"""
        if not self.service:
            logger.error("Not authenticated with Google Drive")
            return {}
        
        try:
            folder_structure = {}
            
            def _get_folder_path(folder_id: str, visited=None) -> str:
                if visited is None:
                    visited = set()
                
                if folder_id in visited:
                    return "/"  # Circular reference protection
                
                visited.add(folder_id)
                
                if folder_id == root_folder_id:
                    return ""
                
                try:
                    self.rate_limiter.wait_if_needed()
                    folder_info = self.service.files().get(
                        fileId=folder_id,
                        fields="name, parents"
                    ).execute()
                    
                    if 'parents' in folder_info:
                        parent_path = _get_folder_path(folder_info['parents'][0], visited)
                        return f"{parent_path}/{folder_info['name']}" if parent_path else folder_info['name']
                    else:
                        return folder_info['name']
                        
                except HttpError:
                    return "Unknown"
            
            # Get all files and build structure
            all_files = self.list_folder_contents(root_folder_id)
            
            for file_info in all_files:
                if 'parents' in file_info:
                    parent_id = file_info['parents'][0]
                    folder_path = _get_folder_path(parent_id)
                    
                    if folder_path not in folder_structure:
                        folder_structure[folder_path] = []
                    
                    folder_structure[folder_path].append(file_info)
            
            return folder_structure
            
        except Exception as e:
            logger.error(f"Error getting folder structure: {str(e)}")
            return {}
    
    def test_connection(self) -> bool:
        """Test Google Drive connection"""
        if not self.service:
            return False
        
        try:
            self.rate_limiter.wait_if_needed()
            about = self.service.about().get(fields="user").execute()
            logger.info(f"Connected to Google Drive as: {about['user']['emailAddress']}")
            return True
            
        except HttpError as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False 
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """
        Create a folder in Google Drive
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID if created successfully, None otherwise
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            self.rate_limiter.wait_if_needed()
            
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info(f"Created folder '{name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder '{name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating folder '{name}': {e}")
            return None
    
    def find_or_create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """
        Find existing folder or create new one
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID if found/created successfully, None otherwise
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            self.rate_limiter.wait_if_needed()
            
            # Search for existing folder
            query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Found existing folder '{name}' with ID: {folder_id}")
                return folder_id
            else:
                # Create new folder
                return self.create_folder(name, parent_id)
                
        except Exception as e:
            logger.error(f"Error finding/creating folder '{name}': {e}")
            return None
    
    def upload_file(self, file_path: str, folder_id: str = None, 
                   drive_filename: str = None) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to local file
            folder_id: Google Drive folder ID (None for root)
            drive_filename: Custom filename in Drive (uses local filename if None)
            
        Returns:
            File ID if uploaded successfully, None otherwise
        """
        if not self.service:
            logger.error("Google Drive service not initialized")
            return None
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            filename = drive_filename or file_path.name
            
            # Detect MIME type
            mime_type = 'application/octet-stream'  # Default
            if file_path.suffix.lower() == '.docx':
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif file_path.suffix.lower() == '.pdf':
                mime_type = 'application/pdf'
            elif file_path.suffix.lower() in ['.txt']:
                mime_type = 'text/plain'
            
            self.rate_limiter.wait_if_needed()
            
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(str(file_path), mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            logger.info(f"Uploaded file '{filename}' to Google Drive with ID: {file_id}")
            logger.info(f"File link: {web_link}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading file '{file_path}': {e}")
            return None
    
    def create_folder_path(self, folder_path: str, root_folder_id: str = None) -> Optional[str]:
        """
        Create a nested folder structure in Google Drive
        
        Args:
            folder_path: Path like "Clients/Internal/Repsmate Team"
            root_folder_id: Root folder ID (None for Drive root)
            
        Returns:
            Final folder ID if created successfully, None otherwise
        """
        if not folder_path:
            return root_folder_id
        
        folder_parts = [part.strip() for part in folder_path.split('/') if part.strip()]
        current_parent_id = root_folder_id
        
        for folder_name in folder_parts:
            folder_id = self.find_or_create_folder(folder_name, current_parent_id)
            if not folder_id:
                logger.error(f"Failed to create/find folder: {folder_name}")
                return None
            current_parent_id = folder_id
        
        return current_parent_id 