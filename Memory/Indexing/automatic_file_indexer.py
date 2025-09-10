"""
Automatic File Indexer with Dual Memory RBAC Integration
Monitors Google Drive folders and automatically indexes files with proper access controls.
"""

import os
import sys
import logging
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Memory.unified_rbac_service import get_unified_rbac_service
from Integrations.Google.Drive.gdrive_manager import GoogleDriveManager
from Memory.Indexing.file_processor import FileProcessor
from Auth.User_management.user_models import User, UserRole, AgentType, AgentAssignment
from Auth.User_management.auth_manager import AuthManager

logger = logging.getLogger(__name__)

class AutomaticFileIndexer:
    """Automatically indexes Google Drive files into the dual memory RBAC system"""
    
    def __init__(self, user_id: str):
        """
        Initialize the automatic file indexer
        
        Args:
            user_id: User ID to use for Google Drive access
        """
        self.user_id = user_id
        self.rbac_service = get_unified_rbac_service()
        self.drive_manager = GoogleDriveManager(user_id)
        self.file_processor = FileProcessor()
        self.auth_manager = AuthManager()
        
        # Cache for processed files to avoid reprocessing
        self.processed_files = set()
        
        # Folder mapping for determining agent and department
        self.folder_mappings = {
            # Department public folders
            "Business Development": {"type": "public", "department": "business_development", "agents": ["bdm", "ipm", "presales_engineer"]},
            "Marketing": {"type": "public", "department": "marketing", "agents": ["content", "seo", "analytics"]},
            "Operations": {"type": "public", "department": "operations", "agents": ["head_of_operations", "senior_csm", "legal"]},
            "Executive": {"type": "public", "department": "executive", "agents": ["cmo"]},
            
            # Private folder patterns (will be detected by name ending with "_private")
        }
    
    async def scan_and_index_all_files(self) -> Dict[str, Any]:
        """Scan all files in DigitalTwin_Brain and index them appropriately"""
        logger.info(f"🔍 Starting automatic file indexing for user {self.user_id}")
        
        results = {
            "public_files_indexed": 0,
            "private_files_indexed": 0,
            "errors": 0,
            "skipped_files": 0,
            "file_details": []
        }
        
        try:
            # Find the DigitalTwin_Brain folder
            brain_folder = await self._find_brain_folder()
            if not brain_folder:
                logger.error("DigitalTwin_Brain folder not found")
                return results
            
            logger.info(f"Found DigitalTwin_Brain folder: {brain_folder['name']}")
            
            # Get all folders in DigitalTwin_Brain
            folders = await self._get_folders_in_brain(brain_folder['id'])
            
            # Process each folder
            for folder in folders:
                folder_results = await self._process_folder(folder)
                
                # Aggregate results
                results["public_files_indexed"] += folder_results["public_files"]
                results["private_files_indexed"] += folder_results["private_files"]
                results["errors"] += folder_results["errors"]
                results["skipped_files"] += folder_results["skipped"]
                results["file_details"].extend(folder_results["details"])
                
                logger.info(f"📁 Processed folder '{folder['name']}': "
                          f"{folder_results['public_files']} public, "
                          f"{folder_results['private_files']} private, "
                          f"{folder_results['errors']} errors")
            
            total_indexed = results["public_files_indexed"] + results["private_files_indexed"]
            logger.info(f"✅ Indexing complete: {total_indexed} files indexed, {results['errors']} errors")
            
        except Exception as e:
            logger.error(f"Error during automatic file indexing: {e}")
            results["errors"] += 1
        
        return results
    
    async def _find_brain_folder(self) -> Optional[Dict]:
        """Find the DigitalTwin_Brain folder"""
        try:
            query = "name='DigitalTwin_Brain' and mimeType='application/vnd.google-apps.folder'"
            response = self.drive_manager.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, parents, mimeType)'
            ).execute()
            
            files = response.get('files', [])
            if files:
                return files[0]  # Return the first match
            return None
            
        except Exception as e:
            logger.error(f"Error finding DigitalTwin_Brain folder: {e}")
            return None
    
    async def _get_folders_in_brain(self, brain_folder_id: str) -> List[Dict]:
        """Get all folders inside DigitalTwin_Brain"""
        try:
            query = f"'{brain_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            response = self.drive_manager.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, parents, mimeType)'
            ).execute()
            
            return response.get('files', [])
            
        except Exception as e:
            logger.error(f"Error getting folders in DigitalTwin_Brain: {e}")
            return []
    
    async def _process_folder(self, folder: Dict) -> Dict[str, Any]:
        """Process all files in a folder"""
        results = {"public_files": 0, "private_files": 0, "errors": 0, "skipped": 0, "details": []}
        
        folder_name = folder['name']
        folder_id = folder['id']
        
        # Determine if this is a public department folder or private agent folder
        is_private = folder_name.endswith('_private')
        
        if is_private:
            # Extract agent name from private folder
            agent_name = folder_name[:-8]  # Remove "_private" suffix
            agent_type, department = self._get_agent_info(agent_name)
            
            if not agent_type:
                logger.warning(f"Unknown agent for private folder: {folder_name}")
                results["errors"] += 1
                return results
            
            # Process private files
            folder_results = await self._process_private_folder(folder_id, agent_name, agent_type, department)
            
        else:
            # Check if this is a known department folder
            if folder_name in self.folder_mappings:
                dept_config = self.folder_mappings[folder_name]
                
                # Process public department files
                folder_results = await self._process_public_folder(folder_id, folder_name, dept_config)
            else:
                logger.info(f"Skipping unknown folder: {folder_name}")
                results["skipped"] += 1
                return results
        
        # Merge results
        for key in ["public_files", "private_files", "errors", "skipped"]:
            results[key] += folder_results.get(key, 0)
        results["details"].extend(folder_results.get("details", []))
        
        return results
    
    async def _process_public_folder(self, folder_id: str, folder_name: str, dept_config: Dict) -> Dict[str, Any]:
        """Process files in a public department folder"""
        results = {"public_files": 0, "private_files": 0, "errors": 0, "skipped": 0, "details": []}
        
        try:
            # Get all files in the folder
            files = await self._get_files_in_folder(folder_id)
            
            # Get a representative user for this department (use first agent)
            user = await self._get_user_for_agent(dept_config["agents"][0])
            if not user:
                logger.error(f"No user found for department {folder_name}")
                results["errors"] += 1
                return results
            
            # Process each file
            for file_info in files:
                try:
                    # Download and extract content
                    content = await self._extract_file_content(file_info)
                    if not content:
                        results["skipped"] += 1
                        continue
                    
                    # Index into public memory for each agent in the department
                    for agent_name in dept_config["agents"]:
                        memory_id = f"public_{file_info['name'].replace('.', '_').replace(' ', '_').lower()}_{file_info['id']}"
                        
                        success = self.rbac_service.add_public_memory(
                            user=user,
                            agent_name=agent_name,
                            memory_id=memory_id,
                            content=content,
                            metadata={
                                "filename": file_info['name'],
                                "source": "google_drive",
                                "folder": folder_name,
                                "file_id": file_info['id'],
                                "department": dept_config["department"],
                                "confidentiality": "public"
                            }
                        )
                        
                        if success:
                            results["public_files"] += 1
                            results["details"].append({
                                "file": file_info['name'],
                                "type": "public",
                                "agent": agent_name,
                                "department": dept_config["department"]
                            })
                            logger.info(f"✅ Indexed public file '{file_info['name']}' for agent {agent_name}")
                        else:
                            results["errors"] += 1
                            logger.error(f"❌ Failed to index public file '{file_info['name']}' for agent {agent_name}")
                
                except Exception as e:
                    results["errors"] += 1
                    logger.error(f"Error processing public file {file_info.get('name', 'unknown')}: {e}")
        
        except Exception as e:
            results["errors"] += 1
            logger.error(f"Error processing public folder {folder_name}: {e}")
        
        return results
    
    async def _process_private_folder(self, folder_id: str, agent_name: str, agent_type: AgentType, department: str) -> Dict[str, Any]:
        """Process files in a private agent folder"""
        results = {"public_files": 0, "private_files": 0, "errors": 0, "skipped": 0, "details": []}
        
        try:
            # Get user for this agent
            user = await self._get_user_for_agent(agent_name)
            if not user:
                logger.error(f"No user found for agent {agent_name}")
                results["errors"] += 1
                return results
            
            # Get all files in the private folder
            files = await self._get_files_in_folder(folder_id)
            
            # Process each file
            for file_info in files:
                try:
                    # Download and extract content
                    content = await self._extract_file_content(file_info)
                    if not content:
                        results["skipped"] += 1
                        continue
                    
                    # Index into private memory
                    memory_id = f"private_{file_info['name'].replace('.', '_').replace(' ', '_').lower()}_{file_info['id']}"
                    
                    success = self.rbac_service.add_private_memory(
                        user=user,
                        agent_name=agent_name,
                        memory_id=memory_id,
                        content=content,
                        metadata={
                            "filename": file_info['name'],
                            "source": "google_drive", 
                            "folder": f"{agent_name}_private",
                            "file_id": file_info['id'],
                            "agent": agent_name,
                            "department": department,
                            "confidentiality": "private"
                        }
                    )
                    
                    if success:
                        results["private_files"] += 1
                        results["details"].append({
                            "file": file_info['name'],
                            "type": "private",
                            "agent": agent_name,
                            "department": department
                        })
                        logger.info(f"🔒 Indexed private file '{file_info['name']}' for agent {agent_name}")
                    else:
                        results["errors"] += 1
                        logger.error(f"❌ Failed to index private file '{file_info['name']}' for agent {agent_name}")
                
                except Exception as e:
                    results["errors"] += 1
                    logger.error(f"Error processing private file {file_info.get('name', 'unknown')}: {e}")
        
        except Exception as e:
            results["errors"] += 1
            logger.error(f"Error processing private folder for agent {agent_name}: {e}")
        
        return results
    
    async def _get_files_in_folder(self, folder_id: str) -> List[Dict]:
        """Get all files in a folder (excluding subfolders)"""
        try:
            query = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder'"
            response = self.drive_manager.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size, modifiedTime)'
            ).execute()
            
            return response.get('files', [])
            
        except Exception as e:
            logger.error(f"Error getting files in folder {folder_id}: {e}")
            return []
    
    async def _extract_file_content(self, file_info: Dict) -> Optional[str]:
        """Extract text content from a file"""
        try:
            # Download file content
            file_id = file_info['id']
            file_name = file_info['name']
            
            # Use GoogleDriveManager to download
            content = self.drive_manager.download_file_content(file_id)
            if not content:
                logger.warning(f"No content downloaded for file {file_name}")
                return None
            
            # Extract text using FileProcessor
            if isinstance(content, bytes):
                # Save to temp file for processing
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as temp_file:
                    temp_file.write(content)
                    temp_path = temp_file.name
                
                try:
                    text_content = self.file_processor.extract_text(temp_path)
                finally:
                    os.unlink(temp_path)  # Clean up temp file
                
                return text_content
            else:
                # Assume it's already text
                return str(content)
        
        except Exception as e:
            logger.error(f"Error extracting content from file {file_info.get('name', 'unknown')}: {e}")
            return None
    
    def _get_agent_info(self, agent_name: str) -> tuple[Optional[AgentType], Optional[str]]:
        """Get agent type and department for an agent name"""
        # Map agent names to types and departments
        agent_mappings = {
            "bdm": (AgentType.BDM, "business_development"),
            "ipm": (AgentType.IPM, "business_development"),
            "presales_engineer": (AgentType.PRESALES_ENGINEER, "business_development"),
            "content": (AgentType.CONTENT, "marketing"),
            "seo": (AgentType.SEO, "marketing"),
            "analytics": (AgentType.ANALYTICS, "marketing"),
            "cmo": (AgentType.CMO, "executive"),
            "head_of_operations": (AgentType.HEAD_OF_OPERATIONS, "operations"),
            "senior_csm": (AgentType.SENIOR_CSM, "operations"),
            "legal": (AgentType.LEGAL, "operations"),
        }
        
        return agent_mappings.get(agent_name.lower(), (None, None))
    
    async def _get_user_for_agent(self, agent_name: str) -> Optional[User]:
        """Get a user that has access to the specified agent"""
        try:
            # For demo purposes, create a synthetic user with appropriate access
            agent_type, department = self._get_agent_info(agent_name)
            if not agent_type:
                return None
            
            # Create a user with the appropriate agent assignment
            user = User(
                id=f"auto-indexer-{agent_name}",
                username=f"indexer_{agent_name}",
                email=f"indexer+{agent_name}@example.com",
                role=self._get_role_for_agent(agent_type)
            )
            
            # Add agent assignment
            assignment = AgentAssignment(
                agent_type=agent_type,
                access_level='full',
                memory_read_access=[f'public_{department}'],
                memory_write_access=[f'public_{department}'],
                assigned_by='system'
            )
            user.agent_assignments = [assignment]
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating user for agent {agent_name}: {e}")
            return None
    
    def _get_role_for_agent(self, agent_type: AgentType) -> UserRole:
        """Map agent type to appropriate user role"""
        role_mappings = {
            AgentType.BDM: UserRole.BDM_AGENT,
            AgentType.CONTENT: UserRole.CONTENT_AGENT,
            AgentType.CMO: UserRole.EXECUTIVE,
            AgentType.LEGAL: UserRole.OPERATIONS_AGENT,
        }
        
        return role_mappings.get(agent_type, UserRole.EMPLOYEE)

async def run_automatic_indexing(user_id: str) -> Dict[str, Any]:
    """Run automatic file indexing for a user"""
    indexer = AutomaticFileIndexer(user_id)
    return await indexer.scan_and_index_all_files()

if __name__ == "__main__":
    import asyncio
    
    # Example usage
    async def main():
        user_id = "demo-admin-001"  # Replace with actual user ID
        results = await run_automatic_indexing(user_id)
        print("\n" + "="*60)
        print("📊 AUTOMATIC FILE INDEXING RESULTS")
        print("="*60)
        print(f"Public files indexed: {results['public_files_indexed']}")
        print(f"Private files indexed: {results['private_files_indexed']}")
        print(f"Errors: {results['errors']}")
        print(f"Skipped files: {results['skipped_files']}")
        print("="*60)
    
    asyncio.run(main())





