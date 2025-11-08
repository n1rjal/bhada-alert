#!/usr/bin/env python3
"""End-to-end test script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from property_monitor.adapters.notifiers.discord import DiscordNotifier
from property_monitor.adapters.scrapers.nepal_bazaar import NepalBazaarScraper
from property_monitor.adapters.storage.sqlite_store import SQLiteStorage
from property_monitor.config import get_settings
from property_monitor.logging_config import get_logger, setup_logging
from property_monitor.services.monitor_service import MonitorService

# Setup logging
setup_logging(log_level="INFO", environment="development")
logger = get_logger(__name__)

logger.info("=== END-TO-END TEST ===")

# Load config
settings = get_settings()

# Initialize components
scraper = NepalBazaarScraper(
    timeout=settings.request_timeout, max_retries=settings.max_retries, logger=logger
)

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
    scraper=scraper,
    notifier=notifier,
    storage=storage,
    max_price=settings.max_price,
    time_window_hours=settings.time_window_hours,
    logger=logger,
)

# Run one check cycle
logger.info("running_check_cycle")
stats = monitor.check_properties(settings.property_urls)

print(f"\n{stats}\n")

# Check results
if not storage.is_initialized():
    logger.error("❌ Storage should be initialized after first run")
    sys.exit(1)

property_count = storage.get_property_count()
logger.info(f"✅ Test completed! Properties in database: {property_count}")

if property_count == 0:
    logger.warning("⚠️ No properties were saved - check scraper")
else:
    logger.info(f"✅ SUCCESS: Monitor is working correctly!")
