"""
AgentUI Backend
===============

Python backend components for the Agent UI system.

This module contains:
- api.py: FastAPI backend server
- communication_manager.py: Agent communication management  
- user_agent_mapping.py: User-agent mapping logic
"""

# Import key components for easier access
try:
    from .api import app
    from .communication_manager import agent_manager
    from .user_agent_mapping import user_agent_matcher
except ImportError:
    # Graceful fallback during module loading
    pass
