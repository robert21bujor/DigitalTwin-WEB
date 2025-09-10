"""
Advanced Date Parser for Calendar System
=========================================

Handles natural language date parsing and date range calculations.
"""

import logging
import re
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class AdvancedDateParser:
    """Advanced date parser with natural language support"""
    
    def __init__(self):
        """Initialize the advanced date parser"""
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        self.weekday_names = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        logger.info("📅 AdvancedDateParser initialized")
    
    def parse_natural_date(self, date_string: str) -> Optional[str]:
        """
        Parse natural language date to YYYY-MM-DD format
        
        Args:
            date_string: Natural language date string
            
        Returns:
            Date in YYYY-MM-DD format or None if parsing fails
        """
        if not date_string:
            return None
            
        date_str = date_string.lower().strip()
        today = datetime.now()
        
        try:
            # Handle relative dates
            if date_str in ["today"]:
                return today.strftime('%Y-%m-%d')
            elif date_str in ["tomorrow"]:
                return (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif date_str in ["yesterday"]:
                return (today - timedelta(days=1)).strftime('%Y-%m-%d')
                
            # Handle relative time expressions
            if "next week" in date_str:
                next_week = today + timedelta(weeks=1)
                return next_week.strftime('%Y-%m-%d')
            elif "last week" in date_str:
                last_week = today - timedelta(weeks=1)
                return last_week.strftime('%Y-%m-%d')
            elif "next month" in date_str:
                next_month = today + relativedelta(months=1)
                return next_month.strftime('%Y-%m-%d')
            elif "last month" in date_str:
                last_month = today - relativedelta(months=1)
                return last_month.strftime('%Y-%m-%d')
            elif "next year" in date_str:
                next_year = today + relativedelta(years=1)
                return next_year.strftime('%Y-%m-%d')
            elif "last year" in date_str:
                last_year = today - relativedelta(years=1)
                return last_year.strftime('%Y-%m-%d')
                
            # Handle weekday names with modifiers
            for weekday, day_num in self.weekday_names.items():
                if weekday in date_str:
                    if "next" in date_str:
                        return self._get_next_weekday(day_num, weeks_ahead=1).strftime('%Y-%m-%d')
                    elif "last" in date_str:
                        return self._get_last_weekday(day_num).strftime('%Y-%m-%d')
                    elif "this" in date_str:
                        return self._get_this_weekday(day_num).strftime('%Y-%m-%d')
                    else:
                        # Default to next occurrence
                        return self._get_next_weekday(day_num).strftime('%Y-%m-%d')
                        
            # Handle month names
            for month_name, month_num in self.month_names.items():
                if month_name in date_str:
                    # Extract year if specified
                    year = today.year
                    year_match = re.search(r'\b(20\d{2})\b', date_str)
                    if year_match:
                        year = int(year_match.group(1))
                    
                    # Extract day if specified
                    day = 1  # Default to first day of month
                    day_match = re.search(r'\b(\d{1,2})(st|nd|rd|th)?\b', date_str)
                    if day_match:
                        day = int(day_match.group(1))
                    
                    try:
                        target_date = datetime(year, month_num, day)
                        return target_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Invalid date, try with last day of month
                        target_date = datetime(year, month_num, 1) + relativedelta(months=1) - timedelta(days=1)
                        return target_date.strftime('%Y-%m-%d')
            
            # Try dateutil parser for other formats
            try:
                parsed_date = parser.parse(date_string, default=today)
                return parsed_date.strftime('%Y-%m-%d')
            except (ValueError, parser.ParserError):
                pass
                
            # If already in YYYY-MM-DD format, return as-is
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return date_str
                
        except Exception as e:
            logger.error(f"Error parsing date '{date_string}': {e}")
            
        return None
    
    def parse_date_range(self, date_string: str) -> Optional[Tuple[str, str]]:
        """
        Parse date range from natural language
        
        Args:
            date_string: Natural language date range string
            
        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format or None
        """
        date_str = date_string.lower().strip()
        today = datetime.now()
        
        try:
            # Handle month ranges
            for month_name, month_num in self.month_names.items():
                if month_name in date_str:
                    year = today.year
                    year_match = re.search(r'\b(20\d{2})\b', date_str)
                    if year_match:
                        year = int(year_match.group(1))
                    elif "last" in date_str:
                        if month_num > today.month:
                            year = today.year - 1
                        else:
                            year = today.year
                    elif "next" in date_str:
                        if month_num < today.month:
                            year = today.year + 1
                        else:
                            year = today.year
                    
                    start_date = datetime(year, month_num, 1)
                    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
                    
                    return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            # Handle year ranges
            year_match = re.search(r'\b(20\d{2})\b', date_str)
            if year_match and ("year" in date_str or len(date_str.strip()) == 4):
                year = int(year_match.group(1))
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31)
                return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            # Handle week ranges
            if "week" in date_str:
                if "next week" in date_str:
                    start_date = today + timedelta(weeks=1)
                    start_date = start_date - timedelta(days=start_date.weekday())  # Monday
                elif "last week" in date_str:
                    start_date = today - timedelta(weeks=1)
                    start_date = start_date - timedelta(days=start_date.weekday())  # Monday
                elif "this week" in date_str:
                    start_date = today - timedelta(days=today.weekday())  # Monday
                else:
                    start_date = today - timedelta(days=today.weekday())  # This week
                
                end_date = start_date + timedelta(days=6)  # Sunday
                return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                
        except Exception as e:
            logger.error(f"Error parsing date range '{date_string}': {e}")
            
        return None
    
    def _get_next_weekday(self, target_weekday: int, weeks_ahead: int = 0) -> datetime:
        """Get the next occurrence of a weekday"""
        today = datetime.now()
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        if weeks_ahead > 0:
            days_ahead += (weeks_ahead - 1) * 7
            
        return today + timedelta(days=days_ahead)
    
    def _get_last_weekday(self, target_weekday: int) -> datetime:
        """Get the last occurrence of a weekday"""
        today = datetime.now()
        days_back = today.weekday() - target_weekday
        if days_back <= 0:  # Target day is in the future this week
            days_back += 7
        
        return today - timedelta(days=days_back)
    
    def _get_this_weekday(self, target_weekday: int) -> datetime:
        """Get this week's occurrence of a weekday"""
        today = datetime.now()
        days_ahead = target_weekday - today.weekday()
        
        return today + timedelta(days=days_ahead)
    
    def extract_date_info(self, user_input: str) -> Dict[str, Any]:
        """
        Extract comprehensive date information from user input
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with date information
        """
        result = {
            'type': 'unknown',
            'start_date': None,
            'end_date': None,
            'parsed_date': None,
            'is_range': False,
            'confidence': 0.0
        }
        
        user_lower = user_input.lower().strip()
        
        # Check for range indicators
        if any(word in user_lower for word in ['month', 'year', 'week', 'all events in', 'during']):
            date_range = self.parse_date_range(user_input)
            if date_range:
                result['type'] = 'date_range'
                result['start_date'] = date_range[0]
                result['end_date'] = date_range[1]
                result['is_range'] = True
                result['confidence'] = 0.9
                return result
        
        # Check for specific date
        parsed_date = self.parse_natural_date(user_input)
        if parsed_date:
            result['type'] = 'specific_date'
            result['parsed_date'] = parsed_date
            result['start_date'] = parsed_date
            result['end_date'] = parsed_date
            result['confidence'] = 0.8
            return result
        
        result['confidence'] = 0.0
        return result