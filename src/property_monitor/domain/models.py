"""Domain models using Pydantic for validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PropertyPriority(str, Enum):
    """Priority levels based on price ranges."""

    URGENT = "urgent"  # Under Rs 7,000
    HIGH = "high"  # Rs 7,000-9,000
    NORMAL = "normal"  # Rs 9,000-10,000


class Property(BaseModel):
    """Property listing model with validation."""

    # Core identifiers
    property_id: str = Field(..., description="Unique property ID from data-hz-id")
    url: str = Field(..., description="Full URL to property listing")

    # Property details
    title: str = Field(..., description="Property title/name")
    address: str = Field(..., description="Full address/location")
    price: int = Field(..., ge=0, description="Price in Rs per month")

    # Amenities
    bedrooms: int | None = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: float | None = Field(None, ge=0, description="Number of bathrooms")
    property_type: str | None = Field(None, description="Type (Flat, House, Room, etc.)")

    # Metadata
    posted_minutes_ago: int | None = Field(None, ge=0, description="Minutes since posted")
    first_seen_at: datetime = Field(
        default_factory=datetime.utcnow, description="When first detected"
    )
    last_seen_at: datetime = Field(
        default_factory=datetime.utcnow, description="When last seen"
    )

    # Raw data for debugging
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw scraped data")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is absolute."""
        if not v.startswith("http"):
            base_url = "https://nepalpropertybazaar.com"
            return f"{base_url}{v}" if v.startswith("/") else f"{base_url}/{v}"
        return v

    @property
    def priority(self) -> PropertyPriority:
        """Calculate priority based on price."""
        if self.price < 7000:
            return PropertyPriority.URGENT
        elif self.price < 9000:
            return PropertyPriority.HIGH
        else:
            return PropertyPriority.NORMAL

    @property
    def priority_emoji(self) -> str:
        """Get emoji for priority level."""
        return {"urgent": "🔥", "high": "⭐", "normal": "✓"}[self.priority.value]

    @property
    def priority_label(self) -> str:
        """Get human-readable priority label."""
        return {
            "urgent": "🔥 URGENT - GREAT DEAL!",
            "high": "⭐ HIGH PRIORITY",
            "normal": "✓ Within Budget",
        }[self.priority.value]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.property_id,
            "url": self.url,
            "title": self.title,
            "address": self.address,
            "price": self.price,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "property_type": self.property_type,
            "posted_minutes_ago": self.posted_minutes_ago,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "raw_data": self.raw_data,
        }


class MonitorStats(BaseModel):
    """Statistics for a monitoring cycle."""

    total_properties: int = Field(default=0, description="Total properties found")
    new_properties: int = Field(default=0, description="New properties detected")
    within_budget: int = Field(default=0, description="Properties within budget")
    notifications_sent: int = Field(default=0, description="Notifications sent")
    errors: int = Field(default=0, description="Errors encountered")
    check_duration_ms: int = Field(default=0, description="Check duration in milliseconds")

    def __str__(self) -> str:
        """Human-readable statistics."""
        return (
            f"📊 Stats: Total: {self.total_properties} | "
            f"New: {self.new_properties} | "
            f"Budget: {self.within_budget} | "
            f"Notifications: {self.notifications_sent} | "
            f"Duration: {self.check_duration_ms}ms"
        )
