"""
Custom Reporting Department
===========================

Business intelligence and custom reporting services including:
- Strategic reporting and business intelligence management
- Custom dashboard and report development
- Data visualization and analytics
- Performance metrics and KPI tracking
- Automated reporting solutions

Focus: Deliver actionable insights through expert reporting and analytics.
"""

from .manager import CustomReportingManager
from .Agents import (
    ReportingManagerAgent,
    ReportingSpecialistAgent
)

__all__ = [
    'CustomReportingManager',
    'ReportingManagerAgent',
    'ReportingSpecialistAgent'
] 