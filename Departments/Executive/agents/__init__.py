"""
Executive Agents Module

Provides executive-level agents for strategic oversight and decision-making.
"""

from .chief_marketing_officer import ExecutiveAgent

# Export the main agent class with multiple access patterns
__all__ = ["ExecutiveAgent", "ChiefMarketingOfficer", "CMO"]

# Create aliases for different naming conventions
ChiefMarketingOfficer = ExecutiveAgent
CMO = ExecutiveAgent 