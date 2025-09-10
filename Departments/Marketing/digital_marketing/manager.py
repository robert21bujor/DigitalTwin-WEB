"""
Digital Marketing Manager
"""

import semantic_kernel as sk
from Core.Agents.manager import Manager
from .agents.seo_agent import SEOAgent
from .agents.sem_agent import SEMAgent
from .agents.landing_agent import LandingAgent
from .agents.analytics_agent import AnalyticsAgent
from .agents.funnel_agent import FunnelAgent


class DigitalMarketingManager(Manager):
    """
    Digital Marketing Manager
    Manages the digital marketing team
    """
    
    def __init__(self, kernel: sk.Kernel):
        # Initialize team members
        team_members = [
            SEOAgent(kernel),
            SEMAgent(kernel),
            LandingAgent(kernel),
            AnalyticsAgent(kernel),
            FunnelAgent(kernel)
        ]
        
        super().__init__(
            name="DigitalMarketingManager",
            role="Digital Marketing Manager",
            kernel=kernel,
            team_members=team_members
        ) 