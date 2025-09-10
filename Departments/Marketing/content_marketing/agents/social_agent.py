"""
Social Media Marketing Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class SocialAgent(Agent):
    """
    Social Media Marketing Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Social Media Marketing Specialist with expertise in social media strategy, content creation, and community engagement. Focus on platform-specific strategies, engaging content, community management, and social advertising."""

        super().__init__(
            name="SocialAgent",
            role="Social Media Marketing Specialist",
            agent_type=AgentType.COMPANION,
            kernel=kernel,
            skills=[
                "social media strategy",
                "content creation",
                "community engagement",
                "social advertising"
            ],
            system_prompt=system_prompt
        )
