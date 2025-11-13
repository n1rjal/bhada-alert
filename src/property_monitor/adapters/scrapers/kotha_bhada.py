from selectolax.parser import HTMLParser
from property_monitor.adapters.scrapers.base import BasePropertyScrapper

import re

from property_monitor.domain.models import Property


class KothaBhadaScrapper(BasePropertyScrapper):
    """
    Scrapper for ERent service
    """

    BASE_URL = "https://kothabhada.com/latest-properties?order=latest"

    def __init__(
        self,
        timeout=30.0,
        max_retries=3,
    ) -> None:
        """
        Initialize scrapper
        """
        self.timeout = timeout
        self.max_retries = max_retries

    def _parse_amniety(self, node):
        """
        Amenty is in this format

        - "Purpose\nRent"
        - "Rent Price\nRs. 12,000"
        - "Bedroom\n2"
        - "Bathroom\n2"
        - "Floor\nGround Floor"
        - "Parking\nYes"
        - "Running Water\nYes"
        - "Kitchen\n1"
        - "Sitting Room\n1"
        - "Category\n2BHK"
        - "Status\nAvailable"
        - "Seller Contact Number\n9745923902"
        - "Furnishing\nNo"
        - "Price Negotiable\nYes"
        - "Ad id\n#KB2511041108195607"
        - "Ad Views\n129"
        - "Posted On\n2025/11/04"
        - "Expire On\n2026/08/06"

        So splitting by \n, taking last and then splittling
        by " " and taking last element works
        """
        pattern = r"[^\w\n\s]"
        text = node.text().strip().split("\n").pop().split(" ").pop()
        cleaned = re.sub(pattern, "", text)
        return " ".join([ch for ch in cleaned.split(" ") if ch])

    def _parse_text(self, node):
        pattern = r"[^\w\n\s]"
        text = node.text().strip()
        cleaned = re.sub(pattern, "", text)
        return " ".join([ch for ch in cleaned.split(" ") if ch])

    def scrape_detail_page(self, url):
        detail_content = self._fetch_page(url, fake_curl=True)
        tree = HTMLParser(detail_content)
        amneties_wrapper_nodes = tree.css(".row.border.amenitiesWrapper > div")

        # The amneties are in this order in webpage
        amenities = [
            "Purpose",
            "Rent Price",
            "Bedroom",
            "Bathroom",
            "Floor",
            "Parking",
            "Running Water",
            "Kitchen",
            "Sitting Room",
            "Category",
            "Status",
            "Seller Contact Number",
            "Furnishing",
            "Price Negotiable",
            "Ad id",
            "Ad Views",
            "Posted On",
            "Expire On",
        ]

        amenity_model_property = {
            "Ad id": {
                "name": "property_id",
            },
            "Bathroom": {
                "name": "bathrooms",
                "type": float,
            },
            "Bedroom": {
                "name": "bedrooms",
                "type": int,
            },
            "Rent Price": {"name": "price", "type": float},
        }

        property = {
            "title": self._parse_text(tree.css_first(".propertyTitle")),
            "address": self._parse_text(tree.css_first(".locationPin")),
            "url": url,
        }

        for i, amenity in enumerate(amenities):
            node = amneties_wrapper_nodes[i]
            if amenity in amenity_model_property:
                entry = amenity_model_property[amenity]
                property_name = entry["name"]
                typecast = entry.get("type", str)
                parsed = self._parse_amniety(node)
                casted = typecast(parsed)
                property[property_name] = casted

        return Property(**property)

    def _parse_property(self, node):
        link = (
            a_node.attributes.get("href")
            if (a_node := node.css_first("a"))
            else None  # noqa
        )
        if link:
            return self.scrape_detail_page(link)

    def scrape(self):
        try:
            url = self.BASE_URL
            html = self._fetch_page(url, fake_curl=True)
            self.logger.info(f"Html page {url} parsed")

            tree = HTMLParser(html)

            nodes = tree.css("body > section.siteSec > div > div.row-cols-5.row > div")

            properties = [
                parsed for node in nodes if (parsed := self._parse_property(node))
            ]

            self.logger.info("properties_parsed", count=len(properties))
            return properties

        except Exception as e:
            self.logger.error(
                "property_parse_error",
                error=str(e),
                exc_info=True,
            )
            raise e
            return None
