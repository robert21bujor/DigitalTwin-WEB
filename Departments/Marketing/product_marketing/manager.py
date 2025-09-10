"""
Product Marketing Manager
"""

import semantic_kernel as sk
from Core.Agents.manager import Manager
from Core.Agents.agent import Agent
from typing import List


class ProductMarketingManager(Manager):
    """
    Manager for Product Marketing Division
    """
    
    def __init__(self, kernel: sk.Kernel, team_members: List[Agent] = None):
        super().__init__(
            name="ProductMarketingManager",
            role="Product Marketing Manager",
            kernel=kernel,
            team_members=team_members or []
        ) 