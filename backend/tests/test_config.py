"""Tests for application configuration."""

import pytest

from app.core.config import Settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_environment_is_development(self):
        """Default environment should be development."""
        settings = Settings()
        assert settings.environment == "development"

    def test_default_database_url(self):
        """Default database URL should be SQLite."""
        settings = Settings()
        assert "sqlite" in settings.database_url

    def test_app_version_is_set(self):
        """App version should be 1.0.0."""
        settings = Settings()
        assert settings.app_version == "1.0.0"

    def test_app_name_is_reportlift(self):
        """App name should be ReportLift."""
        settings = Settings()
        assert settings.app_name == "ReportLift"

    def test_log_level_is_valid(self):
        """Log level should be a valid logging level."""
        settings = Settings()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.log_level.upper() in valid_levels
