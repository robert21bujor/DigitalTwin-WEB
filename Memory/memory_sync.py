"""
Google Drive Memory Sync Engine
"""

import os
import json
import logging
import hashlib
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import asyncio

from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager
from Memory.Vector_store.enhanced_memory import EnhancedMemoryManager
from Memory.Vector_store.vector_store import VectorStoreManager  
from Memory.Indexing.file_processor import FileProcessor
from Utils.config import Config

# Gmail integration import  
from Integrations.Google.Gmail.gmail_database import gmail_database
from Integrations.Google.Gmail.gmail_auth import GmailAuthService

logger = logging.getLogger(__name__)


class GoogleDriveMemorySync:
    """Core synchronization logic for Google Drive memory sync using Gmail OAuth"""
    
    def __init__(self, user_id: str, root_folder_id: str = None):
        """
        Initialize Google Drive Memory Sync with Gmail OAuth
        
        Args:
            user_id: User ID to get Gmail OAuth tokens
            root_folder_id: Optional specific folder ID (uses root if None)
        """
        self.user_id = user_id
        self.root_folder_id = root_folder_id
        
        # Get Gmail OAuth tokens and initialize Google Drive service
        self.gmail_auth_service = GmailAuthService()
        self.drive_service = None
        self._initialize_drive_service()
        
        # Configuration
        memory_config = Config.get_memory_config()
        self.local_cache_dir = Path(memory_config["cache_dir"])
        self.sync_state_file = "Memory/Config/gdrive_sync_state.json"
        self.max_file_size = memory_config["max_file_size"]
        self.supported_extensions = memory_config["supported_extensions"]
        
        # Ensure cache directory exists
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize file processor
        self.file_processor = FileProcessor()
        
        # Agent folder mapping for categorizing documents by agent
        self.agent_folder_mapping = Config.get_agent_folder_mapping() if hasattr(Config, 'get_agent_folder_mapping') else {}
        
        # Initialize memory managers
        self.memory_managers = {}
        self._initialize_memory_managers()
    
    def _initialize_drive_service(self):
        """Initialize Google Drive service using Gmail OAuth tokens"""
        try:
            # Get Gmail OAuth tokens
            token_data = gmail_database.get_gmail_tokens(self.user_id)
            if not token_data:
                logger.error(f"No Gmail tokens found for user {self.user_id}")
                return False
            
            # Get credentials from Gmail auth service
            credentials = self.gmail_auth_service.get_credentials(token_data)
            if not credentials:
                logger.error("Failed to get valid credentials for Google Drive")
                return False
            
            # Build Google Drive service
            from googleapiclient.discovery import build
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
            logger.info(f"Google Drive service initialized for user {self.user_id} using Gmail OAuth")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Google Drive service: {e}")
            return False
    
    def _initialize_memory_managers(self):
        """Initialize memory managers for different agent types"""
        try:
            # Create enhanced memory managers for each agent category
            agent_categories = ['business_development', 'operations', 'marketing', 'executive', 'shared']
            
            for category in agent_categories:
                self.memory_managers[category] = EnhancedMemoryManager(
                    agent_name=f"agent_{category}",
                    collection_name=f"agent_memory_{category}",
                    lazy_init=True
                )
            
            logger.info("Memory managers initialized for all agent categories")
            
        except Exception as e:
            logger.error(f"Error initializing memory managers: {e}")
    
    async def sync_with_google_drive(self, force_full_sync: bool = False) -> bool:
        """Main sync method"""
        logger.info("Starting Google Drive memory sync...")
        
        try:
            # Step 1: Check Google Drive service
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return False
            
            # Step 2: Get current Google Drive state
            current_gdrive_state = self._get_gdrive_file_state()
            if not current_gdrive_state:
                logger.error("Failed to get Google Drive file state")
                return False
            
            # Step 3: Compare with local sync state
            changes = self._detect_changes(current_gdrive_state, force_full_sync)
            
            if not changes["added"] and not changes["modified"] and not changes["deleted"]:
                logger.info("No changes detected in Google Drive")
                return True
            
            # Step 4: Download changed files to cache
            if not await self._download_changed_files(changes["added"] + changes["modified"]):
                logger.error("Failed to download changed files")
                return False
            
            # Step 5: Process file changes
            if not await self._process_file_changes(changes):
                logger.error("Failed to process file changes")
                return False
            
            # Step 6: Update sync state
            self._save_sync_state(current_gdrive_state)
            
            logger.info("Google Drive memory sync completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
            return False
    
    def _get_gdrive_file_state(self) -> Dict[str, Dict]:
        """Get current state of all files in Google Drive"""
        try:
            folder_structure = self._get_folder_structure(self.root_folder_id)
            file_state = {}
            
            for folder_path, files in folder_structure.items():
                for file_info in files:
                    # Skip unsupported file types
                    file_name = file_info.get("name", "")
                    if not any(file_name.lower().endswith(ext) for ext in self.supported_extensions):
                        continue
                    
                    # Skip files that are too large
                    file_size = int(file_info.get("size", 0))
                    if file_size > self.max_file_size:
                        logger.warning(f"Skipping large file: {file_name} ({file_size} bytes)")
                        continue
                    
                    file_id = file_info["id"]
                    file_state[file_id] = {
                        "name": file_name,
                        "folder_path": folder_path or "__root__",
                        "modified_time": file_info.get("modifiedTime"),
                        "size": file_size,
                        "hash": file_info.get("md5Checksum", ""),
                        "mime_type": file_info.get("mimeType", "")
                    }
            
            logger.info(f"Found {len(file_state)} files in Google Drive")
            return file_state
            
        except Exception as e:
            logger.error(f"Error getting Google Drive file state: {str(e)}")
            return {}
    
    def _detect_changes(self, current_state: Dict[str, Dict], force_full_sync: bool = False) -> Dict[str, List]:
        """Detect changes between current and last sync state"""
        changes = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        try:
            if force_full_sync:
                # Treat all files as new
                changes["added"] = list(current_state.keys())
                return changes
            
            # Load last sync state
            last_sync_state = self._load_sync_state()
            if not last_sync_state:
                # First sync - all files are new
                changes["added"] = list(current_state.keys())
                return changes
            
            last_files = last_sync_state.get("files", {})
            
            # Find added and modified files
            for file_id, file_info in current_state.items():
                if file_id not in last_files:
                    changes["added"].append(file_id)
                elif (file_info.get("modified_time") != last_files[file_id].get("modified_time") or
                      file_info.get("hash") != last_files[file_id].get("hash")):
                    changes["modified"].append(file_id)
            
            # Find deleted files
            for file_id in last_files:
                if file_id not in current_state:
                    changes["deleted"].append(file_id)
            
            logger.info(f"Changes detected - Added: {len(changes['added'])}, "
                       f"Modified: {len(changes['modified'])}, Deleted: {len(changes['deleted'])}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting changes: {str(e)}")
            return changes
    
    async def _download_changed_files(self, file_ids: List[str]) -> bool:
        """Download changed files to local cache"""
        try:
            success_count = 0
            
            for file_id in file_ids:
                # Get file metadata
                metadata = self._get_file_metadata(file_id)
                if not metadata:
                    continue
                
                # Create local cache path
                file_name = metadata["name"]
                local_path = self.local_cache_dir / file_id / file_name
                
                # Download file
                if self._download_file(file_id, str(local_path)):
                    success_count += 1
                    logger.info(f"Downloaded {file_name}")
                else:
                    logger.error(f"Failed to download {file_name}")
            
            logger.info(f"Downloaded {success_count}/{len(file_ids)} files")
            return success_count == len(file_ids)
            
        except Exception as e:
            logger.error(f"Error downloading files: {str(e)}")
            return False
    
    async def _process_file_changes(self, changes: Dict[str, List]) -> bool:
        """Process file additions, modifications, deletions"""
        try:
            # Process added and modified files
            for file_id in changes["added"] + changes["modified"]:
                if not await self._process_file(file_id, "upsert"):
                    logger.error(f"Failed to process file {file_id}")
            
            # Process deleted files
            for file_id in changes["deleted"]:
                if not await self._process_file(file_id, "delete"):
                    logger.error(f"Failed to delete file {file_id}")
            
            logger.info("File change processing completed")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file changes: {str(e)}")
            return False
    
    async def _process_file(self, file_id: str, operation: str) -> bool:
        """Process a single file (upsert or delete)"""
        try:
            if operation == "delete":
                # Delete from all relevant collections
                for agent_name, memory_manager in self.memory_managers.items():
                    await memory_manager.delete_memory(file_id)
                return True
            
            # Get file info from current state
            current_state = self._get_gdrive_file_state()
            if file_id not in current_state:
                logger.warning(f"File {file_id} not found in current state")
                return False
            
            file_info = current_state[file_id]
            folder_path = file_info["folder_path"]
            
            # Determine which agent/collection this file belongs to
            agent_name, collection_name, is_shared = self._get_agent_for_folder(folder_path)
            if not agent_name:
                logger.warning(f"No agent mapping found for folder: {folder_path}")
                return False
            
            # Get the local file path
            local_path = self.local_cache_dir / file_id / file_info["name"]
            if not local_path.exists():
                logger.error(f"Local file not found: {local_path}")
                return False
            
            # Extract text content from file
            text_content = await self.file_processor.extract_text(str(local_path))
            if not text_content:
                logger.warning(f"No text content extracted from {file_info['name']}")
                return True  # Don't fail the sync for empty files
            
            # Prepare metadata
            metadata = {
                "memory_type": "document",
                "file_name": file_info["name"],
                "folder_path": folder_path,
                "file_size": file_info["size"],
                "modified_time": file_info["modified_time"],
                "mime_type": file_info["mime_type"],
                "source": "google_drive",
                "file_id": file_id
            }
            
            # Add to appropriate memory manager
            memory_manager = self.memory_managers.get(agent_name)
            if memory_manager:
                success = await memory_manager.add_memory(file_id, text_content, metadata)
                if success:
                    logger.info(f"Added {file_info['name']} to {agent_name} memory")
                return success
            else:
                logger.error(f"Memory manager not found for agent: {agent_name}")
                return False
            
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            return False
    
    def _get_agent_for_folder(self, folder_path: str) -> tuple:
        """Get agent info for a folder path"""
        # Try exact match first
        if folder_path in self.agent_folder_mapping:
            return self.agent_folder_mapping[folder_path]
        
        # Try to find best match for nested folders
        best_match = "__root__"  # Default to root
        for folder_name in self.agent_folder_mapping.keys():
            if folder_name != "__root__" and folder_name in folder_path:
                best_match = folder_name
                break
        
        return self.agent_folder_mapping.get(best_match, ("", "", False))
    
    def _load_sync_state(self) -> Optional[Dict]:
        """Load sync state from file"""
        try:
            state_file = Path(self.sync_state_file)
            if state_file.exists():
                with open(state_file, 'r') as f:
                    return json.load(f)
            return None
            
        except Exception as e:
            logger.error(f"Error loading sync state: {str(e)}")
            return None
    
    def _save_sync_state(self, file_state: Dict[str, Dict]):
        """Save sync state to file"""
        try:
            sync_state = {
                "last_sync": datetime.now().isoformat(),
                "gdrive_root_folder": self.root_folder_id,
                "files": file_state
            }
            
            with open(self.sync_state_file, 'w') as f:
                json.dump(sync_state, f, indent=2)
            
            logger.info("Sync state saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving sync state: {str(e)}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        try:
            sync_state = self._load_sync_state()
            if not sync_state:
                return {"status": "never_synced"}
            
            return {
                "status": "synced",
                "last_sync": sync_state.get("last_sync"),
                "total_files": len(sync_state.get("files", {})),
                "collections": list(self.memory_managers.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    # Helper methods for Google Drive API operations using Gmail OAuth
    
    def _get_folder_structure(self, root_folder_id: str = None, max_depth: int = 10, current_depth: int = 0, visited: set = None) -> Dict[str, List[Dict]]:
        """Get folder structure from Google Drive using direct API calls with recursion protection"""
        try:
            if not self.drive_service:
                return {}
            
            # Initialize visited set on first call
            if visited is None:
                visited = set()
            
            # Check depth limit to prevent infinite recursion
            if current_depth >= max_depth:
                logger.warning(f"Maximum recursion depth ({max_depth}) reached for folder {root_folder_id}")
                return {}
            
            # Check if we've already visited this folder to prevent cycles
            folder_key = root_folder_id or 'root'
            if folder_key in visited:
                logger.warning(f"Circular reference detected: folder {folder_key} already visited")
                return {}
            
            visited.add(folder_key)
            folder_structure = {}
            
            # Get all files and folders
            query = f"'{root_folder_id}' in parents" if root_folder_id else "parents in 'root'"
            query += " and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, parents, modifiedTime, size)",
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            
            # Process files and organize by folders
            for file_info in files:
                if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively get folder contents with increased depth and visited tracking
                    subfolder_structure = self._get_folder_structure(
                        file_info['id'], 
                        max_depth, 
                        current_depth + 1, 
                        visited.copy()  # Pass a copy to avoid modifying the current visited set
                    )
                    folder_structure.update(subfolder_structure)
                else:
                    # Add file to root or current folder
                    folder_path = root_folder_id or 'root'
                    if folder_path not in folder_structure:
                        folder_structure[folder_path] = []
                    
                    folder_structure[folder_path].append({
                        'id': file_info['id'],
                        'name': file_info['name'],
                        'mimeType': file_info['mimeType'],
                        'modifiedTime': file_info.get('modifiedTime'),
                        'size': int(file_info.get('size', 0)) if file_info.get('size') else 0
                    })
            
            return folder_structure
            
        except Exception as e:
            logger.error(f"Error getting folder structure: {e}")
            return {}
    
    def _get_file_metadata(self, file_id: str) -> Dict:
        """Get file metadata from Google Drive"""
        try:
            if not self.drive_service:
                return {}
            
            metadata = self.drive_service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, parents"
            ).execute()
            
            return {
                'id': metadata.get('id'),
                'name': metadata.get('name'),
                'mimeType': metadata.get('mimeType'),
                'size': int(metadata.get('size', 0)) if metadata.get('size') else 0,
                'modifiedTime': metadata.get('modifiedTime'),
                'parents': metadata.get('parents', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata for {file_id}: {e}")
            return {}
    
    def _download_file(self, file_id: str, local_path: str) -> bool:
        """Download file from Google Drive"""
        try:
            if not self.drive_service:
                return False
            
            from googleapiclient.http import MediaIoBaseDownload
            import io
            from pathlib import Path
            
            # Ensure the directory exists
            local_path_obj = Path(local_path)
            local_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            request = self.drive_service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            logger.info(f"Downloaded file {file_id} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return False 