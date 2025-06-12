"""Simple tests for basic project validation."""

from pathlib import Path


def test_project_structure():
    """Test that required project directories exist."""
    project_root = Path(__file__).parent.parent.parent
    
    required_dirs = [
        "backend",
        "config", 
        "docs",
        ".github"
    ]
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        assert full_path.exists(), f"Required directory missing: {dir_path}"


def test_required_files():
    """Test that required files exist."""
    project_root = Path(__file__).parent.parent.parent
    
    required_files = [
        "pyproject.toml",
        "README.md",
        ".gitignore",
        ".env.example"
    ]
    
    for file_path in required_files:
        full_path = project_root / file_path
        assert full_path.exists(), f"Required file missing: {file_path}"


def test_python_files_syntax():
    """Test that main Python files have valid syntax."""
    project_root = Path(__file__).parent.parent.parent
    
    python_files = [
        "config/config.py",
        "backend/app/models/article.py"
    ]
    
    for file_path in python_files:
        full_path = project_root / file_path
        if full_path.exists():
            # Try to compile the Python file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            try:
                compile(content, str(full_path), 'exec')
            except SyntaxError as e:
                assert False, f"Syntax error in {file_path}: {e}"