"""
Agent Configuration Module
=========================

Configuration utilities for agent communication infrastructure.
Provides centralized configuration management for production deployment.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for individual agents"""
    
    # Agent identity
    agent_id: str
    user_name: str
    role: str
    department: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Memory configuration
    memory_config: Dict[str, Any] = field(default_factory=dict)
    gdrive_config_path: Optional[str] = None
    vector_store_url: str = "http://localhost:6333"
    
    # Communication settings
    heartbeat_interval: int = 30
    message_timeout: int = 60
    max_retries: int = 3
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.agent_id.startswith('agent.'):
            raise ValueError("Agent ID must start with 'agent.'")
        
        if not self.user_name:
            raise ValueError("User name is required")
        
        if not self.role:
            raise ValueError("Role is required")
        
        # Setup Redis URL with authentication
        if self.redis_password:
            # Parse existing URL and add password
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.redis_url)
            if '@' not in parsed.netloc:
                netloc = f":{self.redis_password}@{parsed.netloc}"
                self.redis_url = urlunparse(parsed._replace(netloc=netloc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "agent_id": self.agent_id,
            "user_name": self.user_name,
            "role": self.role,
            "department": self.department,
            "capabilities": self.capabilities,
            "redis_url": self.redis_url,
            "redis_password": self.redis_password,
            "redis_db": self.redis_db,
            "memory_config": self.memory_config,
            "gdrive_config_path": self.gdrive_config_path,
            "vector_store_url": self.vector_store_url,
            "heartbeat_interval": self.heartbeat_interval,
            "message_timeout": self.message_timeout,
            "max_retries": self.max_retries,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "custom_settings": self.custom_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create configuration from dictionary"""
        # Filter out None values and unknown keys
        valid_keys = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys and v is not None}
        
        return cls(**filtered_data)
    
    @classmethod
    def from_file(cls, config_file: str) -> 'AgentConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
            raise
    
    def save_to_file(self, config_file: str) -> None:
        """Save configuration to JSON file"""
        try:
            config_data = self.to_dict()
            
            # Create directory if it doesn't exist
            Path(config_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Configuration saved to {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
            raise


def create_agent_config(
    agent_id: str,
    user_name: str,
    role: str,
    department: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    redis_url: Optional[str] = None,
    **kwargs
) -> AgentConfig:
    """
    Create agent configuration with defaults
    
    Args:
        agent_id: Agent identifier
        user_name: User name
        role: Agent role
        department: Department (optional)
        capabilities: List of capabilities
        redis_url: Redis URL (uses environment or default)
        **kwargs: Additional configuration options
        
    Returns:
        AgentConfig instance
    """
    # Get Redis URL from environment or use default
    if not redis_url:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Default capabilities based on role
    if capabilities is None:
        capabilities = get_default_capabilities(role)
    
    # Create configuration
    config = AgentConfig(
        agent_id=agent_id,
        user_name=user_name,
        role=role,
        department=department,
        capabilities=capabilities,
        redis_url=redis_url,
        **kwargs
    )
    
    # Apply environment-specific settings
    apply_environment_settings(config)
    
    return config


def get_default_capabilities(role: str) -> List[str]:
    """Get default capabilities for a role"""
    role_capabilities = {
        "cmo": [
            "strategic_planning",
            "team_management",
            "budget_oversight",
            "roadmap_creation",
            "stakeholder_communication"
        ],
        "marketing_manager": [
            "campaign_management",
            "team_coordination",
            "performance_analysis",
            "content_strategy",
            "budget_management"
        ],
        "content_agent": [
            "content_creation",
            "content_editing",
            "seo_optimization",
            "social_media_management",
            "brand_messaging"
        ],
        "seo_agent": [
            "keyword_research",
            "technical_seo",
            "content_optimization",
            "link_building",
            "seo_analysis"
        ],
        "product_manager": [
            "product_planning",
            "feature_specification",
            "user_research",
            "roadmap_management",
            "stakeholder_coordination"
        ],
        "default": [
            "task_execution",
            "communication",
            "reporting"
        ]
    }
    
    return role_capabilities.get(role.lower(), role_capabilities["default"])


def apply_environment_settings(config: AgentConfig) -> None:
    """Apply environment-specific configuration settings"""
    
    # Redis settings from environment
    if os.getenv('REDIS_PASSWORD'):
        config.redis_password = os.getenv('REDIS_PASSWORD')
    
    if os.getenv('REDIS_DB'):
        config.redis_db = int(os.getenv('REDIS_DB'))
    
    # Memory settings from environment
    if os.getenv('GDRIVE_CONFIG_PATH'):
        config.gdrive_config_path = os.getenv('GDRIVE_CONFIG_PATH')
    
    if os.getenv('VECTOR_STORE_URL'):
        config.vector_store_url = os.getenv('VECTOR_STORE_URL')
    
    # Logging settings from environment
    if os.getenv('LOG_LEVEL'):
        config.log_level = os.getenv('LOG_LEVEL')
    
    if os.getenv('LOG_FILE'):
        config.log_file = os.getenv('LOG_FILE')
    
    # Communication settings from environment
    if os.getenv('HEARTBEAT_INTERVAL'):
        config.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL'))
    
    if os.getenv('MESSAGE_TIMEOUT'):
        config.message_timeout = int(os.getenv('MESSAGE_TIMEOUT'))


def load_multi_agent_config(config_file: str) -> Dict[str, AgentConfig]:
    """
    Load configuration for multiple agents from a single file
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Dictionary mapping agent_id to AgentConfig
    """
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        agents = {}
        
        # Handle different config file formats
        if 'agents' in data:
            # Multi-agent format
            for agent_data in data['agents']:
                config = AgentConfig.from_dict(agent_data)
                agents[config.agent_id] = config
        else:
            # Single agent format
            config = AgentConfig.from_dict(data)
            agents[config.agent_id] = config
        
        logger.info(f"Loaded configuration for {len(agents)} agents")
        return agents
        
    except Exception as e:
        logger.error(f"Failed to load multi-agent config from {config_file}: {e}")
        raise


def create_startup_config() -> Dict[str, AgentConfig]:
    """
    Create a default configuration for a startup team
    
    Returns:
        Dictionary of agent configurations
    """
    configs = {}
    
    # CMO Agent
    configs['agent.user1'] = create_agent_config(
        agent_id='agent.user1',
        user_name='user1',
        role='cmo',
        department='executive',
        capabilities=[
            'strategic_planning',
            'team_management',
            'budget_oversight',
            'roadmap_creation',
            'stakeholder_communication'
        ]
    )
    
    # Marketing Manager
    configs['agent.sarah'] = create_agent_config(
        agent_id='agent.sarah',
        user_name='sarah',
        role='marketing_manager',
        department='marketing',
        capabilities=[
            'campaign_management',
            'team_coordination',
            'performance_analysis',
            'content_strategy'
        ]
    )
    
    # Content Agent
    configs['agent.alex'] = create_agent_config(
        agent_id='agent.alex',
        user_name='alex',
        role='content_agent',
        department='marketing',
        capabilities=[
            'content_creation',
            'content_editing',
            'seo_optimization',
            'social_media_management'
        ]
    )
    
    # SEO Agent
    configs['agent.taylor'] = create_agent_config(
        agent_id='agent.taylor',
        user_name='taylor',
        role='seo_agent',
        department='marketing',
        capabilities=[
            'keyword_research',
            'technical_seo',
            'content_optimization',
            'seo_analysis'
        ]
    )
    
    # Product Manager
    configs['agent.jordan'] = create_agent_config(
        agent_id='agent.jordan',
        user_name='jordan',
        role='product_manager',
        department='product',
        capabilities=[
            'product_planning',
            'feature_specification',
            'user_research',
            'roadmap_management'
        ]
    )
    
    return configs


def save_startup_config(config_file: str = "agent_configs.json") -> None:
    """
    Save startup configuration to file
    
    Args:
        config_file: Path to save configuration
    """
    try:
        configs = create_startup_config()
        
        # Convert to serializable format
        config_data = {
            "agents": [config.to_dict() for config in configs.values()],
            "created_at": "2024-01-01T00:00:00Z",
            "version": "1.0.0"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Startup configuration saved to {config_file}")
        
    except Exception as e:
        logger.error(f"Failed to save startup config: {e}")
        raise


def setup_logging(config: AgentConfig) -> None:
    """
    Setup logging for an agent based on configuration
    
    Args:
        config: Agent configuration
    """
    # Create logger
    logger_name = f"agent.{config.agent_id}"
    agent_logger = logging.getLogger(logger_name)
    
    # Set log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    agent_logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        f'%(asctime)s - {config.agent_id} - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    agent_logger.addHandler(console_handler)
    
    # File handler if specified
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(formatter)
        agent_logger.addHandler(file_handler)
    
    # Prevent duplicate logs
    agent_logger.propagate = False
    
    logger.info(f"Logging configured for {config.agent_id}")


# Environment detection utilities

def is_development() -> bool:
    """Check if running in development environment"""
    return os.getenv('ENVIRONMENT', 'development').lower() == 'development'


def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv('ENVIRONMENT', 'development').lower() == 'production'


def get_environment() -> str:
    """Get current environment"""
    return os.getenv('ENVIRONMENT', 'development').lower()


def get_redis_url() -> str:
    """Get Redis URL from environment with fallback"""
    if is_production():
        # Production Redis URL (required)
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL environment variable required in production")
        return redis_url
    else:
        # Development Redis URL with fallback
        return os.getenv('REDIS_URL', 'redis://localhost:6379')


def get_config_file_path() -> str:
    """Get configuration file path based on environment"""
    if is_production():
        return os.getenv('AGENT_CONFIG_FILE', '/app/config/agent_configs.json')
    else:
        return os.getenv('AGENT_CONFIG_FILE', 'agent_configs.json')


# Configuration validation

def validate_config(config: AgentConfig) -> List[str]:
    """
    Validate agent configuration
    
    Args:
        config: Agent configuration to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Basic validation
    if not config.agent_id or not config.agent_id.startswith('agent.'):
        errors.append("Invalid agent_id format")
    
    if not config.user_name:
        errors.append("user_name is required")
    
    if not config.role:
        errors.append("role is required")
    
    # Redis validation
    if not config.redis_url:
        errors.append("redis_url is required")
    
    # Production-specific validation
    if is_production():
        if not config.redis_password:
            errors.append("redis_password is required in production")
        
        if not config.log_file:
            errors.append("log_file is required in production")
    
    return errors


def validate_multi_agent_config(configs: Dict[str, AgentConfig]) -> Dict[str, List[str]]:
    """
    Validate multiple agent configurations
    
    Args:
        configs: Dictionary of agent configurations
        
    Returns:
        Dictionary mapping agent_id to validation errors
    """
    all_errors = {}
    
    for agent_id, config in configs.items():
        errors = validate_config(config)
        if errors:
            all_errors[agent_id] = errors
    
    # Check for duplicate agent IDs
    agent_ids = [config.agent_id for config in configs.values()]
    if len(agent_ids) != len(set(agent_ids)):
        for agent_id in set(agent_ids):
            if agent_ids.count(agent_id) > 1:
                if agent_id not in all_errors:
                    all_errors[agent_id] = []
                all_errors[agent_id].append("Duplicate agent_id")
    
    return all_errors 