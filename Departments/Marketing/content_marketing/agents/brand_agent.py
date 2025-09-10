"""
Brand Strategy Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class BrandAgent(Agent):
    """
    Brand Strategy Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Brand Strategy Specialist with expertise in brand development, visual identity, and brand management. Focus on brand positioning, identity systems, messaging strategies, and brand consistency."""

        super().__init__(
            name="BrandAgent",
            role="Brand Strategy Specialist",
            agent_type=AgentType.COMPANION,
            kernel=kernel,
            skills=[
                "brand development",
                "visual identity",
                "brand management",
                "messaging strategy"
            ],
            system_prompt=system_prompt
        )
