"""
Calendar Manager
===============

Main orchestrator for calendar integration. 
Coordinates detection, handling, and formatting of calendar requests.
"""

import logging
from typing import Optional, Dict, Any
from .detector import CalendarDetector, CalendarRequestType
from .handler import CalendarHandler
from .formatter import CalendarFormatter

logger = logging.getLogger(__name__)


class CalendarManager:
    """
    Main calendar integration manager.
    Orchestrates the entire calendar request flow.
    """
    
    def __init__(self):
        """Initialize the calendar manager with all components"""
        self.detector = CalendarDetector()
        self.handler = CalendarHandler()
        self.formatter = CalendarFormatter()
        
        logger.info("📅 CalendarManager initialized with all components")
    
    def is_available(self) -> bool:
        """Check if calendar integration is available"""
        return self.handler.is_available()
    
    async def process_request(self, user_input: str, user_id: str) -> Optional[str]:
        """
        Process a user request for calendar information
        
        Args:
            user_input: User's message/request
            user_id: User ID for calendar access
            
        Returns:
            Formatted calendar response or None if not a calendar request
        """
        try:
            # Step 1: Detect if this is a calendar request
            if not self.detector.is_calendar_request(user_input):
                logger.debug(f"🔍 Not a calendar request: {user_input[:50]}...")
                return None
            
            # Step 2: Classify the request and extract parameters
            request_info = self.detector.classify_request(user_input)
            
            if not request_info['recognized']:
                logger.warning(f"⚠️ Calendar request not properly classified: {user_input}")
                return None
            
            request_type = request_info['type']
            params = request_info['params']
            
            logger.info(f"📅 Processing {request_type.value} request with params: {params}")
            
            # Step 3: Handle the request (call Google Calendar API)
            events = await self.handler.handle_request(request_type, user_id, params)
            
            # Step 4: Format the response
            response = self.formatter.format_response(request_type, events, params)
            
            logger.info(f"✅ Calendar request processed successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing calendar request: {e}")
            return "❌ I'm having trouble accessing your Google Calendar right now. Please check your authentication."
    
    def is_calendar_request(self, user_input: str) -> bool:
        """
        Quick check if user input is calendar-related
        
        Args:
            user_input: User's message
            
        Returns:
            True if calendar-related, False otherwise
        """
        return self.detector.is_calendar_request(user_input)
    
    def get_supported_requests(self) -> Dict[str, str]:
        """
        Get information about supported calendar request types
        
        Returns:
            Dictionary mapping request types to descriptions
        """
        return {
            "today": "Get today's calendar events",
            "tomorrow": "Get tomorrow's calendar events", 
            "upcoming": "Get upcoming events (next 7 days by default)",
            "search": "Search for specific events by keywords",
            "general": "General calendar information"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status information about calendar integration
        
        Returns:
            Status dictionary
        """
        return {
            "available": self.is_available(),
            "detector_ready": self.detector is not None,
            "handler_ready": self.handler is not None,
            "formatter_ready": self.formatter is not None,
            "supported_requests": list(self.get_supported_requests().keys())
        }


# Convenience function for easy importing
async def process_calendar_request(user_input: str, user_id: str) -> Optional[str]:
    """
    Convenience function to process calendar requests
    
    Args:
        user_input: User's message
        user_id: User ID for calendar access
        
    Returns:
        Formatted calendar response or None if not a calendar request
    """
    manager = CalendarManager()
    return await manager.process_request(user_input, user_id)