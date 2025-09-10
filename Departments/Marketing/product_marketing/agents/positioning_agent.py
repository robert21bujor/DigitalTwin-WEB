"""
Product Positioning Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class PositioningAgent(Agent):
    """
    Product Positioning Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Product Positioning Specialist with expertise in market research, competitive analysis, and strategic positioning frameworks. Focus on market opportunity assessments, competitive analysis, value proposition development, and strategic positioning recommendations."""

        super().__init__(
            name="PositioningAgent",
            role="Product Positioning Specialist",
            agent_type=AgentType.COMPANION,
            kernel=kernel,
            skills=[
                "market research",
                "competitive analysis", 
                "positioning frameworks",
                "value proposition development"
            ],
            system_prompt=system_prompt
        )
 