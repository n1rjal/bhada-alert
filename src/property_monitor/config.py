"""Configuration management using pydantic-settings for type-safe, validated configuration."""

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with automatic validation and type conversion."""

    # Application settings
    app_name: str = Field(default="PropertyMonitor", description="Application name")
    environment: str = Field(
        default="production",
        pattern="^(development|staging|production)$",
        description="Environment mode",
    )
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )

    # Scraping settings
    scrape_interval_seconds: int = Field(
        default=900, ge=60, le=3600, description="Interval between scraping runs (15 min default)"
    )
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    request_timeout: float = Field(
        default=30.0, ge=5.0, le=120.0, description="HTTP request timeout"
    )
    max_price: int = Field(default=10000, ge=0, description="Maximum price filter (Rs)")
    time_window_hours: int = Field(
        default=24, ge=1, le=168, description="Time window for new property detection"
    )

    # Storage settings
    data_dir: Path = Field(default=Path("./data"), description="Data storage directory")
    backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_retention_days: int = Field(
        default=7, ge=1, le=365, description="Backup retention period"
    )

    # Discord webhook
    discord_webhook_url: SecretStr = Field(..., description="Discord webhook URL (required)")
    discord_rate_limit_per_minute: int = Field(
        default=25, ge=1, le=30, description="Discord rate limit"
    )

    # URLs to monitor (JSON array in env var)
    property_urls: list[str] = Field(
        default_factory=list, description="List of property URLs to monitor"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="PROPMON_",
        # Allow JSON parsing for lists
        json_schema_extra={"env_parse_json": True},
    )

    @field_validator("data_dir")
    @classmethod
    def create_data_dir(cls, v: Path) -> Path:
        """Create data directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("property_urls", mode="before")
    @classmethod
    def parse_property_urls(cls, v: Any) -> list[str]:
        """Parse property URLs from JSON string or list."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not JSON, treat as single URL
                return [v] if v else []
        elif isinstance(v, list):
            return v
        return []


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (useful for testing)."""
    global _settings
    _settings = None
