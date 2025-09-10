"""
Task orchestrator for intelligent routing and analysis
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import re

import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
try:
    from Core.Agents.agent import Agent
    from Core.Tasks.task import Task, TaskPriority
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Core.Agents.agent import Agent
    from Core.Tasks.task import Task, TaskPriority

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Intelligent task orchestrator with clean interface
    """
    
    def __init__(self, kernel: sk.Kernel):
        self.name = "TaskOrchestrator"
        self.role = "Task Analysis and Routing Specialist"
        self.kernel = kernel
        self.routing_history = []
        self.created_at = datetime.now()
    
    async def analyze_input(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze user input and determine routing"""
        logger.info(f"Orchestrator analyzing input: {user_input[:50]}...")
        
        try:
            # Try AI-powered analysis first
            if self.kernel and hasattr(self.kernel, 'services'):
                analysis = await self._ai_analysis(user_input, context)
            else:
                # Fallback to keyword-based analysis
                analysis = self._keyword_analysis(user_input, context)
            
            # Record routing decision
            self.routing_history.append({
                "input": user_input[:100],
                "department": analysis["department"],
                "confidence": analysis["confidence"],
                "timestamp": datetime.now().isoformat()
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing input: {str(e)}")
            # Return fallback analysis
            return self._fallback_analysis(user_input, context)
    
    async def create_task(self, analysis: Dict[str, Any]) -> Task:
        """Create task from analysis results"""
        
        # Generate task ID
        task_id = f"TASK_{len(self.routing_history):04d}"
        
        # Determine priority from analysis
        priority = self._determine_priority(analysis)
        
        # Create task
        task = Task(
            id=task_id,
            title=analysis.get("title", "Marketing Task"),
            description=analysis.get("description", "User requested marketing task"),
            priority=priority,
            context=analysis
        )
        
        return task
    
    async def _ai_analysis(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """AI-powered input analysis"""
        
        # This would use the AI service to analyze the input
        # For now, return structured analysis
        return {
            "title": self._extract_title(user_input),
            "description": user_input,
            "department": self._classify_department(user_input),
            "suggested_agent": self._suggest_agent(user_input),
            "priority": self._detect_priority(user_input),
            "confidence": 0.85,
            "reasoning": "AI analysis based on content classification",
            "estimated_duration": "2-3 days"
        }
    
    def _keyword_analysis(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Keyword-based input analysis"""
        
        department = self._classify_department(user_input)
        
        return {
            "title": self._extract_title(user_input),
            "description": user_input,
            "department": department,
            "suggested_agent": self._suggest_agent(user_input),
            "priority": self._detect_priority(user_input),
            "confidence": 0.75,
            "reasoning": f"Keyword-based routing to {department} department",
            "estimated_duration": "1-2 days"
        }
    
    def _fallback_analysis(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback analysis when other methods fail"""
        
        return {
            "title": "General Marketing Task",
            "description": user_input,
            "department": "content",  # Default to content marketing
            "suggested_agent": None,
            "priority": "medium",
            "confidence": 0.5,
            "reasoning": "Fallback routing due to analysis error",
            "estimated_duration": "Unknown"
        }
    
    def _classify_department(self, text: str) -> str:
        """Classify text into marketing departments"""
        text_lower = text.lower()
        
        # Executive/Financial keywords - NEW CATEGORY
        executive_keywords = [
            "earning", "earnings", "financial", "revenue", "profit", "cmo", "executive",
            "strategy", "strategic", "quarterly", "annual", "performance",
            "roi", "budget", "investment", "growth rate", "market share",
            "competitive advantage", "business impact", "cross-division",
            "coordination", "oversight", "leadership", "board", "stakeholder",
            "quarterly results", "annual report", "financial data", "earnings report",
            "income", "sales", "margin", "cash flow", "ebitda", "fiscal"
        ]
        
        # Product marketing keywords
        product_keywords = [
            "product", "launch", "positioning", "competitor", "competitive",
            "market research", "persona", "gtm", "go-to-market", "pricing",
            "differentiation", "value proposition", "customer research"
        ]
        
        # Digital marketing keywords  
        digital_keywords = [
            "seo", "sem", "google", "search", "ads", "ppc", "analytics",
            "conversion", "landing page", "funnel", "website", "traffic",
            "keyword", "optimization", "search engine", "paid search"
        ]
        
        # Content marketing keywords (EXPANDED for social media)
        content_keywords = [
            "content", "blog", "social", "brand", "design", "creative",
            "linkedin", "twitter", "facebook", "community", "engagement",
            "instagram", "post", "caption", "social media", "writing",
            "copywriting", "visual", "graphics", "story", "storytelling",
            "tiktok", "youtube", "pinterest", "content creation", "text",
            "description", "copy", "message", "campaign"
        ]
        
        # Count keyword matches
        executive_score = sum(1 for keyword in executive_keywords if keyword in text_lower)
        product_score = sum(1 for keyword in product_keywords if keyword in text_lower)
        digital_score = sum(1 for keyword in digital_keywords if keyword in text_lower)
        content_score = sum(1 for keyword in content_keywords if keyword in text_lower)
        
        # Special case handling for obvious content tasks
        social_indicators = ["instagram", "facebook", "twitter", "linkedin", "tiktok", 
                           "social media", "post", "caption", "story"]
        if any(indicator in text_lower for indicator in social_indicators):
            content_score += 3  # Heavy bias toward content marketing
        
        # Content creation indicators
        content_creation_indicators = ["write", "create text", "description", "copy", "caption"]
        if any(indicator in text_lower for indicator in content_creation_indicators):
            content_score += 2
        
        # Return department with highest score
        if executive_score > 0 and executive_score >= max(product_score, digital_score, content_score):
            return "executive"
        elif product_score >= digital_score and product_score >= content_score:
            return "product"
        elif digital_score >= content_score:
            return "digital"
        else:
            return "content"
    
    def _suggest_agent(self, text: str) -> Optional[str]:
        """Suggest specific agent based on text content"""
        text_lower = text.lower()
        
        # Agent keyword mapping
        agent_keywords = {
            # Product Marketing
            "PositioningAgent": ["positioning", "differentiation", "value prop"],
            "PersonaAgent": ["persona", "customer research", "user research"],
            "GTMAgent": ["gtm", "go-to-market", "launch strategy"],
            "CompetitorAgent": ["competitor", "competitive", "market analysis"],
            "LaunchAgent": ["launch content", "messaging", "product launch"],
            # Digital Marketing
            "SEOAgent": ["seo", "search optimization", "organic", "keyword"],
            "SEMAgent": ["sem", "ppc", "google ads", "paid search"],
            "LandingAgent": ["landing page", "conversion", "cro"],
            "AnalyticsAgent": ["analytics", "metrics", "tracking", "attribution"],
            "FunnelAgent": ["funnel", "conversion testing", "user flow"],
            # Content Marketing
            "ContentAgent": ["content", "writing", "blog", "copywriting", "article"],
            "BrandAgent": ["brand", "design", "visual", "identity", "graphics"],
            "SocialAgent": ["social media", "posting", "schedule", "instagram", "facebook", 
                           "twitter", "linkedin", "tiktok", "post", "caption", "story"],
            "CommunityAgent": ["community", "engagement", "relationship", "interaction"]
        }
        
        # Special handling for obvious social media tasks
        if any(word in text_lower for word in ["instagram", "facebook", "twitter", "linkedin", 
                                               "tiktok", "social media", "post", "caption"]):
            return "SocialAgent"
        
        # Find best matching agent
        best_agent = None
        best_score = 0
        
        for agent, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent
    
    def _detect_priority(self, text: str) -> str:
        """Detect task priority from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["urgent", "asap", "immediately", "emergency"]):
            return "urgent"
        elif any(word in text_lower for word in ["high priority", "important", "critical"]):
            return "high"
        elif any(word in text_lower for word in ["low priority", "when possible", "no rush"]):
            return "low"
        else:
            return "medium"
    
    def _determine_priority(self, analysis: Dict[str, Any]) -> TaskPriority:
        """Convert priority string to TaskPriority enum"""
        priority_str = analysis.get("priority", "medium").lower()
        
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        
        return priority_map.get(priority_str, TaskPriority.MEDIUM)
    
    def _extract_title(self, text: str) -> str:
        """Extract a concise title from user input"""
        # Take first sentence or first 50 characters
        sentences = text.split('.')
        if sentences:
            title = sentences[0].strip()
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        return text[:50] + "..." if len(text) > 50 else text
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator performance metrics"""
        
        if not self.routing_history:
            return {
                "total_analyzed": 0,
                "average_confidence": 0,
                "department_routing": {}
            }
        
        total_confidence = sum(entry["confidence"] for entry in self.routing_history)
        avg_confidence = total_confidence / len(self.routing_history)
        
        # Count department routing
        dept_counts = {}
        for entry in self.routing_history:
            dept = entry["department"]
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        return {
            "total_analyzed": len(self.routing_history),
            "average_confidence": avg_confidence,
            "department_routing": dept_counts
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert orchestrator to dictionary"""
        return {
            "name": self.name,
            "role": self.role,
            "metrics": self.get_metrics(),
            "created_at": self.created_at.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.name} - {len(self.routing_history)} tasks analyzed"
    
    def __repr__(self) -> str:
        return f"Orchestrator(analyzed={len(self.routing_history)})" 