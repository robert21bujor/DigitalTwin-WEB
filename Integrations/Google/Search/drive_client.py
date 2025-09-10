"""
Google Drive Client for Hybrid Search
Native Drive API client with pagination, retries, and query building
"""

import logging
import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from googleapiclient.errors import HttpError

from .auth_factory import get_auth_factory
from .query_interpreter import SearchSpec

logger = logging.getLogger(__name__)


@dataclass 
class DriveFile:
    """Google Drive file result"""
    id: str
    name: str
    mime_type: str
    size: Optional[int]
    modified_time: datetime
    created_time: datetime
    owners: List[str]
    parents: List[str]
    folder_path: str
    web_view_link: str
    download_link: str
    thumbnail_link: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "size": self.size,
            "modified_time": self.modified_time.isoformat(),
            "created_time": self.created_time.isoformat(),
            "owners": self.owners,
            "parents": self.parents,
            "folder_path": self.folder_path,
            "web_view_link": self.web_view_link,
            "download_link": self.download_link,
            "thumbnail_link": self.thumbnail_link,
            "description": self.description,
            "source": "drive",
            "type": "file",
            "file_type": self._get_file_type()
        }
    
    def _get_file_type(self) -> str:
        """Get human-readable file type"""
        mime_type_map = {
            'application/pdf': 'PDF Document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Spreadsheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint Presentation',
            'application/vnd.google-apps.document': 'Google Doc',
            'application/vnd.google-apps.spreadsheet': 'Google Sheets',
            'application/vnd.google-apps.presentation': 'Google Slides',
            'application/vnd.google-apps.folder': 'Folder',
            'image/jpeg': 'JPEG Image',
            'image/png': 'PNG Image',
            'text/plain': 'Text File'
        }
        return mime_type_map.get(self.mime_type, 'Unknown File Type')


