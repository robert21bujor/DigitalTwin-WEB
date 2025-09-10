"""
Google Drive Search Skill for Semantic Kernel Agents
Allows agents to search and find files in Google Drive using hybrid search system
PRODUCTION READY - Hybrid search system only
"""

import logging
import os
from typing import Optional, List
import sys
from pathlib import Path

# Add Memory module to path
memory_path = str(Path(__file__).parent.parent.parent / "Memory")
if memory_path not in sys.path:
    sys.path.append(memory_path)

from semantic_kernel import Kernel
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.functions.kernel_function_metadata import KernelFunctionMetadata

# Type imports for IDE support
from typing import Any, TYPE_CHECKING

# Import hybrid search system
hybrid_search_adapter = None

# PRODUCTION MODE - Hybrid search system only
print("🚀 INITIALIZING HYBRID SEARCH SYSTEM")

try:
    # Add project root to path for proper imports
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    # Import hybrid search system
    from Integrations.Google.Search.adapters import get_search_adapter
    hybrid_search_adapter = get_search_adapter()
    print("✅ HYBRID SEARCH AVAILABLE")
    logging.getLogger(__name__).info("✅ Hybrid search system imported successfully")
            
except Exception as e:
    print(f"❌ HYBRID SEARCH FAILED TO LOAD: {e}")
    logging.getLogger(__name__).error(f"Failed to load hybrid search system: {e}")
    import traceback
    logging.getLogger(__name__).error(traceback.format_exc())
    hybrid_search_adapter = None

logger = logging.getLogger(__name__)


