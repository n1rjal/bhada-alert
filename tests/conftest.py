"""Pytest fixtures and configuration."""

from pathlib import Path

import pytest
import structlog

from property_monitor.adapters.storage.sqlite_store import SQLiteStorage
from property_monitor.config import reset_settings
from property_monitor.logging_config import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging() -> None:
    """Setup logging for tests."""
    setup_logging(log_level="INFO", environment="development")


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset configuration singleton between tests."""
    reset_settings()


@pytest.fixture
def test_logger() -> structlog.stdlib.BoundLogger:
    """Get test logger."""
    return structlog.get_logger("test")


@pytest.fixture
def temp_storage(tmp_path: Path, test_logger: structlog.stdlib.BoundLogger) -> SQLiteStorage:
    """Create temporary SQLite storage for testing."""
    db_path = tmp_path / "test.db"
    return SQLiteStorage(
        db_path=db_path, backup_enabled=False, backup_retention_days=7, logger=test_logger
    )


@pytest.fixture
def sample_html_dir() -> Path:
    """Get directory containing sample HTML fixtures."""
    return Path(__file__).parent / "fixtures" / "sample_html"
