"""
Landing Page Optimization Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class LandingAgent(Agent):
    """
    Landing Page Optimization Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Landing Page Optimization Specialist with expertise in conversion optimization, user experience, and performance marketing. Focus on high-converting landing pages, A/B testing strategies, and conversion rate optimization."""

        super().__init__(
            name="LandingAgent",
            role="Landing Page Optimization Specialist",
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel,
            skills=[
                "conversion optimization",
                "user experience",
                "A/B testing",
                "performance marketing"
            ],
            system_prompt=system_prompt
        )
