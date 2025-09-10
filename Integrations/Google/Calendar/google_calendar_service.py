"""
Google Calendar Service
Provides calendar access using Gmail OAuth tokens for agents
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar service using Gmail OAuth tokens"""
    
    def __init__(self):
        """Initialize Google Calendar Service"""
        self.service = None
        
    def get_calendar_service(self, user_id: str, force_refresh: bool = False):
        """Get Google Calendar service using Gmail OAuth tokens"""
        try:
            # Import Gmail services for OAuth token access
            import sys
            from pathlib import Path
            gmail_path = str(Path(__file__).parent.parent / "Gmail")
            if gmail_path not in sys.path:
                sys.path.append(gmail_path)
            
            from Integrations.Google.Gmail.gmail_database import gmail_database
            from Integrations.Google.Gmail.gmail_auth import GmailAuthService
            
            # Get Gmail OAuth tokens
            token_data = gmail_database.get_gmail_tokens(user_id)
            if not token_data:
                logger.error(f"No Gmail tokens found for user {user_id}")
                return None
            
            # Use Gmail auth service to get credentials
            auth_service = GmailAuthService()
            credentials = auth_service.get_credentials(token_data)
            
            if not credentials:
                logger.error("Failed to get valid credentials for Google Calendar")
                return None
            
            # Force refresh credentials if requested (for real-time sync)
            if force_refresh and hasattr(credentials, 'refresh'):
                try:
                    import google.auth.transport.requests
                    request = google.auth.transport.requests.Request()
                    credentials.refresh(request)
                    logger.info(f"🔄 Refreshed credentials for real-time sync")
                except Exception as e:
                    logger.warning(f"⚠️ Could not refresh credentials: {e}")
            
            # Build Google Calendar service
            calendar_service = build('calendar', 'v3', credentials=credentials)
            logger.info(f"Google Calendar service initialized for user {user_id}")
            return calendar_service
            
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")
            return None
    
    def get_events(self, user_id: str, start_date: str = None, end_date: str = None, max_results: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Get calendar events for a user
        
        Args:
            user_id: User identifier
            start_date: Start date in YYYY-MM-DD format (defaults to today)
            end_date: End date in YYYY-MM-DD format (defaults to 7 days from start)
            max_results: Maximum number of events to return
            
        Returns:
            List of calendar events or None if error
        """
        try:
            service = self.get_calendar_service(user_id)
            if not service:
                return None
            
            # Set default dates if not provided
            if not start_date:
                start_date = datetime.now().strftime('%Y-%m-%d')
            
            if not end_date:
                # Default to 7 days from start date
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = start_dt + timedelta(days=7)
                end_date = end_dt.strftime('%Y-%m-%d')
            
            # Convert to RFC3339 format for Google Calendar API
            # Use user's timezone instead of UTC to get correct local dates
            # Asia/Jakarta is UTC+7 based on user rules
            time_min = f"{start_date}T00:00:00+07:00"
            time_max = f"{end_date}T23:59:59+07:00"
            
            logger.info(f"Fetching calendar events for user {user_id} from {start_date} to {end_date}")
            
            # Call Google Calendar API with real-time parameters
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                showDeleted=False,  # Ensure we get current events only
                showHiddenInvitations=False  # Skip hidden invitations for cleaner results
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events for easier reading
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': self._format_datetime(event.get('start')),
                    'end': self._format_datetime(event.get('end')),
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                    'creator': event.get('creator', {}).get('email', ''),
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', '')
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Successfully retrieved {len(formatted_events)} calendar events")
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            return None
    
    def get_events_fresh(self, user_id: str, start_date: str = None, end_date: str = None, max_results: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Get calendar events with forced credential refresh for real-time sync
        
        Args:
            user_id: User identifier
            start_date: Start date in YYYY-MM-DD format (defaults to today)
            end_date: End date in YYYY-MM-DD format (defaults to 7 days from start)
            max_results: Maximum number of events to return
            
        Returns:
            List of calendar events or None if error
        """
        try:
            # Force refresh credentials for real-time data
            service = self.get_calendar_service(user_id, force_refresh=True)
            if not service:
                return None
            
            # Set default dates if not provided
            if not start_date:
                start_date = datetime.now().strftime('%Y-%m-%d')
            
            if not end_date:
                # Default to 7 days from start date
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = start_dt + timedelta(days=7)
                end_date = end_dt.strftime('%Y-%m-%d')
            
            # Convert to RFC3339 format for Google Calendar API
            # Use user's timezone instead of UTC to get correct local dates
            # Asia/Jakarta is UTC+7 based on user rules
            time_min = f"{start_date}T00:00:00+07:00"
            time_max = f"{end_date}T23:59:59+07:00"
            
            logger.info(f"🔄 Fetching FRESH calendar events for user {user_id} from {start_date} to {end_date}")
            
            # Call Google Calendar API with real-time parameters and fresh credentials
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                showDeleted=False,  # Ensure we get current events only
                showHiddenInvitations=False  # Skip hidden invitations for cleaner results
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events for easier reading
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start': self._format_datetime(event.get('start')),
                    'end': self._format_datetime(event.get('end')),
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                    'creator': event.get('creator', {}).get('email', ''),
                    'status': event.get('status', ''),
                    'html_link': event.get('htmlLink', '')
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"✅ Successfully retrieved {len(formatted_events)} FRESH calendar events")
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching fresh calendar events: {e}")
            return None
    
    def get_events_for_date(self, user_id: str, date: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get calendar events for a specific date
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of calendar events for that date
        """
        return self.get_events(user_id, start_date=date, end_date=date)
    
    def get_events_for_date_fresh(self, user_id: str, date: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get calendar events for a specific date with forced refresh
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of calendar events for that date with fresh data
        """
        return self.get_events_fresh(user_id, start_date=date, end_date=date)
    
    def get_upcoming_events(self, user_id: str, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        Get upcoming calendar events
        
        Args:
            user_id: User identifier
            days: Number of days to look ahead
            
        Returns:
            List of upcoming calendar events
        """
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        return self.get_events(user_id, start_date=start_date, end_date=end_date)
    
    def _format_datetime(self, dt_info: Dict[str, Any]) -> str:
        """Format datetime from Google Calendar API response"""
        if not dt_info:
            return ""
        
        # Handle all-day events (date only)
        if 'date' in dt_info:
            return dt_info['date']
        
        # Handle timed events (dateTime)
        if 'dateTime' in dt_info:
            # Parse the datetime string and format it nicely
            try:
                dt = datetime.fromisoformat(dt_info['dateTime'].replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M')
            except:
                return dt_info['dateTime']
        
        return ""
    
    def search_events(self, user_id: str, query: str, max_results: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search calendar events by text query
        
        Args:
            user_id: User identifier
            query: Search query text
            max_results: Maximum number of events to return
            
        Returns:
            List of matching calendar events
        """
        try:
            service = self.get_calendar_service(user_id)
            if not service:
                return None
            
            logger.info(f"Searching calendar events for user {user_id} with query: {query}")
            
            # Search events
            events_result = service.events().list(
                calendarId='primary',
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event.get('id'),
                    'summary': event.get('summary', 'No title'),
                    'description': event.get('description', ''),
                    'start': self._format_datetime(event.get('start')),
                    'end': self._format_datetime(event.get('end')),
                    'location': event.get('location', ''),
                    'status': event.get('status', '')
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Found {len(formatted_events)} matching calendar events")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Error searching calendar events: {e}")
            return None