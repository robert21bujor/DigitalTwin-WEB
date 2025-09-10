"""
Product Launch Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class LaunchAgent(Agent):
    """
    Product Launch Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Product Launch Specialist with expertise in launch strategy, campaign execution, and market introduction. Focus on comprehensive launch plans, campaign strategies, stakeholder communication, and success metrics."""

        super().__init__(
            name="LaunchAgent",
            role="Product Launch Specialist",
            agent_type=AgentType.COMPANION,
            kernel=kernel,
            skills=[
                "launch strategy",
                "campaign execution",
                "market introduction",
                "cross-functional coordination"
            ],
            system_prompt=system_prompt
        )
