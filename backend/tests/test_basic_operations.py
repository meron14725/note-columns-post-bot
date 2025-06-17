"""Basic operations tests for PHASE1 quality assurance."""

import os
import py_compile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Test modules
CORE_MODULES = [
    "backend.batch.daily_process",
    "backend.app.services.json_generator",
    "backend.app.services.evaluator",
    "backend.app.services.scraper",
    "backend.app.services.twitter_bot",
    "backend.app.utils.database",
    "backend.app.utils.logger",
    "backend.app.utils.rate_limiter",
    "backend.app.models.article",
    "backend.app.models.evaluation",
    "backend.app.repositories.article_repository",
    "backend.app.repositories.evaluation_repository",
    "config.config",
]

BATCH_SCRIPTS = ["backend/batch/daily_process.py", "backend/batch/post_to_twitter.py"]


class TestImports:
    """Test successful imports of all core modules."""

    @pytest.mark.parametrize("module_name", CORE_MODULES)
    def test_module_import(self, module_name):
        """Test that core modules can be imported successfully."""
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

    def test_backend_package_import(self):
        """Test that backend package can be imported."""
        try:
            import backend

            assert hasattr(backend, "__path__")
        except ImportError as e:
            pytest.fail(f"Failed to import backend package: {e}")

    def test_config_package_import(self):
        """Test that config package can be imported."""
        try:
            import config

            assert hasattr(config, "__path__")
        except ImportError as e:
            pytest.fail(f"Failed to import config package: {e}")

    def test_specific_class_imports(self):
        """Test importing specific classes from modules."""
        test_imports = [
            ("backend.app.services.evaluator", "ArticleEvaluator"),
            ("backend.app.services.scraper", "NoteScraper"),
            ("backend.app.services.json_generator", "JSONGenerator"),
            ("backend.app.models.article", "Article"),
            ("backend.app.models.evaluation", "Evaluation"),
            ("backend.app.utils.database", "db_manager"),
        ]

        for module_name, class_name in test_imports:
            try:
                module = __import__(module_name, fromlist=[class_name])
                assert hasattr(module, class_name), (
                    f"{class_name} not found in {module_name}"
                )
            except ImportError as e:
                pytest.fail(f"Failed to import {class_name} from {module_name}: {e}")


class TestSyntaxValidation:
    """Test syntax validation of all Python files."""

    @pytest.mark.parametrize("script_path", BATCH_SCRIPTS)
    def test_batch_script_syntax(self, script_path):
        """Test that batch scripts have valid Python syntax."""
        try:
            py_compile.compile(script_path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {script_path}: {e}")

    def test_all_service_files_syntax(self):
        """Test syntax of all service files."""
        service_dir = Path("backend/app/services")
        if not service_dir.exists():
            pytest.skip("Services directory not found")

        python_files = list(service_dir.glob("*.py"))
        assert len(python_files) > 0, "No Python files found in services directory"

        for py_file in python_files:
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")

    def test_all_model_files_syntax(self):
        """Test syntax of all model files."""
        models_dir = Path("backend/app/models")
        if not models_dir.exists():
            pytest.skip("Models directory not found")

        python_files = list(models_dir.glob("*.py"))
        assert len(python_files) > 0, "No Python files found in models directory"

        for py_file in python_files:
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")


class TestDryRunExecution:
    """Test dry-run execution of batch processes."""

    @patch.dict(os.environ, {"DRY_RUN": "true"})
    def test_daily_process_dry_run(self):
        """Test dry-run execution of daily process."""
        # Mock external dependencies
        with (
            patch("backend.app.services.scraper.NoteScraper") as mock_scraper,
            patch("backend.app.services.evaluator.ArticleEvaluator") as mock_evaluator,
            patch("backend.app.services.json_generator.JSONGenerator") as mock_json_gen,
            patch("backend.app.utils.database.db_manager"),
        ):
            # Setup mocks
            mock_scraper_instance = MagicMock()
            mock_scraper.return_value = mock_scraper_instance
            mock_scraper_instance.collect_articles.return_value = []

            mock_evaluator_instance = MagicMock()
            mock_evaluator.return_value = mock_evaluator_instance
            mock_evaluator_instance.evaluate_articles.return_value = []

            mock_json_gen_instance = MagicMock()
            mock_json_gen.return_value = mock_json_gen_instance
            mock_json_gen_instance.generate_all_files.return_value = True

            # Try to import and initialize components without actual execution
            try:
                from backend.app.services.json_generator import JSONGenerator
                from backend.app.services.scraper import NoteScraper

                # Test instantiation (should not fail)
                scraper = NoteScraper()
                assert scraper is not None

                # Note: We don't test evaluator instantiation without API key
                # as it would raise ValueError - this is tested in error handling

                json_gen = JSONGenerator()
                assert json_gen is not None

            except Exception as e:
                pytest.fail(f"Dry-run execution failed: {e}")

    def test_configuration_loading(self):
        """Test that configuration files can be loaded."""
        try:
            from config.config import config

            # Basic configuration should be accessible
            assert hasattr(config, "urls_config")
            assert hasattr(config, "get_collection_settings")
            assert hasattr(config, "get_collection_urls")

        except Exception as e:
            pytest.fail(f"Configuration loading failed: {e}")

    def test_database_connection_dry_run(self):
        """Test database connection without actual operations."""
        try:
            from backend.app.utils.database import db_manager

            # Should be able to access db_manager without connection
            assert db_manager is not None

        except Exception as e:
            pytest.fail(f"Database manager access failed: {e}")

    def test_logger_initialization(self):
        """Test that logger can be initialized."""
        try:
            from backend.app.utils.logger import get_logger

            logger = get_logger(__name__)
            assert logger is not None
            assert hasattr(logger, "info")
            assert hasattr(logger, "error")
            assert hasattr(logger, "warning")

        except Exception as e:
            pytest.fail(f"Logger initialization failed: {e}")


class TestPackageStructure:
    """Test package structure and file organization."""

    def test_init_files_exist(self):
        """Test that all necessary __init__.py files exist."""
        required_init_files = [
            "backend/__init__.py",
            "backend/app/__init__.py",
            "backend/app/services/__init__.py",
            "backend/app/models/__init__.py",
            "backend/app/utils/__init__.py",
            "backend/app/repositories/__init__.py",
            "backend/batch/__init__.py",
            "config/__init__.py",
        ]

        for init_file in required_init_files:
            assert Path(init_file).exists(), f"Missing {init_file}"

    def test_pyproject_configuration(self):
        """Test that pyproject.toml has correct configuration."""
        pyproject_path = Path("pyproject.toml")
        assert pyproject_path.exists(), "pyproject.toml not found"

        # Read and basic validation
        content = pyproject_path.read_text()
        assert 'packages = ["backend", "config"]' in content
        assert "pytest" in content
        assert 'asyncio_mode = "auto"' in content

    def test_required_dependencies(self):
        """Test that required dependencies are available."""
        required_packages = [
            ("requests", "requests"),
            ("beautifulsoup4", "bs4"),
            ("groq", "groq"),
            ("httpx", "httpx"),
            ("pytest", "pytest"),
        ]

        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
            except ImportError:
                pytest.fail(f"Required package {package_name} not available")

        # Test pytest-asyncio plugin availability (optional)
        try:
            import importlib.util

            pytest_asyncio_spec = importlib.util.find_spec("pytest_asyncio")
            if pytest_asyncio_spec is None:
                pytest.skip(
                    "pytest-asyncio plugin not available, but tests can still run"
                )
        except ImportError:
            pytest.skip("pytest-asyncio plugin not available, but tests can still run")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
