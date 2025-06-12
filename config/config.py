"""Application configuration module."""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
BACKEND_DIR = PROJECT_ROOT / "backend"
DOCS_DIR = PROJECT_ROOT / "docs"

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "database" / "entertainment_columns.db"))

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# GitHub configuration
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "")
GITHUB_PAGES_URL = os.getenv("GITHUB_PAGES_URL", "")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(BACKEND_DIR / "logs" / "app.log"))

# Output directories
OUTPUT_DIR = BACKEND_DIR / "output"
LOGS_DIR = BACKEND_DIR / "logs"
JSON_DATA_DIR = DOCS_DIR / "data"


def load_json_config(filename: str) -> Dict[str, Any]:
    """Load JSON configuration file.
    
    Args:
        filename: Name of the JSON file (with .json extension)
        
    Returns:
        Dictionary containing configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    config_path = CONFIG_DIR / filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_urls_config() -> Dict[str, Any]:
    """Get URLs configuration."""
    return load_json_config("urls_config.json")


def get_prompt_settings() -> Dict[str, Any]:
    """Get AI prompt settings."""
    return load_json_config("prompt_settings.json")


def get_posting_schedule() -> Dict[str, Any]:
    """Get posting schedule configuration."""
    return load_json_config("posting_schedule.json")


# Validation functions
def validate_required_env_vars() -> None:
    """Validate that required environment variables are set.
    
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = [
        ("GROQ_API_KEY", GROQ_API_KEY),
    ]
    
    optional_twitter_vars = [
        ("TWITTER_API_KEY", TWITTER_API_KEY),
        ("TWITTER_API_SECRET", TWITTER_API_SECRET),
        ("TWITTER_ACCESS_TOKEN", TWITTER_ACCESS_TOKEN),
        ("TWITTER_ACCESS_TOKEN_SECRET", TWITTER_ACCESS_TOKEN_SECRET),
    ]
    
    missing_vars = []
    
    # Check required variables
    for var_name, var_value in required_vars:
        if not var_value:
            missing_vars.append(var_name)
    
    # Check if all Twitter variables are set together (if any is set)
    twitter_vars_set = [bool(var_value) for _, var_value in optional_twitter_vars]
    if any(twitter_vars_set) and not all(twitter_vars_set):
        missing_twitter = [var_name for var_name, var_value in optional_twitter_vars if not var_value]
        missing_vars.extend(missing_twitter)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


def ensure_directories() -> None:
    """Ensure required directories exist."""
    directories = [
        OUTPUT_DIR,
        LOGS_DIR,
        JSON_DATA_DIR,
        JSON_DATA_DIR / "archives",
        BACKEND_DIR / "database",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Configuration constants
DEFAULT_CONFIG = {
    "max_articles_per_day": 100,
    "evaluation_batch_size": 10,
    "request_timeout": 30,
    "max_retries": 3,
    "backup_retention_days": 30,
}


class Config:
    """Configuration class for easy access to settings."""
    
    def __init__(self) -> None:
        """Initialize configuration."""
        self.database_path = DATABASE_PATH
        self.groq_api_key = GROQ_API_KEY
        self.twitter_credentials = {
            "api_key": TWITTER_API_KEY,
            "api_secret": TWITTER_API_SECRET,
            "access_token": TWITTER_ACCESS_TOKEN,
            "access_token_secret": TWITTER_ACCESS_TOKEN_SECRET,
            "bearer_token": TWITTER_BEARER_TOKEN,
        }
        self.github_repo_url = GITHUB_REPO_URL
        self.github_pages_url = GITHUB_PAGES_URL
        self.log_level = LOG_LEVEL
        self.log_file_path = LOG_FILE_PATH
        
        # Load JSON configurations
        try:
            self.urls_config = get_urls_config()
            self.prompt_settings = get_prompt_settings()
            self.posting_schedule = get_posting_schedule()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load configuration: {e}")
            self.urls_config = {}
            self.prompt_settings = {}
            self.posting_schedule = {}
    
    @property
    def has_twitter_credentials(self) -> bool:
        """Check if Twitter credentials are available."""
        return all(self.twitter_credentials.values())
    
    @property
    def has_groq_credentials(self) -> bool:
        """Check if Groq credentials are available."""
        return bool(self.groq_api_key)


# Global configuration instance
config = Config()