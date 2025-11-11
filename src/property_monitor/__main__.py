"""Main entry point for property monitor."""

import random
import signal
import sys
import time
import logging


from property_monitor.adapters.notifiers.discord import DiscordNotifier
from property_monitor.adapters.storage.sqlite_store import SQLiteStorage
from property_monitor.config import get_settings
from property_monitor.logging_config import get_logger, setup_logging
from property_monitor.services.monitor_service import MonitorService
from property_monitor.adapters.scrapers import scrappers


class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM/SIGINT."""

    def __init__(self) -> None:
        """Initialize shutdown handler."""
        self.shutdown_requested = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, frame: object) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        print(f"\n🛑 Received {signal_name}. Shutting down gracefully...")
        self.shutdown_requested = True

    def should_continue(self) -> bool:
        """
        Check if service should continue running.

        Returns:
            True if should continue, False if shutdown requested
        """
        return not self.shutdown_requested


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Load configuration

    try:
        settings = get_settings()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return 1

    setup_logging(log_level=settings.log_level, environment=settings.environment)
    logger = get_logger(__name__)
    logger.info(
        "service_starting",
        app_name=settings.app_name,
        environment=settings.environment,
        version="1.0.0",
    )

    # Initialize components with dependency injection
    try:
        service_init_kwargs = dict(
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )

        scrapers = [
            scrapper_class(**service_init_kwargs)
            for scrapper_class in scrappers  # noqa
        ]

        notifier = DiscordNotifier(
            webhook_url=settings.discord_webhook_url.get_secret_value(),
            rate_limit_per_minute=settings.discord_rate_limit_per_minute,
            logger=logger,
        )

        storage = SQLiteStorage(
            db_path=settings.data_dir / "properties.db",
            backup_enabled=settings.backup_enabled,
            backup_retention_days=settings.backup_retention_days,
            logger=logger,
        )

        monitor = MonitorService(
            scrapers=scrapers,
            notifier=notifier,
            storage=storage,
            max_price=settings.max_price,
            time_window_hours=settings.time_window_hours,
            logger=logger,
        )

    except Exception as e:
        logger.error("initialization_failed", error=str(e), exc_info=True)
        return 1

    # Graceful shutdown handler
    shutdown = GracefulShutdown()

    # Main monitoring loop
    try:
        iteration = 0
        while shutdown.should_continue():
            iteration += 1
            logger.info(
                "monitoring_cycle_start",
                iteration=iteration,
                interval_seconds=settings.scrape_interval_seconds,
            )

            try:
                stats = monitor.check_properties()

                # Log statistics
                print(f"\n{stats}")

                # Create backup periodically (every 10 iterations)
                if iteration % 10 == 0 and settings.backup_enabled:
                    backup_path = storage.backup()
                    if backup_path:
                        logger.info("periodic_backup_created", path=str(backup_path))

            except Exception as e:
                logger.error("monitoring_error", error=str(e), exc_info=True)

            # Sleep with randomization (14-16 minutes for 15-minute interval)
            # This prevents detection of automated patterns
            if shutdown.should_continue():
                variance = random.uniform(0.93, 1.07)  # ±7% variance
                sleep_seconds = int(settings.scrape_interval_seconds * variance)

                logger.info("sleeping", seconds=sleep_seconds)

                # Sleep in 1-second intervals to allow for quick shutdown
                for _ in range(sleep_seconds):
                    if not shutdown.should_continue():
                        break
                    time.sleep(1)

        logger.info("shutdown_graceful")
        print("\n✅ Shutdown complete. State saved.")
        return 0

    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        print("\n✅ Interrupted. Shutting down gracefully...")
        return 0

    except Exception as e:
        logger.error("service_error", error=str(e), exc_info=True)
        print(f"\n❌ Service error: {e}")
        return 1

    finally:
        logger.info("service_stopped")


if __name__ == "__main__":
    sys.exit(main())
