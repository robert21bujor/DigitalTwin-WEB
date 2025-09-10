"""
Gmail Integration Package
Provides Gmail API integration for the Digital Twin platform
"""

try:
    from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
    from Integrations.Google.Gmail.gmail_service import EmailData
    from Integrations.Google.Gmail.document_service import document_service
    from Integrations.Google.Gmail.gmail_database import gmail_database
except ImportError:
    # Fallback imports with path adjustment
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    from Integrations.Google.Gmail.gmail_auth import gmail_auth_service
    from Integrations.Google.Gmail.gmail_service import EmailData
    from Integrations.Google.Gmail.document_service import document_service
    from Integrations.Google.Gmail.gmail_database import gmail_database

# Import gmail_manager separately to avoid circular import
try:
    from Integrations.Google.Gmail.gmail_manager import GmailIntegrationManager
    gmail_manager = GmailIntegrationManager()
except ImportError:
    gmail_manager = None

__all__ = [
    'gmail_auth_service',
    'EmailData',
    'document_service',
    'gmail_database',
    'gmail_manager'
] 