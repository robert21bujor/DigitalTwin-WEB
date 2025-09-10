"""
Calendar Response Formatter
===========================

Formats calendar data into user-friendly responses with emojis and structure.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from .detector import CalendarRequestType

logger = logging.getLogger(__name__)


class CalendarFormatter:
    """Formats calendar events into readable responses"""
    
    def __init__(self):
        """Initialize the calendar formatter"""
        logger.info("📅 CalendarFormatter initialized")
    
    def format_response(self, request_type: CalendarRequestType, events: Optional[List[Dict]], 
                       params: Dict = None) -> str:
        """
        Format calendar events into a user-friendly response
        
        Args:
            request_type: Type of calendar request
            events: List of calendar events
            params: Additional parameters from the request
            
        Returns:
            Formatted response string
        """
        if events is None:
            return self._format_error_response()
        
        if not events:
            return self._format_empty_response(request_type, params)
        
        try:
            if request_type == CalendarRequestType.TODAY:
                return self._format_today_response(events)
                
            elif request_type == CalendarRequestType.TOMORROW:
                return self._format_tomorrow_response(events)
                
            elif request_type == CalendarRequestType.UPCOMING:
                days = params.get('days', 7) if params else 7
                return self._format_upcoming_response(events, days)
                
            elif request_type == CalendarRequestType.SEARCH:
                search_term = params.get('search_term', '') if params else ''
                return self._format_search_response(events, search_term)
                
            else:
                return self._format_general_response(events)
                
        except Exception as e:
            logger.error(f"❌ Error formatting response: {e}")
            return self._format_error_response()
    
    def _format_today_response(self, events: List[Dict]) -> str:
        """Format today's events"""
        result = "📅 **Your schedule for today:**\n\n"
        
        for i, event in enumerate(events, 1):
            result += f"**{i}. {event['summary']}**\n"
            
            # Add time information
            if event['start'] and len(event['start']) > 10:  # Timed event
                start_time = self._extract_time(event['start'])
                end_time = self._extract_time(event['end']) if event['end'] else ""
                result += f"⏰ {start_time}"
                if end_time:
                    result += f" - {end_time}"
                result += "\n"
            else:
                result += "📅 All day\n"
            
            # Add location
            if event.get('location'):
                result += f"📍 {event['location']}\n"
            
            # Add description (truncated)
            if event.get('description'):
                desc = event['description'][:100] + "..." if len(event['description']) > 100 else event['description']
                result += f"📝 {desc}\n"
            
            result += "\n"
        
        return result
    
    def _format_tomorrow_response(self, events: List[Dict]) -> str:
        """Format tomorrow's events"""
        result = "📅 **Your schedule for tomorrow:**\n\n"
        
        for i, event in enumerate(events, 1):
            result += f"**{i}. {event['summary']}**\n"
            
            # Add time information
            if event['start'] and len(event['start']) > 10:
                start_time = self._extract_time(event['start'])
                end_time = self._extract_time(event['end']) if event['end'] else ""
                result += f"⏰ {start_time}"
                if end_time:
                    result += f" - {end_time}"
                result += "\n"
            
            # Add location
            if event.get('location'):
                result += f"📍 {event['location']}\n"
            
            result += "\n"
        
        return result
    
    def _format_upcoming_response(self, events: List[Dict], days: int) -> str:
        """Format upcoming events grouped by date"""
        result = f"📅 **Your upcoming events (next {days} days):**\n\n"
        
        current_date = ""
        for event in events:
            event_date = event['start'][:10] if event['start'] else ""
            
            # Group by date
            if event_date != current_date:
                current_date = event_date
                formatted_date = self._format_date_display(current_date)
                result += f"**{formatted_date}:**\n"
            
            result += f"• **{event['summary']}**"
            
            # Add time for timed events
            if event['start'] and len(event['start']) > 10:
                start_time = self._extract_time(event['start'])
                result += f" at {start_time}"
            
            # Add location
            if event.get('location'):
                result += f" ({event['location']})"
            
            result += "\n"
        
        return result
    
    def _format_search_response(self, events: List[Dict], search_term: str) -> str:
        """Format search results"""
        result = f"📅 **Events matching '{search_term}':**\n\n"
        
        for i, event in enumerate(events, 1):
            result += f"**{i}. {event['summary']}**\n"
            
            # Add date and time
            if event['start']:
                if len(event['start']) == 10:  # All-day event
                    result += f"📅 {self._format_date_display(event['start'])}\n"
                else:
                    date_part = event['start'][:10]
                    time_part = self._extract_time(event['start'])
                    result += f"📅 {self._format_date_display(date_part)} at {time_part}\n"
            
            # Add location
            if event.get('location'):
                result += f"📍 {event['location']}\n"
            
            result += "\n"
        
        return result
    
    def _format_general_response(self, events: List[Dict]) -> str:
        """Format general calendar response (fallback)"""
        result = "📅 **Your calendar:**\n\n"
        
        for i, event in enumerate(events, 1):
            result += f"**{i}. {event['summary']}**\n"
            if event['start'] and len(event['start']) > 10:
                start_time = self._extract_time(event['start'])
                result += f"⏰ {start_time}\n"
            result += "\n"
        
        return result
    
    def _format_empty_response(self, request_type: CalendarRequestType, params: Dict = None) -> str:
        """Format response when no events are found"""
        if request_type == CalendarRequestType.TODAY:
            return "📅 **Your schedule for today:** You have no events scheduled for today. Your day is free!"
            
        elif request_type == CalendarRequestType.TOMORROW:
            return "📅 **Your schedule for tomorrow:** You have no events scheduled for tomorrow. Your day is free!"
            
        elif request_type == CalendarRequestType.UPCOMING:
            days = params.get('days', 7) if params else 7
            return f"📅 **Your upcoming schedule:** You have no events scheduled for the next {days} days. Your week is free!"
            
        elif request_type == CalendarRequestType.SEARCH:
            search_term = params.get('search_term', '') if params else ''
            return f"📅 No events found matching '{search_term}' in your calendar."
            
        else:
            return "📅 **Your calendar:** You have no events scheduled. Your calendar is free!"
    
    def _format_error_response(self) -> str:
        """Format error response"""
        return "❌ I'm having trouble accessing your Google Calendar right now. Please make sure you're authenticated."
    
    def _extract_time(self, datetime_str: str) -> str:
        """Extract time from datetime string"""
        try:
            if len(datetime_str) <= 10:  # Date only
                return ""
            
            # Extract HH:MM from datetime string
            time_part = datetime_str[11:16]  # Gets HH:MM from YYYY-MM-DDTHH:MM:SS format
            return time_part
            
        except Exception:
            return datetime_str
    
    def _format_date_display(self, date_str: str) -> str:
        """Format date string for display"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Check if it's today, tomorrow, etc.
            today = datetime.now().date()
            event_date = date_obj.date()
            
            if event_date == today:
                return f"Today ({date_obj.strftime('%B %d, %Y')})"
            elif event_date == today + timedelta(days=1):
                return f"Tomorrow ({date_obj.strftime('%B %d, %Y')})"
            else:
                return date_obj.strftime('%A, %B %d, %Y')
                
        except Exception:
            return date_str