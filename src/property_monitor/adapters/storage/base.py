"""Base protocol for storage implementations."""

from typing import Protocol

from property_monitor.domain.models import Property


class Storage(Protocol):
    """Protocol for storage implementations."""

    def is_new_or_updated(self, property_data: Property) -> bool:
        """
        Check if property is new or has been updated.

        Args:
            property_data: Property to check

        Returns:
            True if new or updated (price changed), False otherwise
        """
        ...

    def save(self, property_data: Property) -> None:
        """
        Save property to storage.

        Args:
            property_data: Property to save
        """
        ...

    def is_initialized(self) -> bool:
        """
        Check if storage has been initialized.

        Returns:
            True if initialized (has baseline data), False otherwise
        """
        ...

    def set_initialized(self) -> None:
        """Mark storage as initialized."""
        ...

    def get_property_count(self) -> int:
        """
        Get total number of properties in storage.

        Returns:
            Count of properties
        """
        ...
