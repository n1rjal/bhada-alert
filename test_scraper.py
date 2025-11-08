#!/usr/bin/env python3
"""Test script to fetch and parse Nepal Property Bazaar website."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx
from selectolax.parser import HTMLParser

from property_monitor.logging_config import get_logger, setup_logging

setup_logging(log_level="INFO", environment="development")
logger = get_logger(__name__)

URL = "https://nepalpropertybazaar.com/search-results/?status%5B%5D=for-rent&location%5B%5D=&areas%5B%5D="


def main() -> None:
    """Fetch and parse the website."""
    logger.info("fetching_nepal_property_bazaar", url=URL)

    # Fetch the page
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(URL, headers=headers)
            response.raise_for_status()

        logger.info(
            "page_fetched",
            status_code=response.status_code,
            content_length=len(response.text),
        )

        # Parse with selectolax
        tree = HTMLParser(response.text)

        # Find all property listings
        property_items = tree.css("div.item-listing-wrap")
        logger.info("properties_found", count=len(property_items))

        # Parse first 3 properties as examples
        for idx, item in enumerate(property_items[:3], 1):
            logger.info(f"--- Property #{idx} ---")

            # Extract property ID from data-hz-id attribute
            property_id = item.attributes.get("data-hz-id", "N/A")
            logger.info("property_id", value=property_id)

            # Extract price
            price_node = item.css_first("span.price")
            price_text = price_node.text().strip() if price_node else "N/A"
            logger.info("price_raw", value=price_text)

            # Extract title
            title_node = item.css_first("h2.item-title a")
            title = title_node.text().strip() if title_node else "N/A"
            logger.info("title", value=title)

            # Extract link
            link = title_node.attributes.get("href", "N/A") if title_node else "N/A"
            logger.info("link", value=link)

            # Extract address
            address_node = item.css_first("address.item-address")
            address = address_node.text().strip() if address_node else "N/A"
            logger.info("address", value=address)

            # Extract timestamp
            date_node = item.css_first("div.item-date")
            timestamp = date_node.text().strip() if date_node else "N/A"
            logger.info("posted_time", value=timestamp)

            # Extract amenities
            amenities = {}
            amenity_items = item.css("ul.item-amenities li")
            for amenity in amenity_items:
                text = amenity.text().strip()
                logger.info("amenity", value=text)

            print()  # Blank line between properties

        logger.info(
            "✅ Sample extraction successful! Extracted data from first 3 properties."
        )

    except httpx.HTTPError as e:
        logger.error("http_error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
