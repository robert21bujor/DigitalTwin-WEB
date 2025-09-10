"""
Google Calendar Integration Module
=================================

Modular calendar integration for AI agents.
Provides direct Google Calendar access with clean separation of concerns.
"""

from .calendar_manager import CalendarManager
from .detector import CalendarDetector
from .handler import CalendarHandler
from .formatter import CalendarFormatter
from .google_calendar_service import GoogleCalendarService

__all__ = [
    'CalendarManager',
    'CalendarDetector', 
    'CalendarHandler',
    'CalendarFormatter',
    'GoogleCalendarService'
]

__version__ = "1.0.0"
__author__ = "Digital Twin System"