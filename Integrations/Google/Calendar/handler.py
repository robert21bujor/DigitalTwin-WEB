"""
Calendar Request Handler
=======================

Handles calendar requests by calling Google Calendar API and processing results.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

# Add Gmail path for calendar service
gmail_path = str(Path(__file__).parent.parent / "Gmail")
if gmail_path not in sys.path:
    sys.path.append(gmail_path)

from .detector import CalendarRequestType

logger = logging.getLogger(__name__)


class CalendarHandler:
    """Handles calendar API calls and data processing"""
    
    def __init__(self):
        """Initialize the calendar handler"""
        self.calendar_service = None
        self._initialize_calendar_service()
        logger.info("📅 CalendarHandler initialized")
    
    def _initialize_calendar_service(self):
        """Initialize Google Calendar service"""
        try:
            from .google_calendar_service import GoogleCalendarService
            self.calendar_service = GoogleCalendarService()
            logger.info("✅ Google Calendar service initialized")
        except ImportError as e:
            logger.error(f"❌ Failed to import GoogleCalendarService: {e}")
            self.calendar_service = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize calendar service: {e}")
            self.calendar_service = None
    
    def is_available(self) -> bool:
        """Check if calendar service is available"""
        return self.calendar_service is not None
    
    def _should_use_fresh_data(self, params: Dict[str, Any]) -> bool:
        """
        Determine if we should use fresh data based on request context
        
        Args:
            params: Request parameters including original query
            
        Returns:
            True if fresh data should be used
        """
        original_query = params.get('original_query', '').lower()
        
        # Keywords that suggest user is asking about recently added events
        fresh_keywords = [
            'just', 'added', 'created', 'new', 'latest',
            'recent', 'recently', 'current', 'now', 'updated', 'changed',
            'fresh', 'live', 'real-time', 'immediate', 'instant'
        ]
        
        # Check if any fresh keywords are in the query
        has_fresh_keywords = any(keyword in original_query for keyword in fresh_keywords)
        
        # Always use fresh data for today's requests (most likely to have new events)
        is_today_request = any(word in original_query for word in ['today', 'now', 'current'])
        
        return has_fresh_keywords or is_today_request
    
    async def handle_request(self, request_type: CalendarRequestType, user_id: str, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Handle calendar request based on type and parameters
        
        Args:
            request_type: Type of calendar request
            user_id: User ID for calendar access
            params: Request parameters
            
        Returns:
            List of calendar events or None if error
        """
        if not self.is_available():
            logger.error("❌ Calendar service not available")
            return None
        
        try:
            logger.info(f"📅 Handling {request_type.value} request for user {user_id}")
            
            # Determine if we should use fresh data
            use_fresh_data = self._should_use_fresh_data(params)
            if use_fresh_data:
                logger.info("🔄 Using fresh data for real-time sync")
            
            if request_type == CalendarRequestType.TODAY:
                return await self._handle_today_request(user_id, use_fresh_data)
                
            elif request_type == CalendarRequestType.TOMORROW:
                return await self._handle_tomorrow_request(user_id)
                
            elif request_type == CalendarRequestType.YESTERDAY:
                return await self._handle_yesterday_request(user_id)
                
            elif request_type == CalendarRequestType.SPECIFIC_DATE:
                target_date = params.get('target_date')
                return await self._handle_specific_date_request(user_id, target_date)
                
            elif request_type == CalendarRequestType.DATE_RANGE:
                start_date = params.get('start_date')
                end_date = params.get('end_date')
                return await self._handle_date_range_request(user_id, start_date, end_date)
                
            elif request_type == CalendarRequestType.MONTH:
                start_date = params.get('start_date')
                end_date = params.get('end_date')
                return await self._handle_month_request(user_id, start_date, end_date)
                
            elif request_type == CalendarRequestType.YEAR:
                start_date = params.get('start_date')
                end_date = params.get('end_date')
                return await self._handle_year_request(user_id, start_date, end_date)
                
            elif request_type == CalendarRequestType.WEEK:
                start_date = params.get('start_date')
                end_date = params.get('end_date')
                return await self._handle_week_request(user_id, start_date, end_date)
                
            elif request_type == CalendarRequestType.UPCOMING:
                days = params.get('days', 7)
                return await self._handle_upcoming_request(user_id, days)
                
            elif request_type == CalendarRequestType.SEARCH:
                search_term = params.get('search_term', '')
                return await self._handle_search_request(user_id, search_term)
                
            elif request_type == CalendarRequestType.GENERAL:
                # Default to today's events
                return await self._handle_today_request(user_id)
                
            else:
                logger.warning(f"⚠️ Unknown request type: {request_type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error handling calendar request: {e}")
            return None
    
    async def _handle_today_request(self, user_id: str, use_fresh_data: bool = False) -> Optional[List[Dict]]:
        """Handle request for today's events"""
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"📅 Getting events for today: {today} {'(FRESH)' if use_fresh_data else ''}")
        
        try:
            if use_fresh_data:
                events = self.calendar_service.get_events_for_date_fresh(user_id, today)
            else:
                events = self.calendar_service.get_events_for_date(user_id, today)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for today")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting today's events: {e}")
            return None
    
    async def _handle_tomorrow_request(self, user_id: str) -> Optional[List[Dict]]:
        """Handle request for tomorrow's events"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"📅 Getting events for tomorrow: {tomorrow}")
        
        try:
            events = self.calendar_service.get_events_for_date(user_id, tomorrow)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for tomorrow")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting tomorrow's events: {e}")
            return None
    
    async def _handle_yesterday_request(self, user_id: str) -> Optional[List[Dict]]:
        """Handle request for yesterday's events"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"📅 Getting events for yesterday: {yesterday}")
        
        try:
            events = self.calendar_service.get_events_for_date(user_id, yesterday)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for yesterday")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting yesterday's events: {e}")
            return None
    
    async def _handle_upcoming_request(self, user_id: str, days: int) -> Optional[List[Dict]]:
        """Handle request for upcoming events"""
        logger.info(f"📅 Getting upcoming events for next {days} days")
        
        try:
            events = self.calendar_service.get_upcoming_events(user_id, days)
            logger.info(f"✅ Retrieved {len(events) if events else 0} upcoming events")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting upcoming events: {e}")
            return None
    
    async def _handle_search_request(self, user_id: str, search_term: str) -> Optional[List[Dict]]:
        """Handle search request for specific events"""
        if not search_term:
            logger.warning("⚠️ Empty search term provided")
            return []
            
        logger.info(f"📅 Searching events with term: '{search_term}'")
        
        try:
            events = self.calendar_service.search_events(user_id, search_term)
            logger.info(f"✅ Found {len(events) if events else 0} events matching '{search_term}'")
            return events
        except Exception as e:
            logger.error(f"❌ Error searching events: {e}")
            return None
    
    async def _handle_specific_date_request(self, user_id: str, target_date: str) -> Optional[List[Dict]]:
        """Handle request for a specific date"""
        logger.info(f"📅 Getting events for specific date: {target_date}")
        
        try:
            events = self.calendar_service.get_events_for_date(user_id, target_date)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for {target_date}")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting events for {target_date}: {e}")
            return None
    
    async def _handle_date_range_request(self, user_id: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Handle request for a date range"""
        logger.info(f"📅 Getting events for date range: {start_date} to {end_date}")
        
        try:
            events = self.calendar_service.get_events(user_id, start_date=start_date, end_date=end_date, max_results=100)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for date range")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting events for date range {start_date} to {end_date}: {e}")
            return None
    
    async def _handle_month_request(self, user_id: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Handle request for a specific month"""
        logger.info(f"📅 Getting events for month: {start_date} to {end_date}")
        
        try:
            events = self.calendar_service.get_events(user_id, start_date=start_date, end_date=end_date, max_results=200)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for month")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting events for month {start_date} to {end_date}: {e}")
            return None
    
    async def _handle_year_request(self, user_id: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Handle request for a specific year"""
        logger.info(f"📅 Getting events for year: {start_date} to {end_date}")
        
        try:
            events = self.calendar_service.get_events(user_id, start_date=start_date, end_date=end_date, max_results=1000)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for year")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting events for year {start_date} to {end_date}: {e}")
            return None
    
    async def _handle_week_request(self, user_id: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Handle request for a specific week"""
        logger.info(f"📅 Getting events for week: {start_date} to {end_date}")
        
        try:
            events = self.calendar_service.get_events(user_id, start_date=start_date, end_date=end_date, max_results=50)
            logger.info(f"✅ Retrieved {len(events) if events else 0} events for week")
            return events
        except Exception as e:
            logger.error(f"❌ Error getting events for week {start_date} to {end_date}: {e}")
            return None
    
    def parse_date(self, date_str: str) -> str:
        """
        Parse natural language date strings to YYYY-MM-DD format
        
        Args:
            date_str: Date string (e.g., 'today', 'tomorrow', 'monday')
            
        Returns:
            Formatted date string
        """
        date_str = date_str.lower().strip()
        
        if date_str == "today":
            return datetime.now().strftime('%Y-%m-%d')
        elif date_str == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str == "yesterday":
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            # Find next occurrence of this weekday
            days_ahead = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(date_str)
            current_day = datetime.now().weekday()
            days_to_add = (days_ahead - current_day) % 7
            if days_to_add == 0:  # If it's the same day, get next week's occurrence
                days_to_add = 7
            target_date = datetime.now() + timedelta(days=days_to_add)
            return target_date.strftime('%Y-%m-%d')
        else:
            # Assume it's already in YYYY-MM-DD format or return as-is
            return date_str