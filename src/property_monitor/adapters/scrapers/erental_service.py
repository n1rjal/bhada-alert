from selectolax.parser import HTMLParser

from property_monitor.domain.models import Property
from .base import BasePropertyScrapper
import re


class ERentalService(BasePropertyScrapper):
    """
    Scrapper for ERental Service
    """

    BASE_URL = "https://erentalservice.com/property/"

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

    def _parse_normal_node(self, li):
        pattern = r"[^\w\s]"
        text = li.text().strip().title()
        cleaned = re.sub(pattern, "", text)
        return " ".join([ch for ch in cleaned.split(" ") if ch])

    def _parse_price_node(self, li):
        text = self._parse_normal_node(li)
        return float(text.split(" ").pop())

    def _parse_bedrooms(self, li):
        return int(self._parse_rooms_node(li))

    def _parse_rooms_node(self, li):
        text = self._parse_normal_node(li)
        return float(text.split(" ").pop(0))

    def _parse_property_id(self, li):
        text = self._parse_normal_node(li)
        return text.split(" ").pop()

    def _parse_property(self, node):
        title = node.css_first("h4").text()
        url = a.attributes.get("href") if (a := node.css_first("a")) else None

        # list of li elements
        # ['Chabahil', 'ID: 33683', '3 Bedroom', '1 Kitchen', '1 Living', '3 Bathroom', 'Water - Yes', '2.5 Floor', 'Rs. 105000', '/Month'] # noqa

        property = {"title": title, "url": url, "property_type": None}

        li_setup = [
            {"name": "address", "parser": self._parse_normal_node},
            {"name": "property_id", "parser": self._parse_property_id},
            {"name": "bedrooms", "parser": self._parse_rooms_node},
            {"name": "bathroom", "parser": self._parse_rooms_node},
            None,
            None,
            None,
            None,
            {"name": "price", "parser": self._parse_price_node},
            None,
        ]

        for i, li in enumerate(node.css(".elementor-icon-list-item")):
            try:
                setup = li_setup[i]
                if not setup:
                    continue

                name = setup["name"]
                parser = setup["parser"]
                parsed = parser(li)
                property[name] = parsed

            except Exception as e:
                self.logger.error(
                    "property_parsing_error",
                    error=str(e),
                    exc_info=True,
                )
                property = {}

        return Property(**property)

    def scrape(self):
        try:
            url = self.BASE_URL
            html = self._fetch_page(url)
            self.logger.info(f"Html page {url} parsed")

            tree = HTMLParser(html)

            nodes = tree.css("div.jet-listing-grid__item")
            self.logger.info(
                "properties_found",
                count=len(nodes),
                url=self.BASE_URL,
            )

            properties = [
                self._parse_property(node) for node in nodes if node is not None
            ]

            self.logger.info("properties_parsed", count=len(properties))
            return properties

        except Exception as e:
            self.logger.error(
                "property_parse_error",
                error=str(e),
                exc_info=True,
            )
            return None
