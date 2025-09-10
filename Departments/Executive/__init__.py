"""
Executive Leadership Department
Comprehensive executive capabilities with strategic oversight and approval authority
"""

from .executive_department import ExecutiveAgents  
from .agents import ExecutiveAgent

# Main exports
__all__ = [
    'ExecutiveAgents',      # Department manager (main department class)
    'ExecutiveAgent',       # Main executive agent
]
