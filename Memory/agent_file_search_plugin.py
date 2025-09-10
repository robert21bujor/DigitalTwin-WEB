"""
Semantic Kernel Plugin for Agent File Search
Allows agents to search through indexed Google Drive files with proper RBAC
"""

import sys
import os
from typing import Annotated

# Add parent directory to path for imports  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from semantic_kernel.functions import kernel_function
from Memory.agent_memory_integration import search_agent_files, get_agent_capabilities

class AgentFileSearchPlugin:
    """
    Semantic Kernel plugin that allows agents to search indexed files
    """
    
    @kernel_function(
        description="Search through indexed files and documents for information relevant to a query",
        name="search_files"
    )
    def search_files(
        self,
        query: Annotated[str, "What to search for in the files"],
        agent_name: Annotated[str, "Name of the agent making the request (e.g., 'bdm', 'content', 'cmo')"] = "general",
        user_id: Annotated[str, "ID of the user making the request"] = "system",
        max_results: Annotated[int, "Maximum number of results to return"] = 5
    ) -> str:
        """
        Search through indexed Google Drive files for relevant information
        
        Args:
            query: What to search for
            agent_name: Name of the agent (determines access permissions)
            user_id: User ID for authentication
            max_results: Maximum results to return
            
        Returns:
            Formatted search results with file content
        """
        try:
            return search_agent_files(agent_name, user_id, query, max_results)
        except Exception as e:
            return f"I encountered an error while searching files: {e}. Please make sure files are indexed and accessible."
    
    @kernel_function(
        description="Get information about what files and knowledge the agent has access to",
        name="get_capabilities"
    )
    def get_capabilities(
        self,
        agent_name: Annotated[str, "Name of the agent"] = "general",
        user_id: Annotated[str, "ID of the user"] = "system"
    ) -> str:
        """
        Get a summary of what files and knowledge the agent can access
        
        Args:
            agent_name: Name of the agent
            user_id: User ID for authentication
            
        Returns:
            Description of agent's file access capabilities
        """
        try:
            return get_agent_capabilities(agent_name, user_id)
        except Exception as e:
            return f"I couldn't determine my file access capabilities: {e}"
    
    @kernel_function(
        description="Search for specific todo tasks, project information, or action items in files",
        name="search_todos"
    )
    def search_todos(
        self,
        query: Annotated[str, "What specific todos, tasks, or projects to search for"] = "todo tasks projects",
        agent_name: Annotated[str, "Name of the agent making the request"] = "general",
        user_id: Annotated[str, "ID of the user making the request"] = "system"
    ) -> str:
        """
        Search specifically for todo items, tasks, projects, and action items
        
        Args:
            query: Specific search terms for tasks/todos
            agent_name: Name of the agent
            user_id: User ID for authentication
            
        Returns:
            Formatted list of found todos and tasks
        """
        try:
            # Enhance query to focus on task-related content
            enhanced_query = f"todo tasks projects action items deliverables assignments {query}"
            results = search_agent_files(agent_name, user_id, enhanced_query, max_results=10)
            
            if "I don't have any specific information" in results:
                return "I don't have any specific todo tasks or project information in my indexed files. You may want to add project documents, task lists, or planning files to the appropriate Google Drive folders."
            
            return f"📋 **Todo Tasks and Projects Found:**\n\n{results}"
            
        except Exception as e:
            return f"I couldn't search for todo tasks: {e}"





