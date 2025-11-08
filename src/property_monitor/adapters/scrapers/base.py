"""Base protocol for scrapers."""

from typing import Protocol

from property_monitor.domain.models import Property


class PropertyScraper(Protocol):
    """Protocol for property scraper implementations."""

    def scrape(self, url: str) -> list[Property]:
        """
        Scrape properties from a URL.

        Args:
            url: URL to scrape

        Returns:
            List of Property objects

        Raises:
            ScraperError: If scraping fails
        """
        ...
