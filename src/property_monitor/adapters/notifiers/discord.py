"""Discord webhook notifier with rate limiting and rich embeds."""

import time
from collections import deque
from datetime import datetime
from typing import Any

import httpx
import structlog

from property_monitor.domain.exceptions import WebhookFailedError
from property_monitor.domain.models import Property


class DiscordNotifier:
    """
    Discord webhook notifier with automatic rate limiting.

    Discord limits:
    - 5 requests per 2 seconds per webhook
    - 30 requests per 60 seconds (global limit)
    """

    def __init__(
        self,
        webhook_url: str,
        rate_limit_per_minute: int = 25,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL
            rate_limit_per_minute: Maximum requests per minute (default: 25, max: 30)
            logger: Structured logger instance
        """
        self.webhook_url = webhook_url
        self.rate_limit = min(rate_limit_per_minute, 30)
        self.logger = logger or structlog.get_logger(__name__)
        self.request_times: deque[float] = deque(maxlen=30)
        self.client = httpx.Client(timeout=10.0)

    def _check_rate_limit(self) -> None:
        """Implement sliding window rate limiting."""
        now = time.time()

        # Remove requests older than 60 seconds
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

        # Check if we've hit the limit
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                self.logger.warning("rate_limit_sleeping", sleep_seconds=sleep_time)
                time.sleep(sleep_time)

    def _create_embed(self, property_data: Property) -> dict[str, Any]:
        """
        Create rich Discord embed for property notification.

        Args:
            property_data: Property to create embed for

        Returns:
            Discord embed dictionary
        """
        # Color based on priority
        color_map = {
            "urgent": 0xFF0000,  # Red
            "high": 0xFFA500,  # Orange
            "normal": 0x00FF00,  # Green
        }
        color = color_map[property_data.priority.value]

        # Build fields
        fields = [
            {"name": "💰 Price", "value": f"Rs {property_data.price:,}/Month", "inline": True},
            {"name": "📍 Location", "value": property_data.address[:1024], "inline": False},
        ]

        # Add amenities if available
        if property_data.bedrooms is not None:
            fields.append(
                {"name": "🛏️ Bedrooms", "value": str(property_data.bedrooms), "inline": True}
            )

        if property_data.bathrooms is not None:
            fields.append(
                {"name": "🚿 Bathrooms", "value": str(property_data.bathrooms), "inline": True}
            )

        if property_data.property_type:
            fields.append(
                {"name": "🏠 Type", "value": property_data.property_type[:1024], "inline": True}
            )

        # Add posted time if available
        if property_data.posted_minutes_ago is not None:
            minutes = property_data.posted_minutes_ago
            if minutes < 60:
                time_str = f"{minutes} minutes ago"
            elif minutes < 1440:
                hours = minutes // 60
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                days = minutes // 1440
                time_str = f"{days} day{'s' if days > 1 else ''} ago"

            fields.append({"name": "🕐 Posted", "value": time_str, "inline": True})

        embed = {
            "title": f"🏠 NEW PROPERTY FOUND!",
            "description": (
                f"**{property_data.title[:256]}**\n\n" f"{property_data.priority_label}"
            ),
            "url": property_data.url,
            "color": color,
            "fields": fields,
            "footer": {"text": "Nepal Property Monitor"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        return embed

    def _send_embed(self, embed: dict[str, Any], retry_count: int = 3) -> bool:
        """
        Send Discord embed with automatic retry on rate limits.

        Args:
            embed: Discord embed dictionary
            retry_count: Maximum retry attempts

        Returns:
            True if sent successfully, False otherwise
        """
        self._check_rate_limit()

        for attempt in range(retry_count):
            try:
                response = self.client.post(self.webhook_url, json={"embeds": [embed]})

                if response.status_code == 429:
                    # Rate limited by Discord
                    retry_after = float(response.headers.get("X-RateLimit-Reset-After", 1))
                    self.logger.warning(
                        "discord_rate_limited", retry_after=retry_after, attempt=attempt + 1
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                self.request_times.append(time.time())
                self.logger.info("notification_sent", title=embed.get("title", "Unknown"))
                return True

            except httpx.HTTPStatusError as e:
                self.logger.error(
                    "webhook_http_error",
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == retry_count - 1:
                    return False
                time.sleep(2**attempt)

            except httpx.RequestError as e:
                self.logger.error(
                    "webhook_request_error", attempt=attempt + 1, error=str(e)
                )
                if attempt == retry_count - 1:
                    return False
                time.sleep(2**attempt)

        return False

    def notify(self, property_data: Property) -> bool:
        """
        Send notification for a property.

        Args:
            property_data: Property to notify about

        Returns:
            True if notification was sent successfully, False otherwise
        """
        embed = self._create_embed(property_data)
        return self._send_embed(embed)

    def send_test_message(self) -> bool:
        """
        Send a test notification to verify webhook configuration.

        Returns:
            True if test message was sent successfully, False otherwise
        """
        test_embed = {
            "title": "✅ Nepal Property Monitor - Test Notification",
            "description": (
                "Your Discord webhook is configured correctly!\n\n"
                "The monitor is now ready to send you notifications when new properties "
                "matching your budget are found."
            ),
            "color": 0x00FF00,  # Green
            "fields": [
                {"name": "Status", "value": "🟢 Operational", "inline": True},
                {
                    "name": "Budget Filter",
                    "value": "≤ Rs 10,000/month",
                    "inline": True,
                },
            ],
            "footer": {"text": "Nepal Property Monitor v1.0.0"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        success = self._send_embed(test_embed)
        if success:
            self.logger.info("test_message_sent")
        else:
            self.logger.error("test_message_failed")
        return success

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        try:
            self.client.close()
        except Exception:
            pass
