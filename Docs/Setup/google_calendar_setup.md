# Gcalendar Module

**Modular Google Calendar Integration for AI Agents**

## 📁 Structure

```
Gcalendar/
├── __init__.py          # Module exports and version info
├── calendar_manager.py  # 🎯 Main orchestrator (USE THIS!)
├── detector.py          # 🔍 Request detection and classification
├── handler.py           # 🔧 Google Calendar API calls
├── formatter.py         # 📝 Response formatting
└── README.md           # This file
```

## 🚀 Quick Start

```python
from Gcalendar import CalendarManager

# Initialize
calendar_manager = CalendarManager()

# Process user requests
response = await calendar_manager.process_request(
    user_input="What's on my calendar today?",
    user_id="user-id-here"
)
```

## 🧩 Component Details

### CalendarManager (Main Interface)
- **Purpose**: Orchestrates the entire flow
- **Methods**: 
  - `process_request()` - Main method to handle calendar requests
  - `is_calendar_request()` - Quick check if input is calendar-related
  - `is_available()` - Check if calendar service is working

### CalendarDetector
- **Purpose**: Detects and classifies calendar requests
- **Features**:
  - Keyword matching for calendar terms
  - Request type classification (today, tomorrow, upcoming, search)
  - Parameter extraction from natural language

### CalendarHandler
- **Purpose**: Makes actual Google Calendar API calls
- **Features**:
  - Handles different request types
  - Date parsing and validation
  - Error handling and retry logic

### CalendarFormatter
- **Purpose**: Formats calendar data into user-friendly responses
- **Features**:
  - Rich formatting with emojis
  - Date grouping for upcoming events
  - Time extraction and display
  - Error message formatting

## 📝 Supported Request Types

| Type | Examples | Description |
|------|----------|-------------|
| **Today** | "What's today?", "Today's schedule" | Shows today's events |
| **Tomorrow** | "Tomorrow's meetings", "What do I have tomorrow?" | Shows tomorrow's events |
| **Upcoming** | "This week", "Next 7 days" | Shows upcoming events |
| **Search** | "Find meeting with John", "Search calendar" | Searches for specific events |
| **General** | "My calendar", "Schedule" | Default calendar view |

## 🔧 Integration

This module is integrated into `AgentUI/communication_manager.py`:

```python
# Import the manager
from Gcalendar import CalendarManager

# Initialize in constructor
self.calendar_manager = CalendarManager()

# Use in message processing
calendar_result = await self.calendar_manager.process_request(message, user_id)
if calendar_result:
    return calendar_result
```

## ✅ Benefits

- **🔍 Clean Separation**: Each file has a single responsibility
- **🔧 Easy Testing**: Each component can be tested independently  
- **📈 Maintainable**: Changes are isolated to specific files
- **🚀 Reusable**: Can be imported and used in other parts of the system
- **📝 Self-Documenting**: Clear structure and naming

## 🎯 Usage in Communication Manager

The calendar integration now works like this:

1. **Detection**: `CalendarDetector` scans for calendar keywords
2. **Classification**: Determines request type and extracts parameters
3. **Handling**: `CalendarHandler` calls Google Calendar API
4. **Formatting**: `CalendarFormatter` creates user-friendly response
5. **Return**: Formatted response sent back to user

All of this happens **before** the message reaches the AI agent, ensuring fast, accurate calendar responses.