"""Unit tests for domain models."""

import pytest
from datetime import datetime

from property_monitor.domain.models import Property, PropertyPriority, MonitorStats


class TestProperty:
    """Tests for Property model."""

    def test_property_creation(self) -> None:
        """Test creating a property."""
        prop = Property(
            property_id="12345",
            url="https://example.com/property/12345",
            title="Test Property",
            address="Test Address",
            price=8000,
            bedrooms=2,
            bathrooms=1.0,
        )

        assert prop.property_id == "12345"
        assert prop.price == 8000
        assert prop.bedrooms == 2

    def test_url_normalization(self) -> None:
        """Test URL is normalized to absolute."""
        prop = Property(
            property_id="123",
            url="/property/test",
            title="Test",
            address="Test",
            price=5000,
        )

        assert prop.url.startswith("https://")
        assert "nepalpropertybazaar.com" in prop.url

    def test_priority_urgent(self) -> None:
        """Test urgent priority (< Rs 7,000)."""
        prop = Property(
            property_id="123",
            url="https://example.com/123",
            title="Test",
            address="Test",
            price=6500,
        )

        assert prop.priority == PropertyPriority.URGENT
        assert prop.priority_emoji == "🔥"
        assert "URGENT" in prop.priority_label

    def test_priority_high(self) -> None:
        """Test high priority (Rs 7,000-9,000)."""
        prop = Property(
            property_id="123",
            url="https://example.com/123",
            title="Test",
            address="Test",
            price=8000,
        )

        assert prop.priority == PropertyPriority.HIGH
        assert prop.priority_emoji == "⭐"
        assert "HIGH" in prop.priority_label

    def test_priority_normal(self) -> None:
        """Test normal priority (Rs 9,000-10,000)."""
        prop = Property(
            property_id="123",
            url="https://example.com/123",
            title="Test",
            address="Test",
            price=9500,
        )

        assert prop.priority == PropertyPriority.NORMAL
        assert prop.priority_emoji == "✓"
        assert "Budget" in prop.priority_label


class TestMonitorStats:
    """Tests for MonitorStats model."""

    def test_stats_creation(self) -> None:
        """Test creating monitor stats."""
        stats = MonitorStats(
            total_properties=100,
            new_properties=5,
            within_budget=20,
            notifications_sent=5,
        )

        assert stats.total_properties == 100
        assert stats.new_properties == 5

    def test_stats_string_representation(self) -> None:
        """Test stats string representation."""
        stats = MonitorStats(
            total_properties=100,
            new_properties=5,
            within_budget=20,
            notifications_sent=5,
        )

        stats_str = str(stats)
        assert "Total: 100" in stats_str
        assert "New: 5" in stats_str
        assert "Budget: 20" in stats_str
