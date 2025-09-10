"""
Search Engine Marketing Specialist Agent - extends agent template
"""

import semantic_kernel as sk
from Core.Agents.agent import Agent, AgentType


class SEMAgent(Agent):
    """
    Search Engine Marketing Specialist - extends the agent template
    """
    
    def __init__(self, kernel: sk.Kernel):
        system_prompt = """You are a Search Engine Marketing (SEM) Specialist with expertise in paid search advertising, PPC campaigns, and search marketing strategy. Focus on campaign optimization, keyword research, ad copy creation, and ROI maximization."""

        super().__init__(
            name="SEMAgent",
            role="Search Engine Marketing Specialist",
            agent_type=AgentType.AUTONOMOUS,
            kernel=kernel,
            skills=[
                "paid search",
                "PPC campaigns",
                "keyword bidding",
                "ad optimization"
            ],
            system_prompt=system_prompt
        )
