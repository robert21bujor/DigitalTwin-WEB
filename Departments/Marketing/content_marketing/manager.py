"""
Content Marketing Manager
"""

import semantic_kernel as sk
from Core.Agents.manager import Manager
from .agents.content_agent import ContentAgent
from .agents.brand_agent import BrandAgent
from .agents.social_agent import SocialAgent
from .agents.community_agent import CommunityAgent


class ContentMarketingManager(Manager):
    """
    Content/Brand Marketing Manager
    Manages the content and brand marketing team
    """
    
    def __init__(self, kernel: sk.Kernel):
        # Initialize team members
        team_members = [
            ContentAgent(kernel),
            BrandAgent(kernel),
            SocialAgent(kernel),
            CommunityAgent(kernel)
        ]
        
        super().__init__(
            name="ContentMarketingManager",
            role="Content/Brand Marketing Manager",
            kernel=kernel,
            team_members=team_members
        ) 