class GoogleDriveSearchSkill:
    """Skill for searching Google Drive files"""
    
    def _get_username_from_user_id(self, user_id: str) -> str:
        """
        Get the actual username from Gmail tokens for a user_id
        """
        try:
            # Import Gmail database to get user info
            from Integrations.Google.Gmail.gmail_database import gmail_database
            
            # Try to get user's Gmail tokens/info to extract username
            gmail_tokens = gmail_database.get_gmail_tokens(user_id)
            if gmail_tokens and 'gmail_email' in gmail_tokens:
                email = gmail_tokens['gmail_email']
                # Extract username from email (before @)
                username = email.split('@')[0] if '@' in email else email
                logger.info(f"Extracted username '{username}' from user_id '{user_id}'")
                return username
            else:
                logger.warning(f"No Gmail tokens found for user_id '{user_id}', using user_id as username")
            return user_id
        except Exception as e:
            logger.error(f"Error extracting username for {user_id}: {e}")
            return user_id
    
    def get_user_department_folder(self, username: str, agent_name: str = None) -> str:
        """Get the appropriate department folder for a user based on agent name"""
        
        # Agent to department mapping (customize based on your setup)
        agent_department_mapping = {
            "chief_marketing_officer": "DigitalTwin_Brain/Executive",
            "digital_marketing_manager": "DigitalTwin_Brain/Digital Marketing",
            "product_marketing_manager": "DigitalTwin_Brain/Product Marketing",
            "content_brand_manager": "DigitalTwin_Brain/Content & Brand",
            "business_dev_manager": "DigitalTwin_Brain/Business Development",
            "operations_manager": "DigitalTwin_Brain/Operations",
            "client_success_manager": "DigitalTwin_Brain/Operations",
            "delivery_consultant": "DigitalTwin_Brain/Operations",
            "legal_specialist": "DigitalTwin_Brain/Operations", 
            "reporting_manager": "DigitalTwin_Brain/Operations",
            "reporting_specialist": "DigitalTwin_Brain/Operations"
        }
        
        return agent_department_mapping.get(agent_name)

    @kernel_function(
        name="search_files", 
        description="Search for files and emails using advanced semantic understanding. Automatically detects email vs file queries."
    )
    def search_files(self, query: str, folder: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """
        Search for files in Google Drive using hybrid search system
        
        Args:
            query: Search terms (file name, keywords, etc.)
            folder: Optional folder to search in (e.g. "Executive", "Marketing", "Product Marketing")
            file_type: Optional file type filter (e.g. "pdf", "doc", "excel", "google")
            
        Returns:
            Formatted string with file results including links and locations
        """
        try:
            # Use hybrid search system
            if hybrid_search_adapter:
                logger.info(f"🚀 Using HYBRID SEARCH for query: '{query}'")
                return self._search_with_hybrid_system(query, folder, file_type)
            else:
                return f"🔍 **Google Drive Search Status**: Hybrid search system not available.\n\nI cannot search for '{query}' because the hybrid search system failed to load. This could be due to import errors or missing configuration.\n\n💡 **Quick Fix**: Check the system configuration and ensure all dependencies are properly installed."
            
        except Exception as e:
            # SAFE FALLBACK: Never let this crash the entire system
            error_msg = f"🔍 **File Search Error**: {str(e)}\n\n"
            error_msg += "The file search system encountered an unexpected error. "
            error_msg += "Please try a different request or contact support if this persists."
            return error_msg
    
    @kernel_function(
        name="list_folders",
        description="List all available folders in Google Drive"
    )
    def list_folders(self) -> str:
        """List all available folders in Google Drive"""
        try:
            # Use hybrid search to get folder information
            if hybrid_search_adapter:
                return "📁 **Available Google Drive Folders:**\n\n1. 📁 Executive\n2. 📁 Digital Marketing\n3. 📁 Product Marketing\n4. 📁 Content & Brand\n5. 📁 Business Development\n6. 📁 Operations\n7. 📁 User Folders\n\n💡 You can search within any of these folders by mentioning the folder name in your request."
            else:
                return "Google Drive search is not available. Please check system configuration."
            
        except Exception as e:
            error_msg = f"🔍 **File Search Error**: {str(e)}\n\n"
            error_msg += "The file search system encountered an unexpected error. "
            error_msg += "Please try a different request or contact support if this persists."
            return error_msg
    
    @kernel_function(
        name="search_recent_files",
        description="Search for recently modified files in Google Drive"
    )
    def search_recent_files(self, days: str = "7") -> str:
        """Search for files modified in the last N days"""
        try:
            if hybrid_search_adapter:
                # Use hybrid search with date filter
                days_int = int(days)
                recent_query = f"modified in last {days_int} days"
                return self._search_with_hybrid_system(recent_query, None, None)
            else:
                return "Google Drive search is not available. Please check system configuration."
            
        except Exception as e:
            logger.error(f"Error searching recent files: {e}")
            return f"Error searching recent files: {str(e)}"
    
    @kernel_function(
        name="search_by_folder",
        description="Search for files within a specific folder"
    )
    def search_by_folder(self, folder_name: str) -> str:
        """Search for files within a specific folder"""
        try:
            if hybrid_search_adapter:
                # Use hybrid search with folder filter
                return self._search_with_hybrid_system("", folder_name, None)
            else:
                return "Google Drive search is not available. Please check system configuration."
            
        except Exception as e:
            logger.error(f"Error searching folder {folder_name}: {e}")
            return f"Error searching folder {folder_name}: {str(e)}"
    
    def _search_with_hybrid_system(self, query: str, folder: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """
        Search using the new hybrid search system with bilingual support
        """
        try:
            # Get current user context
            user_id = getattr(self, '_current_user_id', None)
            agent_name = getattr(self, '_current_agent_name', None)
            
            logger.info(f"🔍 HYBRID SEARCH: query='{query}', folder='{folder}', file_type='{file_type}', user_id='{user_id}'")
            
            # Build enhanced query with file type if specified
            enhanced_query = query
            if file_type:
                # Map common file types to Romanian-aware query enhancement
                type_mappings = {
                    'pdf': 'tip:pdf',
                    'doc': 'tip:docx',
                    'docx': 'tip:docx', 
                    'excel': 'tip:xlsx',
                    'xlsx': 'tip:xlsx',
                    'ppt': 'tip:pptx',
                    'pptx': 'tip:pptx'
                }
                type_query = type_mappings.get(file_type.lower(), f'tip:{file_type}')
                enhanced_query = f"{query} {type_query}" if query else type_query
                logger.info(f"🔍 Enhanced query with file type: '{enhanced_query}'")
            
            # Use hybrid search adapter
            results = hybrid_search_adapter.unified_search(
                query=enhanced_query,
                max_results=10,
                user_id=user_id,
                include_emails=True,  # Include both emails and files
                include_files=True
            )
            
            if not results.get("success", False):
                error_msg = results.get("error", "Unknown error")
                logger.error(f"❌ Hybrid search failed: {error_msg}")
                return f"🔍 **Search Error**: {error_msg}\n\nThere was an issue with the search system. Please try again or contact support if the problem persists."
            
            search_results = results.get("results", [])
            total_results = len(search_results)
            
            if total_results == 0:
                return f"🔍 **Google Drive Search Results for: '{query}'**\n\nNo files found matching your search criteria.\n\n💡 **Search Tips:**\n• Try different keywords\n• Check spelling\n• Use broader terms\n• Try bilingual search: Romanian + English operators"
            
            # Separate email and file results
            email_results = [r for r in search_results if r.get("source") == "gmail"]
            file_results = [r for r in search_results if r.get("source") == "drive"]
            
            # Format response
            response_parts = []
            
            # Header with bilingual support detection
            is_bilingual = results.get("query_interpretation", {}).get("language") == "ro"
            header = f"🔍 **Hybrid Search Results for: '{query}'**"
            if is_bilingual:
                header += " (Romanian query detected)"
            response_parts.append(header)
            
            # Add query interpretation info
            interpretation = results.get("query_interpretation", {})
            if interpretation.get("operators"):
                response_parts.append(f"**Operators detected**: {', '.join(interpretation['operators'].keys())}")
            
            # Email results section
            if email_results:
                response_parts.append(f"\n📧 **Email Results ({len(email_results)}):**")
                for i, email in enumerate(email_results[:5], 1):
                    response_parts.append(
                        f"{i}. **{email.get('subject', '(No Subject)')}**\n"
                        f"   From: {email.get('sender', 'Unknown')}\n"
                        f"   Date: {email.get('date', 'Unknown')}\n"
                        f"   Preview: {email.get('snippet', '')[:100]}...\n"
                        f"   📧 [Open Email]({email.get('url', '#')})\n"
                    )
            
            # File results section  
            if file_results:
                response_parts.append(f"\n📁 **File Results ({len(file_results)}):**")
                for i, file in enumerate(file_results[:5], 1):
                    response_parts.append(
                        f"{i}. **{file.get('name', 'Unknown File')}**\n"
                        f"   Type: {file.get('file_type', 'Unknown')}\n"
                        f"   Location: {file.get('folder_path', 'Unknown')}\n"
                        f"   Modified: {file.get('modified_time', 'Unknown')}\n"
                        f"   🔗 [View File]({file.get('web_view_link', '#')})\n"
                    )
            
            # Performance info
            perf = results.get("performance", {})
            if perf.get("duration_seconds"):
                response_parts.append(f"\n⚡ Search completed in {perf['duration_seconds']:.2f}s")
            
            # Bilingual tips
            if total_results > 0:
                response_parts.append(
                    "\n💡 **Bilingual Search Tips:**\n"
                    "• Romanian: găsește de la:nume subiect:\"text\" tip:pdf\n" 
                    "• English: find from:name subject:\"text\" type:pdf\n"
                    "• Mixed: search nume:contract tip:docx"
                )
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"❌ Hybrid search error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"🔍 **Search Error**: {str(e)}\n\nThere was an unexpected error with the hybrid search system. Please try a different search or contact support if this persists."
    
    @kernel_function(
        description="Search for context from colleagues' emails (privacy-protected)",
        name="search_colleague_context"
    )
    def search_colleague_context(self, query: str, context: KernelFunctionMetadata = None) -> str:
        """
        Search through colleagues' emails for relevant context while protecting privacy.
        Only returns anonymized context - no full email content or sensitive information.
        
        Args:
            query (str): Search query for context (e.g., "emails about Hoang", "project updates")
            
        Returns:
            str: Anonymized context results from colleagues' emails
        """
        try:
            # Get user ID from context
            user_id = self._get_user_id_from_context(context)
            if not user_id:
                return "❌ User authentication required for colleague context search"
            
            logger.info(f"🔍 Colleague context search: '{query}' for user {user_id}")
            
            # Import colleague context search
            from Integrations.Google.Search.context_search import search_colleague_context_api
            
            # Search colleague context
            result = search_colleague_context_api(
                query=query,
                requesting_user_id=user_id,
                max_results=10
            )
            
            if not result.get('success'):
                return f"❌ Colleague context search failed: {result.get('error', 'Unknown error')}"
            
            colleague_context = result.get('colleague_context', [])
            
            if not colleague_context:
                return f"🔍 **Colleague Context Search for: '{query}'**\n\nNo relevant context found from colleagues' emails.\n\n💡 **Possible reasons:**\n• No colleagues have granted access\n• No matching content in accessible emails\n• Try different search terms\n\n🔒 **Privacy Note:** All content is anonymized and sensitive information is automatically removed."
            
            # Format results for user display
            formatted_results = f"🔍 **Colleague Context for: '{query}'**\n\n"
            formatted_results += f"Found {len(colleague_context)} relevant context items:\n\n"
            
            for i, context_item in enumerate(colleague_context, 1):
                colleague_name = context_item.get('colleague_name', 'Colleague')
                message_type = context_item.get('message_type', 'general')
                timestamp = context_item.get('timestamp', '')
                relevant_context = context_item.get('relevant_context', '')
                subject_keywords = context_item.get('subject_keywords', [])
                
                formatted_results += f"**{i}. Context from {colleague_name}** ({message_type})\n"
                if timestamp:
                    formatted_results += f"   📅 {timestamp}\n"
                if subject_keywords:
                    formatted_results += f"   🏷️ Topics: {', '.join(subject_keywords[:3])}\n"
                if relevant_context:
                    formatted_results += f"   💬 Context: {relevant_context}\n"
                formatted_results += "\n"
            
            formatted_results += "\n🔒 **Privacy Notice:** All content has been anonymized and sensitive information removed."
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error in search_colleague_context: {e}")
            return f"❌ Colleague context search error: {str(e)}"


def get_google_drive_search_skill():
    """Get the Google Drive search skill instance"""
    return GoogleDriveSearchSkill() 
