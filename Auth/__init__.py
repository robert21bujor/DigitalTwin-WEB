"""
Unified Authentication System
============================

Consolidated authentication and user management system.

Structure:
- Auth/Core/              - Core authentication system
- Auth/User_management/   - User models, roles, and management
"""

# Re-export commonly used components for backward compatibility
try:
    from .Core.account_system import UserAccount, AccountType, Division
    from .User_management.user_models import User, UserRole
    from .User_management.auth_manager import auth_manager
except ImportError:
    # Graceful fallback during migration
    pass
