"""
Marketing Analytics Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class AnalyticsAgent(Agent):
    """
    Marketing Analytics Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Marketing Analytics Specialist with expertise in data analysis, performance measurement, and marketing intelligence. Focus on comprehensive analytics strategies, data-driven insights, performance reporting, and optimization recommendations."""

        super().__init__(
            name="AnalyticsAgent",
            role="Marketing Analytics Specialist",
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel,
            skills=[
                "data analysis",
                "performance measurement",
                "reporting",
                "marketing intelligence"
            ],
            system_prompt=system_prompt
        )
