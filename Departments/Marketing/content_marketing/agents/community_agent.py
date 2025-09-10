"""
Community Management Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class CommunityAgent(Agent):
    """
    Community Management Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Community Management Specialist with expertise in community building, engagement strategies, and relationship management. Focus on community growth, engagement tactics, relationship building, and community health metrics."""

        super().__init__(
            name="CommunityAgent",
            role="Community Management Specialist",
            agent_type=AgentType.COMPANION,
            kernel=kernel,
            skills=[
                "community building",
                "engagement strategies",
                "relationship management",
                "community content"
            ],
            system_prompt=system_prompt
        )
