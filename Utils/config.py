"""
Configuration management for the Semantic Kernel AI Agent System
"""

import os
from typing import Dict, Any, Optional
import logging

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    import os
    from pathlib import Path
    
    # Get the project root directory (parent of Utils)
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    
    load_dotenv(env_path)
    logger = logging.getLogger(__name__)
    logger.info(f"Loaded environment variables from .env file: {env_path}")
except ImportError:
    # dotenv not installed, continue without it
    pass
except Exception as e:
    # .env file doesn't exist or has issues, continue without it
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not load .env file: {e}")

logger = logging.getLogger(__name__)

class Config:
    """Configuration management with environment variable and .env file support"""
    
    @staticmethod
    def get_azure_config() -> Dict[str, Any]:
        """Get Azure OpenAI configuration"""
        return {
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        }
    
    @staticmethod 
    def get_azure_openai_config() -> Dict[str, str]:
        """Get Azure OpenAI configuration (alias for backward compatibility)"""
        return {
            "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "api_base": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
            "model_name": os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4")
        }
    
    @staticmethod
    def get_supabase_config() -> Dict[str, Any]:
        """Get Supabase configuration"""
        return {
            "url": os.getenv("SUPABASE_URL"),
            "key": os.getenv("SUPABASE_ANON_KEY"),
            "service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        }
    
    @staticmethod
    def get_supabase_client():
        """Get Supabase client instance"""
        try:
            from supabase import create_client
            config = Config.get_supabase_config()
            service_key = config.get("service_role_key") or config["key"]
            return create_client(config["url"], service_key)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create Supabase client: {e}")
            return None
    
    @staticmethod
    def get_service_type() -> str:
        """Get AI service type"""
        return "azure"
    
    @staticmethod
    def is_fast_mode() -> bool:
        """Check if fast mode is enabled (skips heavy initialization)"""
        return os.getenv("FAST_MODE", "false").lower() in ("true", "1", "yes")
    
    @staticmethod
    def get_qdrant_config() -> Dict[str, Any]:
        """Get Qdrant vector database configuration"""
        return {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
            "collection_name": os.getenv("QDRANT_COLLECTION", "memory")
        }
    
    @staticmethod
    def get_logging_level() -> str:
        """Get logging level from environment"""
        return os.getenv("LOG_LEVEL", "INFO").upper()
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @staticmethod
    def is_memory_enabled() -> bool:
        """Check if memory system should be enabled"""
        return os.getenv("ENABLE_MEMORY", "true").lower() in ("true", "1", "yes")
    
    @staticmethod
    def get_google_config() -> Dict[str, Any]:
        """Get Google OAuth2 configuration for Gmail integration with validation"""
        
        # First try to load from credentials.json file
        credentials_file = "Memory/Config/credentials.json"
        if os.path.exists(credentials_file):
            try:
                import json
                with open(credentials_file, 'r') as f:
                    creds_data = json.load(f)
                
                # Check if it's the "installed" format (desktop app)
                if "installed" in creds_data:
                    installed_config = creds_data["installed"]
                    config = {
                        "client_id": installed_config.get("client_id"),
                        "client_secret": installed_config.get("client_secret"),
                        "project_id": installed_config.get("project_id"),
                        "auth_uri": installed_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                        "token_uri": installed_config.get("token_uri", "https://oauth2.googleapis.com/token"),
                        "redirect_uri": "http://localhost:3001/auth/gmail/callback"
                    }
                    logger.info(f"Loaded Google OAuth config from {credentials_file}")
                    logger.info(f"Using client_id: {config['client_id'][:20]}...")
                    return config
                
            except Exception as e:
                logger.warning(f"Failed to load credentials from {credentials_file}: {e}")
        
        # Fallback to environment variables
        config = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uri": "http://localhost:3001/auth/gmail/callback"
        }
        
        # Log configuration status (without revealing secrets)
        missing = []
        for key, value in config.items():
            if key in ["client_id", "client_secret", "project_id"] and not value:
                missing.append(key)
        
        if missing:
            logger.warning(f"Missing Google OAuth configuration: {missing}")
            logger.warning("Please check GOOGLE_OAUTH_SETUP.md for setup instructions")
        else:
            logger.info("Google OAuth configuration loaded successfully")
            
        return config
    
    @staticmethod
    def get_clickup_config() -> Dict[str, Any]:
        """Get ClickUp OAuth2 configuration"""
        config = {
            "client_id": os.getenv("CLICKUP_CLIENT_ID"),
            "client_secret": os.getenv("CLICKUP_CLIENT_SECRET"),
            "redirect_uri": os.getenv("CLICKUP_REDIRECT_URI", "http://localhost:3001/auth/clickup/callback"),
            "encryption_key": os.getenv("CLICKUP_ENCRYPTION_KEY")
        }
        
        # Log configuration status (without revealing secrets)
        missing = []
        for key, value in config.items():
            if key in ["client_id", "client_secret"] and not value:
                missing.append(key)
        
        if missing:
            logger.warning(f"Missing ClickUp OAuth configuration: {missing}")
            logger.warning("Please set CLICKUP_CLIENT_ID and CLICKUP_CLIENT_SECRET environment variables")
        else:
            logger.info("ClickUp OAuth configuration loaded successfully")
            
        return config
    
    @staticmethod
    def get_memory_config() -> Dict[str, Any]:
        """Get memory system configuration"""
        return {
            "gdrive_root_folder_id": os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID"),
            "gdrive_credentials_path": os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "Memory/Config/credentials.json"),
            "gdrive_token_path": os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "Authentication/token.json"),
            "qdrant_host": os.getenv("QDRANT_HOST", "localhost"),
            "qdrant_port": int(os.getenv("QDRANT_PORT", "6333")),
            "qdrant_api_key": os.getenv("QDRANT_API_KEY"),
            "cache_dir": ".cache/gdrive/gdrive_files",
            "sync_interval": int(os.getenv("MEMORY_SYNC_INTERVAL", "300")),
            "max_file_size": int(os.getenv("MEMORY_MAX_FILE_SIZE", "52428800")),
            "supported_extensions": [".pdf", ".docx", ".txt", ".md"],
            "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            "lazy_load": os.getenv("MEMORY_LAZY_LOAD", "true").lower() in ("true", "1", "yes")
        }
    
    @staticmethod
    def get_agent_folder_mapping() -> Dict[str, tuple]:
        """Get Google Drive folder to agent mapping"""
        return {
            # Existing Marketing departments
            "Executive": ("cmo", "executive-shared-memory", True),
            "Digital Marketing": ("digital", "digital-shared-memory", True),
            "Product Marketing": ("product", "product-shared-memory", True),
            "Content & Brand": ("content", "content-shared-memory", True),
            
            # New Business Development department
            "Business Development": ("business_dev", "business-dev-shared-memory", True),
            
            # New Operations department and its subdepartments
            "Operations": ("operations", "operations-shared-memory", True),
            "Operations/Client Success": ("client_success", "client-success-shared-memory", True),
            "Operations/Custom Reporting": ("custom_reporting", "custom-reporting-shared-memory", True),
            "Operations/Legal": ("legal", "legal-shared-memory", True),
            
            # Root folder for general documents
            "__root__": ("shared", "shared-memory", True)
        }
    
    @staticmethod
    def validate_config() -> bool:
        """Validate required configuration"""
        config = Config.get_azure_config()
        required_fields = ["api_key", "endpoint", "deployment_name"]
        
        for field in required_fields:
            if not config.get(field):
                return False
        
        return True
    
    @staticmethod
    def validate_supabase_config() -> bool:
        """Validate Supabase configuration"""
        config = Config.get_supabase_config()
        required_fields = ["url", "key"]
        
        for field in required_fields:
            if not config.get(field):
                return False
        
        return True
    
    @staticmethod
    def validate_memory_config() -> bool:
        """Validate memory system configuration"""
        config = Config.get_memory_config()
        required_fields = ["gdrive_root_folder_id", "gdrive_credentials_path"]
        
        for field in required_fields:
            if not config.get(field):
                return False
        
        return True
    
    @staticmethod
    def get_search_config() -> Dict[str, Any]:
        """Get hybrid search system configuration"""
        return {
            # Google OAuth and Service Account paths
            "oauth_client_secrets": os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS"),
            "service_account_credentials": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            "delegate_subject": os.getenv("GOOGLE_DELEGATE_SUBJECT"),
            
            # Search behavior
            "max_results": int(os.getenv("SEARCH_MAX_RESULTS", "25")),
            "max_workers": int(os.getenv("SEARCH_MAX_WORKERS", "2")),
            "parallel_search": os.getenv("SEARCH_PARALLEL", "true").lower() == "true",
            
            # Pagination
            "gmail_page_size": int(os.getenv("GMAIL_PAGE_SIZE", "50")),
            "drive_page_size": int(os.getenv("DRIVE_PAGE_SIZE", "100")),
            
            # Reranking parameters
            "recency_halflife_days": int(os.getenv("RECENCY_HALFLIFE_DAYS", "30")),
            "lexical_weight": float(os.getenv("LEXICAL_WEIGHT", "0.6")),
            "recency_weight": float(os.getenv("RECENCY_WEIGHT", "0.4")),
            "min_score_threshold": float(os.getenv("MIN_SCORE_THRESHOLD", "0.05")),
            
            # Language support
            "diacritic_insensitive": os.getenv("DIACRITIC_INSENSITIVE", "true").lower() == "true",
            "bilingual_support": os.getenv("BILINGUAL_SUPPORT", "true").lower() == "true"
        }
    
    @staticmethod
    def validate_search_config() -> bool:
        """Validate search system configuration"""
        config = Config.get_search_config()
        
        # Check if at least one auth method is configured
        has_oauth = config.get("oauth_client_secrets") and os.path.exists(config["oauth_client_secrets"])
        has_service_account = config.get("service_account_credentials") and os.path.exists(config["service_account_credentials"])
        
        if not (has_oauth or has_service_account):
            logger.warning("⚠️ No Google authentication configured for search")
            return False
        
        # Validate numeric parameters
        try:
            assert 1 <= config["max_results"] <= 1000, "max_results must be 1-1000"
            assert 1 <= config["max_workers"] <= 10, "max_workers must be 1-10"
            assert 1 <= config["recency_halflife_days"] <= 365, "recency_halflife_days must be 1-365"
            assert 0.0 <= config["lexical_weight"] <= 1.0, "lexical_weight must be 0.0-1.0"
            assert 0.0 <= config["recency_weight"] <= 1.0, "recency_weight must be 0.0-1.0"
        except (AssertionError, ValueError) as e:
            logger.error(f"❌ Invalid search configuration: {e}")
            return False
        
        return True
    
    @staticmethod
    def get_agent_roles() -> Dict[str, Dict[str, Any]]:
        """Get agent role definitions"""
        return {
            "product_marketing": {
                "PositioningAgent": {
                    "role": "Product Positioning Specialist",
                    "type": "companion",
                    "skills": ["positioning", "value_props", "differentiation"]
                },
                "PersonaAgent": {
                    "role": "Customer Persona Researcher", 
                    "type": "autonomous",
                    "skills": ["user_research", "segmentation", "personas"]
                },
                "GTMAgent": {
                    "role": "Go-to-Market Strategist",
                    "type": "companion", 
                    "skills": ["gtm_strategy", "launch_planning", "market_entry"]
                },
                "CompetitorAgent": {
                    "role": "Competitive Intelligence Analyst",
                    "type": "autonomous",
                    "skills": ["competitive_analysis", "market_research", "intelligence"]
                },
                "LaunchAgent": {
                    "role": "Product Launch Content Specialist",
                    "type": "companion",
                    "skills": ["launch_content", "messaging", "communications"]
                }
            },
            "managers": {
                "ProductMarketingManager": {
                    "role": "Product Marketing Manager",
                    "department": "product_marketing"
                }
            },
            "executives": {
                "CMO": {
                    "role": "Chief Marketing Officer",
                    "department": "executive"
                }
            }
        }
    
    @staticmethod
    def get_log_config() -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "Logs/MarketingSystem.log",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5
        } 