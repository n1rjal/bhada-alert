"""Base protocol for scrapers."""

from typing import Protocol
import random

import backoff
import httpx
import structlog

from property_monitor.domain.models import Property

from property_monitor.domain.exceptions import (
    NetworkError,
    PageNotFoundError,
    RateLimitedError,
)


class PropertyScraper(Protocol):
    """Protocol for property scraper implementations."""

    def scrape(self) -> list[Property]:
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


class BasePropertyScrapper:
    client: httpx.Client

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa
    ]

    @property
    def logger(self):
        cls = self.__class__
        return structlog.get_logger(f"{cls.__module__}.{cls.__name__}")

    def _get_headers(self) -> dict[str, str]:
        """Generate request headers with random User-Agent."""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",  # noqa
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @property
    def client(self):
        headers = self._get_headers()
        return httpx.Client(headers=headers)

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
            self.logger.error(
                "http_error",
                url=url,
                status_code=e.response.status_code,
            )
            raise NetworkError(url, str(e))
        except httpx.RequestError as e:
            self.logger.error("request_error", url=url, error=str(e))
            raise NetworkError(url, str(e))

    def __del__(self) -> None:
        """Clean up HTTP client on deletion."""
        try:
            self.client.close()
        except Exception:
            pass
