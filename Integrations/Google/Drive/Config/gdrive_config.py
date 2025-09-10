"""
Google Drive Configuration Loader
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_gdrive_config() -> Dict[str, Any]:
    """Load Google Drive configuration from config file"""
    try:
        config_path = Path(__file__).parent / "gdrive_config.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Google Drive config: {e}")
        return {}


def get_gdrive_root_folder_id() -> str:
    """Get the root folder ID for Google Drive"""
    config = load_gdrive_config()
    return config.get('gdrive_root_folder_id', '')


def get_gdrive_credentials_path() -> str:
    """Get the path to Google Drive credentials file"""
    config = load_gdrive_config()
    return config.get('gdrive_credentials_path', '')


def is_gdrive_setup_complete() -> bool:
    """Check if Google Drive setup is complete"""
    config = load_gdrive_config()
    return config.get('setup_complete', False) 