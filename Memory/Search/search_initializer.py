"""
Search System Initializer
Coordinates initialization of unified semantic search with file and email data.
"""

import logging
import asyncio
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SearchSystemInitializer:
    """Initializes unified semantic search system"""
    
    def __init__(self):
        self.initialized = False
        
    async def initialize_unified_search(self) -> bool:
        """Initialize the unified search system with file and email data"""
        try:
            logger.info("🚀 Initializing unified semantic search system...")
            
            # Import services with graceful fallback for ML library issues
            try:
                from Memory.Search.unified_semantic_search import unified_search_service
                from Integrations.Google.Drive.gdrive_search_service import gdrive_search
                logger.info("✅ Successfully imported search services")
            except ImportError as e:
                logger.error(f"❌ Failed to import unified semantic search: {e}")
                logger.info("⚠️ Semantic search will not be available - falling back to basic search")
                return False
            except Exception as e:
                # Handle segfaults and other issues during import
                logger.error(f"❌ Error importing search services (possible ML library issue): {e}")
                logger.info("⚠️ Semantic search will not be available - falling back to basic search")
                return False
            
            # Get file documents
            file_documents = await self._get_file_documents()
            logger.info(f"📄 Loaded {len(file_documents)} file documents")
            
            # Get email documents  
            email_documents = await self._get_email_documents()
            logger.info(f"📧 Loaded {len(email_documents)} email documents")
            
            # Initialize unified search
            success = unified_search_service.initialize(file_documents, email_documents)
            
            if success:
                self.initialized = True
                logger.info(f"🎉 Unified search initialized with {len(file_documents)} files and {len(email_documents)} emails")
            else:
                logger.error("❌ Failed to initialize unified search")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error initializing unified search: {e}")
            return False
    
    async def _get_file_documents(self) -> List[Dict[str, Any]]:
        """Get file documents from Google Drive"""
        try:
            from Integrations.Google.Drive.gdrive_search_service import gdrive_search
            
            if not gdrive_search:
                logger.warning("⚠️ Google Drive search not available")
                return []
            
            # Get all files from Google Drive
            files = gdrive_search.search_files(
                query="",  # Empty query to get all files
                folder_filter=None,
                file_type_filter=None,
                max_results=1000
            )
            
            # Convert to unified format
            file_documents = []
            for file_info in files:
                doc = {
                    "id": file_info.get("id", ""),
                    "file_id": file_info.get("id", ""),
                    "name": file_info.get("name", ""),
                    "full_path": file_info.get("full_path", ""),
                    "folder_path": file_info.get("folder_path", ""),
                    "mime_type": file_info.get("mimeType", ""),
                    "size": file_info.get("size", ""),
                    "modified_time": file_info.get("modifiedTime", ""),
                    "web_view_link": file_info.get("webViewLink", ""),
                    "download_link": file_info.get("downloadLink", ""),
                    "content": file_info.get("content", ""),  # If content extraction is available
                    "user_id": file_info.get("user_id", "")
                }
                file_documents.append(doc)
            
            return file_documents
            
        except Exception as e:
            logger.error(f"❌ Error getting file documents: {e}")
            return []
    
    async def _get_email_documents(self) -> List[Dict[str, Any]]:
        """Get email documents from Gmail/database"""
        try:
            from Integrations.Google.Gmail.gmail_database import GmailDatabaseService
            
            db = GmailDatabaseService()
            
            if not db.supabase_client:
                logger.warning("⚠️ Gmail database not available")
                return []
            
            # Get processed emails from database
            response = db.supabase_client.table('processed_emails').select('*').execute()
            
            if not response.data:
                logger.info("📧 No processed emails found in database")
                return []
            
            # Convert to unified format
            email_documents = []
            for email_record in response.data:
                # Construct file path for the email document
                user_id = email_record.get("user_id", "")
                category = email_record.get("category", "General")
                file_name = email_record.get("document_path", "").split("/")[-1] if email_record.get("document_path") else ""
                
                if not file_name:
                    continue  # Skip if no document path
                
                doc = {
                    "id": email_record.get("message_id", ""),
                    "message_id": email_record.get("message_id", ""),
                    "name": email_record.get("subject", "No Subject"),
                    "path": email_record.get("document_path", ""),
                    "file_path": email_record.get("document_path", ""),
                    "sender": email_record.get("sender_email", ""),
                    "sender_email": email_record.get("sender_email", ""),
                    "subject": email_record.get("subject", ""),
                    "date": email_record.get("timestamp", ""),
                    "timestamp": email_record.get("timestamp", ""),
                    "category": category,
                    "content": "",  # Will be loaded from .docx file if needed
                    "body": "",
                    "user_id": user_id,
                    "web_view_link": f"https://drive.google.com/file/d/{email_record.get('message_id', '')}/view",
                    "download_link": f"https://drive.google.com/file/d/{email_record.get('message_id', '')}/download"
                }
                email_documents.append(doc)
            
            return email_documents
            
        except Exception as e:
            logger.error(f"❌ Error getting email documents: {e}")
            return []
    
    def is_initialized(self) -> bool:
        """Check if search system is initialized"""
        return self.initialized

# Global instance
search_initializer = SearchSystemInitializer()

async def initialize_search_system() -> bool:
    """Initialize the search system"""
    return await search_initializer.initialize_unified_search()

def is_search_system_ready() -> bool:
    """Check if search system is ready"""
    return search_initializer.is_initialized()

# Export the function for import in other modules
__all__ = ['initialize_search_system', 'is_search_system_ready', 'search_initializer']