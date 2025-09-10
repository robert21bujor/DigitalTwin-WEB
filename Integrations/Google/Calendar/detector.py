"""
Calendar Request Detector
========================

Detects and classifies calendar-related user requests.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from .advanced_date_parser import AdvancedDateParser

logger = logging.getLogger(__name__)


class CalendarRequestType(Enum):
    """Types of calendar requests"""
    TODAY = "today"
    TOMORROW = "tomorrow"
    YESTERDAY = "yesterday"
    UPCOMING = "upcoming"
    SPECIFIC_DATE = "specific_date"
    DATE_RANGE = "date_range"
    MONTH = "month"
    YEAR = "year"
    WEEK = "week"
    SEARCH = "search"
    GENERAL = "general"


class CalendarDetector:
    """Detects calendar-related user requests and classifies them"""
    
    def __init__(self):
        """Initialize the calendar detector with keyword mappings"""
        # Initialize advanced date parser
        self.date_parser = AdvancedDateParser()
        
        self.calendar_keywords = {
            # General calendar terms
            'calendar', 'schedule', 'meeting', 'meetings', 'event', 'events',
            'appointment', 'appointments', 'scheduled', 'agenda', 'busy', 'free time',
            
            # Time-based terms
            'today', 'tomorrow', 'yesterday', 'this week', 'next week', 'last week',
            'this month', 'next month', 'last month', 'this year', 'next year', 'last year',
            'upcoming', 'during', 'in', 'all events',
            
            # Day names
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
            
            # Month names
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            
            # Question patterns
            'whats on my', 'what do i have', 'what did i have', 'my calendar', 'google calendar',
            'do i have', 'did i have', 'am i busy', 'am i free', 'whats scheduled',
            'show me events', 'events for', 'meetings for', 'all events in'
        }
        
        self.today_keywords = [
            'today', 'today\'s', 'what do i have today', 'todays', 'this day'
        ]
        
        self.tomorrow_keywords = [
            'tomorrow', 'tomorrow\'s', 'tomorrows', 'next day'
        ]
        
        self.yesterday_keywords = [
            'yesterday', 'yesterday\'s', 'yesterdays', 'previous day', 'last day'
        ]
        
        self.upcoming_keywords = [
            'this week', 'upcoming', 'next few days', 'coming up', 
            'next week', 'this month', 'soon'
        ]
        
        self.month_keywords = [
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            'this month', 'next month', 'last month', 'all events in'
        ]
        
        self.year_keywords = [
            'this year', 'next year', 'last year', 'year', 'all events in'
        ]
        
        self.week_keywords = [
            'this week', 'next week', 'last week', 'week'
        ]
        
        self.date_range_keywords = [
            'all events', 'events in', 'during', 'throughout', 'from', 'to', 'between'
        ]
        
        self.search_keywords = [
            'search', 'find', 'meeting with', 'look for', 'show me'
        ]
        
        logger.info("📅 CalendarDetector initialized")
    
    def is_calendar_request(self, user_input: str) -> bool:
        """
        Check if user input is calendar-related
        
        Args:
            user_input: User's message
            
        Returns:
            True if calendar-related, False otherwise
        """
        if not user_input:
            return False
            
        user_lower = user_input.lower().strip()
        
        # Check for any calendar-related keywords
        is_calendar = any(keyword in user_lower for keyword in self.calendar_keywords)
        
        if is_calendar:
            logger.info(f"📅 Calendar request detected: {user_input[:50]}...")
            
        return is_calendar
    
    def classify_request(self, user_input: str) -> Dict[str, Any]:
        """
        Classify the type of calendar request and extract parameters
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with request type and extracted parameters
        """
        if not self.is_calendar_request(user_input):
            return {
                'type': None,
                'recognized': False,
                'params': {}
            }
        
        user_lower = user_input.lower().strip()
        
        # Classify request type
        request_type = CalendarRequestType.GENERAL
        params = {}
        
        # Use advanced date parser to get comprehensive date info
        date_info = self.date_parser.extract_date_info(user_input)
        
        # Check for specific request types in priority order
        if any(keyword in user_lower for keyword in self.today_keywords):
            request_type = CalendarRequestType.TODAY
            params['date_type'] = 'today'
            params['original_query'] = user_input  # Include for fresh data detection
            
        elif any(keyword in user_lower for keyword in self.tomorrow_keywords):
            request_type = CalendarRequestType.TOMORROW
            params['date_type'] = 'tomorrow'
            params['original_query'] = user_input  # Include for fresh data detection
            
        elif any(keyword in user_lower for keyword in self.yesterday_keywords):
            request_type = CalendarRequestType.YESTERDAY
            params['date_type'] = 'yesterday'
            params['original_query'] = user_input  # Include for fresh data detection
            
        elif date_info['type'] == 'date_range' and date_info['confidence'] > 0.7:
            # Handle date ranges (months, years, weeks)
            if any(keyword in user_lower for keyword in self.month_keywords):
                request_type = CalendarRequestType.MONTH
                params['date_type'] = 'month'
            elif any(keyword in user_lower for keyword in self.year_keywords):
                request_type = CalendarRequestType.YEAR
                params['date_type'] = 'year'
            elif any(keyword in user_lower for keyword in self.week_keywords):
                request_type = CalendarRequestType.WEEK
                params['date_type'] = 'week'
            else:
                request_type = CalendarRequestType.DATE_RANGE
                params['date_type'] = 'date_range'
                
            params['start_date'] = date_info['start_date']
            params['end_date'] = date_info['end_date']
            params['original_query'] = user_input
            
        elif date_info['type'] == 'specific_date' and date_info['confidence'] > 0.7:
            request_type = CalendarRequestType.SPECIFIC_DATE
            params['date_type'] = 'specific_date'
            params['target_date'] = date_info['parsed_date']
            params['original_query'] = user_input
            
        elif any(keyword in user_lower for keyword in self.upcoming_keywords):
            request_type = CalendarRequestType.UPCOMING
            params['days'] = 7  # Default to 7 days
            params['original_query'] = user_input  # Include for fresh data detection
            
            # Try to extract specific number of days
            words = user_input.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    if i + 1 < len(words) and words[i + 1].lower() in ['day', 'days']:
                        params['days'] = int(word)
                        break
                        
        elif any(keyword in user_lower for keyword in self.search_keywords):
            request_type = CalendarRequestType.SEARCH
            params['original_query'] = user_input  # Include for fresh data detection
            
            # Extract search term by removing common words
            search_term = user_input
            for remove_word in ['search', 'find', 'meeting with', 'look for', 'show me', 'my', 'calendar']:
                search_term = search_term.replace(remove_word, '')
            
            search_term = search_term.strip()
            params['search_term'] = search_term
        
        # Ensure original_query is always included for fresh data detection
        if 'original_query' not in params:
            params['original_query'] = user_input
        
        result = {
            'type': request_type,
            'recognized': True,
            'params': params,
            'original_input': user_input
        }
        
        logger.info(f"📅 Request classified as: {request_type.value} with params: {params}")
        
        return result
    
    def extract_day_name(self, user_input: str) -> Optional[str]:
        """
        Extract day name from user input (e.g., 'monday', 'tuesday')
        
        Args:
            user_input: User's message
            
        Returns:
            Day name if found, None otherwise
        """
        user_lower = user_input.lower()
        
        day_names = {
            'monday': 'monday', 'mon': 'monday',
            'tuesday': 'tuesday', 'tue': 'tuesday', 'tues': 'tuesday',
            'wednesday': 'wednesday', 'wed': 'wednesday',
            'thursday': 'thursday', 'thu': 'thursday', 'thurs': 'thursday',
            'friday': 'friday', 'fri': 'friday',
            'saturday': 'saturday', 'sat': 'saturday',
            'sunday': 'sunday', 'sun': 'sunday'
        }
        
        for day_variant, full_day in day_names.items():
            if day_variant in user_lower:
                logger.info(f"📅 Day extracted: {full_day}")
                return full_day
                
        return None