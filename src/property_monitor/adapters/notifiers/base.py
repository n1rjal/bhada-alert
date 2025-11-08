"""Base protocol for notifiers."""

from typing import Protocol

from property_monitor.domain.models import Property


class Notifier(Protocol):
    """Protocol for notification implementations."""

    def notify(self, property_data: Property) -> bool:
        """
        Send notification for a property.

        Args:
            property_data: Property to notify about

        Returns:
            True if notification was sent successfully, False otherwise
        """
        ...

    def send_test_message(self) -> bool:
        """
        Send a test notification to verify configuration.

        Returns:
            True if test message was sent successfully, False otherwise
        """
        ...
