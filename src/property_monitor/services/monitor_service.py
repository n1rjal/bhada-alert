"""Core monitoring service with dependency injection."""

import time
from dataclasses import dataclass
from typing import List

import structlog

from property_monitor.adapters.notifiers.base import Notifier
from property_monitor.adapters.scrapers.base import PropertyScraper
from property_monitor.adapters.storage.base import Storage
from property_monitor.domain.exceptions import ScraperError
from property_monitor.domain.models import MonitorStats, Property


@dataclass
class MonitorService:
    """
    Core monitoring service coordinating scraping, storage, and notifications.

    Uses dependency injection for testability and loose coupling.
    """

    scrapers: List[PropertyScraper]
    notifier: Notifier
    storage: Storage
    max_price: int
    time_window_hours: int
    logger: structlog.stdlib.BoundLogger

    def _is_within_budget(self, property_data: Property) -> bool:
        """
        Check if property is within budget.

        Args:
            property_data: Property to check

        Returns:
            True if price <= max_price, False otherwise
        """
        return property_data.price <= self.max_price

    def _is_recent(self, property_data: Property) -> bool:
        """
        Check if property was posted recently (within time window).

        Args:
            property_data: Property to check

        Returns:
            True if posted within time window, False if unknown or too old
        """
        if property_data.posted_minutes_ago is None:
            # If no timestamp, assume it might be recent (conservative approach)
            return True

        time_window_minutes = self.time_window_hours * 60
        return property_data.posted_minutes_ago <= time_window_minutes

    def _should_notify(self, property_data: Property) -> bool:
        """
        Determine if we should send notification for this property.

        Criteria:
        1. Property is new or price changed (not in storage or price differs)
        2. Property is within budget
        3. Property was posted recently (within time window)

        Args:
            property_data: Property to check

        Returns:
            True if should notify, False otherwise
        """
        # Must be within budget
        if not self._is_within_budget(property_data):
            return False

        # Must be new or updated
        if not self.storage.is_new_or_updated(property_data):
            return False

        # Must be recent (or timestamp unknown)
        if not self._is_recent(property_data):
            self.logger.info(
                "property_too_old",
                property_id=property_data.property_id,
                posted_minutes_ago=property_data.posted_minutes_ago,
            )
            return False

        return True

    def check_properties(self) -> MonitorStats:
        """
        Check properties from URLs and send notifications for new ones.

        Args:
            urls: List of URLs to scrape

        Returns:
            MonitorStats with results of the check
        """
        start_time = time.time()
        stats = MonitorStats()

        # Check if this is the first run (initialization)
        is_first_run = not self.storage.is_initialized()

        if is_first_run:
            self.logger.info("first_run_initialization", mode="baseline")

        try:
            # Scrape properties from URL
            for scrapper in self.scrapers:
                properties = scrapper.scrape()
                stats.total_properties += len(properties)

                # Process each property
                for prop in properties:
                    # Check if within budget
                    if self._is_within_budget(prop):
                        stats.within_budget += 1

                    # On first run, just save everything without notifications
                    if is_first_run:
                        self.storage.save(prop)
                        continue

                    # Subsequent runs: check if should notify
                    if self._should_notify(prop):
                        stats.new_properties += 1

                        # Send notification
                        try:
                            if self.notifier.notify(prop):
                                stats.notifications_sent += 1
                                self.logger.info(
                                    "notification_sent",
                                    property_id=prop.property_id,
                                    price=prop.price,
                                    title=prop.title[:50],
                                )
                            else:
                                self.logger.warning(
                                    "notification_failed",
                                    property_id=prop.property_id,
                                )
                        except Exception as e:
                            stats.errors += 1
                            self.logger.error(
                                "notification_error",
                                property_id=prop.property_id,
                                error=str(e),
                            )

                        # Save to storage
                        self.storage.save(prop)
                    else:
                        # Update last_seen even if not notifying
                        if not self.storage.is_new_or_updated(prop):
                            self.storage.save(prop)

        except ScraperError as e:
            stats.errors += 1
            self.logger.error("scraper_error", url=url, error=str(e))
        except Exception as e:
            stats.errors += 1
            self.logger.error("unexpected_error", url=url, error=str(e), exc_info=True)

        # Mark as initialized after first run
        if is_first_run:
            self.storage.set_initialized()
            property_count = self.storage.get_property_count()
            self.logger.info(
                "initialization_complete",
                properties_saved=property_count,
                message=f"✅ Initialized with {property_count} properties. Monitoring started.",
            )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        stats.check_duration_ms = duration_ms

        # Log statistics
        self.logger.info("check_completed", stats=str(stats))

        return stats
