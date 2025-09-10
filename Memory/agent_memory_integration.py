"""
Integration layer to connect existing agents with the dual memory RBAC system
"""

import sys
import os
import logging
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Memory.unified_rbac_service import get_unified_rbac_service
from Memory.dual_memory_rbac import AccessType
from Auth.User_management.user_models import User, UserRole, AgentType, AgentAssignment

logger = logging.getLogger(__name__)

class AgentMemoryBridge:
    """
    Bridge between existing agent infrastructure and dual memory RBAC system
    Allows agents to access indexed file information with proper access controls
    """
    
    def __init__(self):
        self.rbac_service = get_unified_rbac_service()
        self._user_cache = {}
    
    def search_agent_knowledge(
        self, 
        agent_name: str, 
        user_id: str, 
        query: str, 
        include_private: bool = True,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search both public and private knowledge for an agent
        
        Args:
            agent_name: Name of the agent (e.g., 'bdm', 'content', 'cmo')
            user_id: ID of the user making the request
            query: Search query
            include_private: Whether to include private memories
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with public and private search results
        """
        results = {
            "public_results": [],
            "private_results": [],
            "total_results": 0,
            "agent": agent_name,
            "query": query,
            "access_summary": {
                "public_access": False,
                "private_access": False,
                "department": None
            }
        }
        
        try:
            # Get or create user for this request
            user = self._get_user_for_agent_request(agent_name, user_id)
            if not user:
                logger.warning(f"Could not create user for agent {agent_name} request")
                return results
            
            # Search public memory
            try:
                public_results = self.rbac_service.search_public_memory(
                    user=user,
                    agent_name=agent_name,
                    query=query,
                    limit=max_results
                )
                results["public_results"] = public_results
                results["access_summary"]["public_access"] = True
                
                # Get department info
                department = self.rbac_service.memory_manager.get_agent_department(agent_name)
                results["access_summary"]["department"] = department
                
                logger.info(f"Found {len(public_results)} public results for agent {agent_name}")
                
            except Exception as e:
                logger.warning(f"Public memory search failed for {agent_name}: {e}")
            
            # Search private memory if requested
            if include_private:
                try:
                    private_results = self.rbac_service.search_private_memory(
                        user=user,
                        agent_name=agent_name,
                        query=query,
                        limit=max_results
                    )
                    results["private_results"] = private_results
                    results["access_summary"]["private_access"] = True
                    
                    logger.info(f"Found {len(private_results)} private results for agent {agent_name}")
                    
                except Exception as e:
                    logger.warning(f"Private memory search failed for {agent_name}: {e}")
            
            results["total_results"] = len(results["public_results"]) + len(results["private_results"])
            
        except Exception as e:
            logger.error(f"Error in agent knowledge search for {agent_name}: {e}")
        
        return results
    
    def get_agent_file_summary(self, agent_name: str, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of what files/information an agent has access to
        
        Args:
            agent_name: Name of the agent
            user_id: ID of the user making the request
            
        Returns:
            Summary of available information
        """
        summary = {
            "agent": agent_name,
            "department": None,
            "public_collections": [],
            "private_collections": [],
            "total_documents": 0,
            "access_level": "none"
        }
        
        try:
            user = self._get_user_for_agent_request(agent_name, user_id)
            if not user:
                return summary
            
            # Get department info
            department = self.rbac_service.memory_manager.get_agent_department(agent_name)
            summary["department"] = department
            
            # Check public access
            if department:
                public_collection = self.rbac_service.memory_manager.get_public_collection_name(department)
                if self.rbac_service.memory_manager.validate_memory_access(
                    user, public_collection, AccessType.READ
                ):
                    summary["public_collections"].append(public_collection)
                    summary["access_level"] = "public"
            
            # Check private access
            private_collection = self.rbac_service.memory_manager.get_private_collection_name(agent_name)
            if self.rbac_service.memory_manager.validate_memory_access(
                user, private_collection, AccessType.READ
            ):
                summary["private_collections"].append(private_collection)
                summary["access_level"] = "full"
            
            # Get document counts (this would require additional Qdrant queries)
            # For now, just indicate if collections exist
            summary["total_documents"] = len(summary["public_collections"]) + len(summary["private_collections"])
            
        except Exception as e:
            logger.error(f"Error getting file summary for agent {agent_name}: {e}")
        
        return summary
    
    def format_search_results_for_agent(self, results: Dict[str, Any]) -> str:
        """
        Format search results into a natural language response for the agent
        
        Args:
            results: Results from search_agent_knowledge
            
        Returns:
            Formatted string for agent to use in response
        """
        if results["total_results"] == 0:
            return f"I don't have any specific information about '{results['query']}' in my knowledge base. You may want to add relevant files to the appropriate Google Drive folders and run the indexer."
        
        response_parts = []
        
        # Add public information
        if results["public_results"]:
            response_parts.append(f"Based on our department's shared knowledge, I found {len(results['public_results'])} relevant documents:")
            
            for i, result in enumerate(results["public_results"][:3], 1):  # Show top 3
                filename = result.get('metadata', {}).get('filename', 'Document')
                content_preview = result.get('text', '')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', '')
                confidence = result.get('score', 0.0)
                
                response_parts.append(f"\n{i}. 📄 **{filename}** (relevance: {confidence:.1f})")
                response_parts.append(f"   {content_preview}")
        
        # Add private information
        if results["private_results"]:
            response_parts.append(f"\n\nFrom my private knowledge base, I also found {len(results['private_results'])} confidential documents:")
            
            for i, result in enumerate(results["private_results"][:2], 1):  # Show top 2
                filename = result.get('metadata', {}).get('filename', 'Confidential Document')
                content_preview = result.get('text', '')[:150] + "..." if len(result.get('text', '')) > 150 else result.get('text', '')
                confidence = result.get('score', 0.0)
                
                response_parts.append(f"\n{i}. 🔒 **{filename}** (relevance: {confidence:.1f})")
                response_parts.append(f"   {content_preview}")
        
        # Add summary
        total_public = len(results["public_results"])
        total_private = len(results["private_results"])
        
        if total_public > 3 or total_private > 2:
            response_parts.append(f"\n\n📊 **Summary**: Found {total_public} public and {total_private} private documents. Showing most relevant results above.")
        
        return "\n".join(response_parts)
    
    def _get_user_for_agent_request(self, agent_name: str, user_id: str) -> Optional[User]:
        """
        Get or create a user object for an agent request
        
        Args:
            agent_name: Name of the agent making the request
            user_id: ID of the user
            
        Returns:
            User object with appropriate permissions
        """
        cache_key = f"{agent_name}_{user_id}"
        
        if cache_key in self._user_cache:
            return self._user_cache[cache_key]
        
        try:
            # Map agent names to types and roles
            agent_mappings = {
                "bdm": (AgentType.BDM, UserRole.BDM_AGENT, "business_development"),
                "ipm": (AgentType.IPM, UserRole.IPM_AGENT, "business_development"),
                "presales_engineer": (AgentType.PRESALES_ENGINEER, UserRole.PRESALES_ENGINEER_AGENT, "business_development"),
                "content": (AgentType.CONTENT, UserRole.CONTENT_AGENT, "marketing"),
                "seo": (AgentType.SEO, UserRole.SEO_AGENT, "marketing"),
                "analytics": (AgentType.ANALYTICS, UserRole.ANALYTICS_AGENT, "marketing"),
                "cmo": (AgentType.CMO, UserRole.CMO, "executive"),
                "head_of_operations": (AgentType.HEAD_OF_OPERATIONS, UserRole.HEAD_OF_OPERATIONS_AGENT, "operations"),
                "senior_csm": (AgentType.SENIOR_CSM, UserRole.SENIOR_CSM_AGENT, "operations"),
                "legal": (AgentType.LEGAL, UserRole.LEGAL_AGENT, "operations"),
            }
            
            agent_info = agent_mappings.get(agent_name.lower())
            if not agent_info:
                logger.warning(f"Unknown agent name: {agent_name}")
                return None
            
            agent_type, user_role, department = agent_info
            
            # Create user object
            user = User(
                id=user_id,
                username=f"agent_{agent_name}_{user_id}",
                email=f"agent+{agent_name}+{user_id}@system.local",
                role=user_role
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
            
            # Cache the user
            self._user_cache[cache_key] = user
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating user for agent {agent_name}: {e}")
            return None

# Global instance for easy access
_agent_memory_bridge = None

def get_agent_memory_bridge() -> AgentMemoryBridge:
    """Get the global agent memory bridge instance"""
    global _agent_memory_bridge
    if _agent_memory_bridge is None:
        _agent_memory_bridge = AgentMemoryBridge()
    return _agent_memory_bridge

# Convenience functions for agent integration
def search_agent_files(agent_name: str, user_id: str, query: str, max_results: int = 5) -> str:
    """
    Search files for an agent and return formatted response
    
    Args:
        agent_name: Name of the agent (e.g., 'bdm', 'content')
        user_id: User ID making the request
        query: What to search for
        max_results: Maximum results to return
        
    Returns:
        Formatted string response for the agent
    """
    bridge = get_agent_memory_bridge()
    results = bridge.search_agent_knowledge(agent_name, user_id, query, max_results=max_results)
    return bridge.format_search_results_for_agent(results)

def get_agent_capabilities(agent_name: str, user_id: str) -> str:
    """
    Get a summary of what files/capabilities an agent has
    
    Args:
        agent_name: Name of the agent
        user_id: User ID making the request
        
    Returns:
        Formatted string describing agent capabilities
    """
    bridge = get_agent_memory_bridge()
    summary = bridge.get_agent_file_summary(agent_name, user_id)
    
    if summary["access_level"] == "none":
        return f"I don't currently have access to any indexed files. To give me access to information, please add files to the appropriate Google Drive folders and run the indexer."
    
    capabilities = []
    capabilities.append(f"I have access to information from our {summary['department']} department.")
    
    if summary["public_collections"]:
        capabilities.append("I can access our shared department knowledge base.")
    
    if summary["private_collections"]:
        capabilities.append("I also have access to my private knowledge base with confidential information.")
    
    capabilities.append(f"I can search through {summary['total_documents']} knowledge collections to help answer your questions.")
    
    return " ".join(capabilities)