class DriveClient:
    """
    Production-grade Google Drive client with native query support
    """
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.auth_factory = get_auth_factory()
        self._service = None
        self.max_results_per_page = int(os.getenv('DRIVE_PAGE_SIZE', '100'))
        self._folder_cache = {}
        
    @property
    def service(self):
        """Lazy-loaded Drive service"""
        if self._service is None:
            self._service = self.auth_factory.get_drive_service(self.user_id)
        return self._service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True
    )
    def search_files(self, 
                    query: str, 
                    max_results: int = 25,
                    include_folders: bool = False,
                    folder_filter: Optional[str] = None) -> List[DriveFile]:
        """
        Search Google Drive files with pagination and retries
        
        Args:
            query: Drive search query string (with proper operators)
            max_results: Maximum number of results to return
            include_folders: Whether to include folders in results
            folder_filter: Optional folder ID or path to restrict search
            
        Returns:
            List of DriveFile objects
        """
        logger.info(f"📁 Drive search: '{query}' (max: {max_results})")
        start_time = time.time()
        
        try:
            # Build final query with filters
            final_query = self._build_final_query(query, include_folders, folder_filter)
            
            files = []
            next_page_token = None
            
            while len(files) < max_results:
                # Calculate remaining results needed
                remaining = max_results - len(files)
                page_size = min(remaining, self.max_results_per_page)
                
                # Execute search request
                search_result = self._execute_search_request(
                    final_query, page_size, next_page_token
                )
                
                if not search_result.get('files'):
                    logger.info("📁 No more files found")
                    break
                
                # Process batch of files
                batch_files = self._process_file_batch(search_result['files'])
                files.extend(batch_files)
                
                # Check for next page
                next_page_token = search_result.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Trim to exact count
            files = files[:max_results]
            
            duration = time.time() - start_time
            logger.info(f"✅ Drive search completed: {len(files)} files in {duration:.2f}s")
            
            return files
            
        except HttpError as e:
            error_code = e.resp.status
            error_detail = e.error_details[0].get('message', str(e)) if e.error_details else str(e)
            
            logger.error(f"❌ Drive API error {error_code}: {error_detail}")
            
            if error_code == 400:
                logger.error(f"❌ Invalid query syntax: '{query}'")
            elif error_code == 403:
                logger.error("❌ Drive API quota exceeded or access denied")
            elif error_code == 401:
                logger.error("❌ Drive authentication failed")
            
            raise
            
        except Exception as e:
            logger.error(f"❌ Drive search failed: {e}")
            raise

    def _build_final_query(self, 
                          query: str, 
                          include_folders: bool = False, 
                          folder_filter: Optional[str] = None) -> str:
        """Build final Drive query with additional filters"""
        query_parts = []
        
        # Add main query if provided
        if query.strip():
            query_parts.append(f"({query})")
        
        # Filter out folders unless explicitly requested
        if not include_folders:
            query_parts.append("mimeType != 'application/vnd.google-apps.folder'")
        
        # Filter by folder if specified
        if folder_filter:
            folder_id = self._resolve_folder_filter(folder_filter)
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
        
        # Exclude trashed items
        query_parts.append("trashed = false")
        
        final_query = " and ".join(query_parts)
        logger.debug(f"📁 Final Drive query: '{final_query}'")
        return final_query

    def _resolve_folder_filter(self, folder_filter: str) -> Optional[str]:
        """Resolve folder filter to folder ID"""
        # If it's already a folder ID (looks like Google Drive ID)
        if len(folder_filter) > 20 and not '/' in folder_filter:
            return folder_filter
        
        # Try to resolve by path
        return self._find_folder_by_path(folder_filter)

    def _find_folder_by_path(self, path: str) -> Optional[str]:
        """Find folder ID by path (simple implementation)"""
        # This is a simplified implementation
        # In production, you'd want more sophisticated path resolution
        try:
            query = f"name = '{path}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            result = self.service.files().list(q=query, fields="files(id, name)").execute()
            
            files = result.get('files', [])
            if files:
                return files[0]['id']
        except Exception as e:
            logger.warning(f"⚠️ Failed to resolve folder path '{path}': {e}")
        
        return None

    def _execute_search_request(self, 
                               query: str, 
                               page_size: int, 
                               page_token: Optional[str] = None) -> Dict[str, Any]:
        """Execute single search request with proper error handling"""
        fields = (
            "nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime, "
            "owners(displayName, emailAddress), parents, webViewLink, thumbnailLink, description)"
        )
        
        request_params = {
            'q': query,
            'pageSize': page_size,
            'fields': fields,
            'orderBy': 'modifiedTime desc'  # Most recent first
        }
        
        if page_token:
            request_params['pageToken'] = page_token
        
        logger.debug(f"📁 Drive API request: q='{query}', pageSize={page_size}")
        
        return self.service.files().list(**request_params).execute()

    def _process_file_batch(self, files_data: List[Dict[str, Any]]) -> List[DriveFile]:
        """Process batch of file data from Drive API"""
        files = []
        
        for file_data in files_data:
            try:
                drive_file = self._parse_file_data(file_data)
                if drive_file:
                    files.append(drive_file)
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse file {file_data.get('id', 'unknown')}: {e}")
                continue
        
        return files

    def _parse_file_data(self, file_data: Dict[str, Any]) -> Optional[DriveFile]:
        """Parse Drive API file data into DriveFile object"""
        try:
            # Parse dates
            modified_time = self._parse_drive_datetime(file_data.get('modifiedTime'))
            created_time = self._parse_drive_datetime(file_data.get('createdTime'))
            
            # Extract owners
            owners = []
            for owner in file_data.get('owners', []):
                display_name = owner.get('displayName', owner.get('emailAddress', 'Unknown'))
                owners.append(display_name)
            
            # Get parents and folder path
            parents = file_data.get('parents', [])
            folder_path = self._get_folder_path(parents[0]) if parents else ""
            
            # Build download link
            download_link = f"https://drive.google.com/uc?id={file_data['id']}&export=download"
            
            return DriveFile(
                id=file_data['id'],
                name=file_data['name'],
                mime_type=file_data.get('mimeType', ''),
                size=int(file_data['size']) if file_data.get('size') else None,
                modified_time=modified_time,
                created_time=created_time,
                owners=owners,
                parents=parents,
                folder_path=folder_path,
                web_view_link=file_data.get('webViewLink', ''),
                download_link=download_link,
                thumbnail_link=file_data.get('thumbnailLink'),
                description=file_data.get('description')
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Drive file {file_data.get('id', 'unknown')}: {e}")
            return None

    def _parse_drive_datetime(self, datetime_str: Optional[str]) -> datetime:
        """Parse Drive API datetime string"""
        if not datetime_str:
            return datetime.now()
        
        try:
            # Drive API returns RFC 3339 format
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.now()

    def _get_folder_path(self, folder_id: str) -> str:
        """Get folder path by ID (with caching)"""
        if folder_id in self._folder_cache:
            return self._folder_cache[folder_id]
        
        try:
            # Get folder metadata
            folder = self.service.files().get(
                fileId=folder_id, 
                fields="name, parents"
            ).execute()
            
            folder_name = folder.get('name', f'Folder_{folder_id[:8]}')
            
            # Build path recursively (simplified)
            parents = folder.get('parents', [])
            if parents and parents[0] != folder_id:  # Avoid infinite recursion
                parent_path = self._get_folder_path(parents[0])
                path = f"{parent_path}/{folder_name}" if parent_path else folder_name
            else:
                path = folder_name
            
            # Cache the result
            self._folder_cache[folder_id] = path
            return path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get folder path for {folder_id}: {e}")
            # Return generic path
            generic_path = f"Folder_{folder_id[:8]}"
            self._folder_cache[folder_id] = generic_path
            return generic_path

    def build_query_from_spec(self, spec: SearchSpec) -> str:
        """
        Build Drive query from SearchSpec
        Delegates to QueryInterpreter but can add Drive-specific optimizations
        """
        from .query_interpreter import QueryInterpreter
        interpreter = QueryInterpreter()
        return interpreter.build_drive_query(spec)

    def get_file_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """
        Get file content for indexing/semantic search
        
        Args:
            file_id: Google Drive file ID
            mime_type: File MIME type
            
        Returns:
            File content as string if extractable, None otherwise
        """
        try:
            # For Google Workspace files, export as plain text
            if mime_type.startswith('application/vnd.google-apps'):
                export_mime_type = 'text/plain'
                content = self.service.files().export(
                    fileId=file_id, 
                    mimeType=export_mime_type
                ).execute()
                
                return content.decode('utf-8') if isinstance(content, bytes) else content
            
            # For other files, try to get content directly (if supported)
            elif mime_type in ['text/plain', 'text/csv']:
                content = self.service.files().get_media(fileId=file_id).execute()
                return content.decode('utf-8') if isinstance(content, bytes) else content
            
            else:
                # Binary files - return None (can't extract text content easily)
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to get content for file {file_id}: {e}")
            return None

    def test_connectivity(self) -> bool:
        """Test Drive API connectivity"""
        try:
            about = self.service.about().get(fields="user").execute()
            user_email = about.get('user', {}).get('emailAddress', 'unknown')
            logger.info(f"✅ Drive connectivity OK for: {user_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Drive connectivity failed: {e}")
            return False

    def get_storage_info(self) -> Dict[str, Any]:
        """Get Drive storage information"""
        try:
            about = self.service.about().get(fields="storageQuota, user").execute()
            quota = about.get('storageQuota', {})
            
            return {
                "user_email": about.get('user', {}).get('emailAddress'),
                "storage_limit": int(quota.get('limit', 0)),
                "storage_usage": int(quota.get('usage', 0)),
                "storage_usage_in_drive": int(quota.get('usageInDrive', 0)),
                "storage_usage_in_gmail": int(quota.get('usageInGmail', 0))
            }
        except Exception as e:
            logger.error(f"❌ Failed to get Drive storage info: {e}")
            return {}


# For backward compatibility
def get_drive_client(user_id: Optional[str] = None) -> DriveClient:
    """Factory function for Drive client"""
    return DriveClient(user_id)
