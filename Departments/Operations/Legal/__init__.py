"""
Legal Department
===============

Legal compliance and contract management services including:
- Contract drafting and review
- Regulatory compliance monitoring
- Risk assessment and mitigation
- Intellectual property protection
- Dispute resolution and negotiation
- Legal documentation and governance

Focus: Ensure legal compliance and protect organizational interests through expert legal guidance.
"""

from .manager import LegalManager
from .Agents import (
    LegalAgent
)

__all__ = [
    'LegalManager',
    'LegalAgent'
] 