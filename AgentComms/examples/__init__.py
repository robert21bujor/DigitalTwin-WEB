"""
Universal Communication Examples
===============================

Universal, modular communication infrastructure that works with ANY agent type.
No predefined roles - completely extensible for any organization.
"""

from .config import AgentConfig, create_agent_config

# Universal interfaces (recommended)
from .universal_dashboard import UniversalDashboard
from .universal_agent_mixin import UniversalAgentMixin, UniversalAgentExample, create_agent_with_communication

# Legacy interfaces (deprecated - use Universal versions)
from .dashboard_interface import DashboardInterface
from .agent_integration import AgentCommunicationMixin
from .digital_twin_demo import DigitalTwinCommunicationDemo, ExistingAgentExample

__all__ = [
    # Configuration
    "AgentConfig",
    "create_agent_config",
    
    # Universal interfaces (recommended)
    "UniversalDashboard",
    "UniversalAgentMixin", 
    "UniversalAgentExample",
    "create_agent_with_communication",
    
    # Legacy interfaces (deprecated)
    "DashboardInterface",
    "AgentCommunicationMixin",
    "DigitalTwinCommunicationDemo",
    "ExistingAgentExample"
] 