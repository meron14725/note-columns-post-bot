"""Test configuration loading."""

from pathlib import Path

import pytest


def test_config_imports():
    """Test that configuration can be imported without errors."""
    try:
        import sys

        # Add project root to path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from config.config import config

        assert config is not None
    except ImportError as e:
        pytest.fail(f"Failed to import config: {e}")


def test_project_structure():
    """Test that required project directories exist."""
    project_root = Path(__file__).parent.parent.parent

    required_dirs = [
        "backend/app",
        "backend/batch",
        "config",
        "docs",
        ".github/workflows",
    ]

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        assert full_path.exists(), f"Required directory missing: {dir_path}"


def test_required_files():
    """Test that required configuration files exist."""
    project_root = Path(__file__).parent.parent.parent

    required_files = [
        "pyproject.toml",
        "README.md",
        ".gitignore",
        ".env.example",
        "config/config.py",
        "config/urls_config.json",
        "config/prompt_settings.json",
        "config/posting_schedule.json",
    ]

    for file_path in required_files:
        full_path = project_root / file_path
        assert full_path.exists(), f"Required file missing: {file_path}"
