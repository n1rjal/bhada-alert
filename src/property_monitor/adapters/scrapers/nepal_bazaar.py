"""Nepal Property Bazaar scraper implementation."""

import re
import random
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import backoff
import httpx
import structlog
from selectolax.parser import HTMLParser, Node

from property_monitor.domain.exceptions import (
    NetworkError,
    PageNotFoundError,
    ParseError,
    RateLimitedError,
)
from property_monitor.domain.models import Property


class NepalBazaarScraper:
    """Scraper for Nepal Property Bazaar website."""

    BASE_URL = "https://nepalpropertybazaar.com"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        """
        Initialize scraper.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts
            logger: Structured logger instance
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger or structlog.get_logger(__name__)
        self.client = httpx.Client(
            timeout=timeout, follow_redirects=True, http2=False
        )

    def _get_headers(self) -> dict[str, str]:
        """Generate request headers with random User-Agent."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.TimeoutException),
        max_tries=3,
        max_time=300,
    )
    def _fetch_page(self, url: str) -> str:
        """
        Fetch page with exponential backoff retry.

        Args:
            url: URL to fetch

        Returns:
            HTML content

        Raises:
            PageNotFoundError: If page returns 404
            RateLimitedError: If rate limited
            NetworkError: If network error occurs
        """
        try:
            response = self.client.get(url, headers=self._get_headers())

            if response.status_code == 404:
                raise PageNotFoundError(url)
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitedError(retry_after)

            response.raise_for_status()
            self.logger.info(
                "page_fetched",
                url=url,
                status_code=response.status_code,
                content_length=len(response.text),
            )
            return response.text

        except httpx.HTTPStatusError as e:
            self.logger.error("http_error", url=url, status_code=e.response.status_code)
            raise NetworkError(url, str(e))
        except httpx.RequestError as e:
            self.logger.error("request_error", url=url, error=str(e))
            raise NetworkError(url, str(e))

    def _parse_price(self, price_text: str) -> int | None:
        """
        Parse price from text like 'Rs15,000' or 'Rs 15000'.

        Args:
            price_text: Raw price text

        Returns:
            Price as integer, or None if parsing fails
        """
        try:
            # Remove 'Rs', commas, and spaces
            cleaned = re.sub(r"[Rs,\s]", "", price_text)
            return int(cleaned)
        except (ValueError, AttributeError):
            self.logger.warning("price_parse_failed", price_text=price_text)
            return None

    def _parse_timestamp(self, timestamp_text: str) -> int | None:
        """
        Parse timestamp like '40 minutes ago', '2 hours ago', '1 day ago'.

        Args:
            timestamp_text: Raw timestamp text

        Returns:
            Minutes ago as integer, or None if parsing fails
        """
        try:
            timestamp_lower = timestamp_text.lower().strip()

            # Match patterns like "40 minutes ago", "2 hours ago", "1 day ago"
            minute_match = re.search(r"(\d+)\s*minute", timestamp_lower)
            hour_match = re.search(r"(\d+)\s*hour", timestamp_lower)
            day_match = re.search(r"(\d+)\s*day", timestamp_lower)

            if minute_match:
                return int(minute_match.group(1))
            elif hour_match:
                return int(hour_match.group(1)) * 60
            elif day_match:
                return int(day_match.group(1)) * 1440

            self.logger.warning("timestamp_parse_failed", timestamp_text=timestamp_text)
            return None

        except (ValueError, AttributeError):
            self.logger.warning("timestamp_parse_error", timestamp_text=timestamp_text)
            return None

    def _parse_amenities(self, item: Node) -> dict[str, Any]:
        """
        Parse amenities from property item.

        Args:
            item: Property item HTML node

        Returns:
            Dictionary with bedrooms, bathrooms, property_type
        """
        amenities: dict[str, Any] = {
            "bedrooms": None,
            "bathrooms": None,
            "property_type": None,
        }

        amenity_items = item.css("ul.item-amenities li")
        for amenity in amenity_items:
            text = amenity.text().strip()

            # Parse bedrooms: "Bed: 1" or "Beds: 2"
            bed_match = re.search(r"Beds?:\s*(\d+)", text, re.IGNORECASE)
            if bed_match:
                amenities["bedrooms"] = int(bed_match.group(1))
                continue

            # Parse bathrooms: "Bath: 1" or "Baths: 1.5"
            bath_match = re.search(r"Baths?:\s*([\d.]+)", text, re.IGNORECASE)
            if bath_match:
                amenities["bathrooms"] = float(bath_match.group(1))
                continue

            # Property type: "Flat / Apartment", "Commercial", etc.
            if any(
                keyword in text.lower()
                for keyword in ["flat", "apartment", "house", "room", "commercial"]
            ):
                amenities["property_type"] = text

        return amenities

    def _parse_property_item(self, item: Node) -> Property | None:
        """
        Parse a single property listing item.

        Args:
            item: Property item HTML node

        Returns:
            Property object or None if parsing fails
        """
        try:
            # Extract property ID from data-hz-id attribute
            property_id = item.attributes.get("data-hz-id")
            if not property_id:
                self.logger.warning("missing_property_id")
                return None

            # Extract price
            price_node = item.css_first("span.price")
            price_text = price_node.text().strip() if price_node else None
            price = self._parse_price(price_text) if price_text else None

            if price is None:
                self.logger.warning("skipping_no_price", property_id=property_id)
                return None

            # Extract title and link
            title_node = item.css_first("h2.item-title a")
            if not title_node:
                self.logger.warning("missing_title", property_id=property_id)
                return None

            title = title_node.text().strip()
            link = title_node.attributes.get("href", "")
            absolute_url = urljoin(self.BASE_URL, link)

            # Extract address
            address_node = item.css_first("address.item-address")
            address = address_node.text().strip() if address_node else "Unknown"

            # Extract timestamp
            date_node = item.css_first("div.item-date")
            timestamp_text = date_node.text().strip() if date_node else None
            posted_minutes_ago = (
                self._parse_timestamp(timestamp_text) if timestamp_text else None
            )

            # Extract amenities
            amenities = self._parse_amenities(item)

            # Create Property object
            property_obj = Property(
                property_id=property_id,
                url=absolute_url,
                title=title,
                address=address,
                price=price,
                bedrooms=amenities["bedrooms"],
                bathrooms=amenities["bathrooms"],
                property_type=amenities["property_type"],
                posted_minutes_ago=posted_minutes_ago,
                raw_data={
                    "price_text": price_text,
                    "timestamp_text": timestamp_text,
                },
            )

            return property_obj

        except Exception as e:
            self.logger.error("property_parse_error", error=str(e), exc_info=True)
            return None

    def scrape(self, url: str) -> list[Property]:
        """
        Scrape properties from Nepal Property Bazaar.

        Args:
            url: URL to scrape

        Returns:
            List of Property objects

        Raises:
            ScraperError: If scraping fails
        """
        html = self._fetch_page(url)

        # Parse with selectolax
        tree = HTMLParser(html)

        # Find all property listings
        property_items = tree.css("div.item-listing-wrap")
        self.logger.info("properties_found", count=len(property_items), url=url)

        # Parse each property
        properties: list[Property] = []
        for item in property_items:
            prop = self._parse_property_item(item)
            if prop:
                properties.append(prop)

        self.logger.info("properties_parsed", count=len(properties))
        return properties

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        try:
            self.client.close()
        except Exception:
            pass
