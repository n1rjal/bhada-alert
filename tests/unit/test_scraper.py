"""Unit tests for scrapers."""

import pytest

from property_monitor.adapters.scrapers.nepal_bazaar import NepalBazaarScraper


class TestNepalBazaarScraper:
    """Tests for Nepal Bazaar scraper."""

    def test_parse_price_with_comma(self) -> None:
        """Test price parsing with comma."""
        scraper = NepalBazaarScraper()
        price = scraper._parse_price("Rs15,000")
        assert price == 15000

    def test_parse_price_without_comma(self) -> None:
        """Test price parsing without comma."""
        scraper = NepalBazaarScraper()
        price = scraper._parse_price("Rs15000")
        assert price == 15000

    def test_parse_price_with_spaces(self) -> None:
        """Test price parsing with spaces."""
        scraper = NepalBazaarScraper()
        price = scraper._parse_price("Rs 15 000")
        assert price == 15000

    def test_parse_price_invalid(self) -> None:
        """Test price parsing with invalid input."""
        scraper = NepalBazaarScraper()
        price = scraper._parse_price("Price not available")
        assert price is None

    def test_parse_timestamp_minutes(self) -> None:
        """Test timestamp parsing for minutes."""
        scraper = NepalBazaarScraper()
        minutes = scraper._parse_timestamp("40 minutes ago")
        assert minutes == 40

    def test_parse_timestamp_hours(self) -> None:
        """Test timestamp parsing for hours."""
        scraper = NepalBazaarScraper()
        minutes = scraper._parse_timestamp("2 hours ago")
        assert minutes == 120

    def test_parse_timestamp_days(self) -> None:
        """Test timestamp parsing for days."""
        scraper = NepalBazaarScraper()
        minutes = scraper._parse_timestamp("1 day ago")
        assert minutes == 1440

    def test_parse_timestamp_invalid(self) -> None:
        """Test timestamp parsing with invalid input."""
        scraper = NepalBazaarScraper()
        minutes = scraper._parse_timestamp("unknown time")
        assert minutes is None
