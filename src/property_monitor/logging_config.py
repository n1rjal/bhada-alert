"""Structured logging configuration using structlog."""

import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO", environment: str = "production") -> None:
    """
    Configure structlog with environment-specific settings.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment mode (development, staging, production)
    """
    # Configure standard library logging (for third-party libraries)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Shared processors for all environments
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Environment-specific output format
    if environment == "development":
        # Human-readable colored output for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.better_tracebacks)
        ]
    else:
        # JSON output for production (easy to parse by log aggregators)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound logger with structured logging capabilities
    """
    return structlog.get_logger(name)
