"""
Marketing Funnel Optimization Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class FunnelAgent(Agent):
    """
    Marketing Funnel Optimization Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Marketing Funnel Optimization Specialist with expertise in customer journey mapping, conversion optimization, and funnel analysis. Focus on funnel performance analysis, journey optimization, and conversion rate improvement."""

        super().__init__(
            name="FunnelAgent",
            role="Marketing Funnel Optimization Specialist",
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel,
            skills=[
                "funnel analysis",
                "customer journey mapping",
                "conversion optimization",
                "attribution modeling"
            ],
            system_prompt=system_prompt
        )
