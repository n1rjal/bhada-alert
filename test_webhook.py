#!/usr/bin/env python3
"""Quick test script to verify Discord webhook configuration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from property_monitor.adapters.notifiers.discord import DiscordNotifier
from property_monitor.config import get_settings
from property_monitor.logging_config import get_logger, setup_logging

# Setup logging
setup_logging(log_level="INFO", environment="development")
logger = get_logger(__name__)

def main() -> None:
    """Test Discord webhook."""
    logger.info("testing_discord_webhook")

    # Load webhook URL from configuration (.env file)
    settings = get_settings()
    webhook_url = settings.discord_webhook_url.get_secret_value()

    notifier = DiscordNotifier(webhook_url=webhook_url, logger=logger)

    logger.info("sending_test_message")
    success = notifier.send_test_message()

    if success:
        logger.info("✅ Discord webhook test successful! Check your Discord channel.")
        sys.exit(0)
    else:
        logger.error("❌ Discord webhook test failed. Please check the webhook URL.")
        sys.exit(1)


if __name__ == "__main__":
    main()
