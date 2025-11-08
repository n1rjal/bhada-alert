"""Custom exception hierarchy for property monitor."""


class PropertyMonitorError(Exception):
    """Base exception for all property monitor errors."""

    pass


# Scraping errors
class ScraperError(PropertyMonitorError):
    """Base class for scraping-related errors."""

    pass


class PageNotFoundError(ScraperError):
    """Property listing page not found (404)."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Page not found: {url}")


class RateLimitedError(ScraperError):
    """Scraper was rate limited."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds")


class ParseError(ScraperError):
    """Failed to parse property data from HTML."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Parse error for {url}: {reason}")


class NetworkError(ScraperError):
    """Network-related error during scraping."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Network error for {url}: {reason}")


# Notification errors
class NotificationError(PropertyMonitorError):
    """Base class for notification errors."""

    pass


class WebhookFailedError(NotificationError):
    """Discord webhook failed to send."""

    def __init__(self, reason: str, status_code: int | None = None) -> None:
        self.reason = reason
        self.status_code = status_code
        msg = f"Webhook failed: {reason}"
        if status_code:
            msg += f" (status: {status_code})"
        super().__init__(msg)


# Storage errors
class StorageError(PropertyMonitorError):
    """Base class for storage errors."""

    pass


class DataCorruptedError(StorageError):
    """Stored data is corrupted."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Data corrupted at {path}: {reason}")
