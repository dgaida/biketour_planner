"""Data models for the Bike Tour Planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


@dataclass
class RoutePosition:
    """Current position in route calculation.

    Attributes:
        file: Name of the GPX file.
        index: Index of the point within the GPX track.
        lat: Latitude of the point.
        lon: Longitude of the point.
    """

    file: str
    index: int
    lat: float
    lon: float


@dataclass
class RouteStatistics:
    """Accumulated route statistics.

    Attributes:
        max_elevation: Maximum elevation reached in meters.
        total_distance: Total distance traveled in meters.
        total_ascent: Total ascent in meters.
        total_descent: Total descent in meters.
    """

    max_elevation: float = 0.0
    total_distance: float = 0.0
    total_ascent: float = 0.0
    total_descent: float = 0.0

    def update(self, other: RouteStatistics) -> None:
        """Update statistics with another statistics object.

        Args:
            other: Another RouteStatistics object to merge.
        """
        self.max_elevation = max(self.max_elevation, other.max_elevation)
        self.total_distance += other.total_distance
        self.total_ascent += other.total_ascent
        self.total_descent += other.total_descent


@dataclass
class RouteContext:
    """Context for route iteration.

    Attributes:
        iteration: Current iteration index.
        target: The target RoutePosition we are heading towards.
        visited: Set of filenames already visited.
        used_base_files: Set of base filenames already used.
        route_files: List of GPX segments forming the route.
        force_direction: Direction to force for the first segment ('forward' or 'backward').
    """

    iteration: int
    target: RoutePosition
    visited: set[str] = field(default_factory=set)
    used_base_files: set[str] = field(default_factory=set)
    route_files: list[dict[str, Any]] = field(default_factory=list)
    force_direction: str | None = None


class Booking(BaseModel):
    """Validated booking model representing an accommodation and associated route data.

    Attributes:
        hotel_name: Name of the accommodation.
        arrival_date: Date of arrival.
        departure_date: Date of departure.
        latitude: Latitude of the accommodation.
        longitude: Longitude of the accommodation.
        address: Full address.
        phone: Contact phone number.
        city_name: Name of the city.
        country_name: Name of the country.
        has_kitchen: Whether the accommodation has a kitchen.
        has_washing_machine: Whether the accommodation has a washing machine.
        has_breakfast: Whether breakfast is included.
        total_price: Total cost of the stay.
        free_cancel_until: Last date for free cancellation.
        tourist_sights: Nearby tourist sights discovered.
        gpx_files: List of GPX segments for the route to this booking.
        gpx_track_final: Filename of the merged final GPX track.
        total_distance_km: Total distance for the daily route in km.
        total_ascent_m: Total ascent for the daily route in meters.
        total_descent_m: Total descent for the daily route in meters.
        max_elevation_m: Maximum elevation reached on the route in meters.
        last_gpx_file: Internal state for chaining routes to the next day.
    """

    hotel_name: str = Field(..., min_length=1)
    arrival_date: date
    departure_date: date
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    address: str | None = None
    phone: str | None = None
    city_name: str | None = None
    country_name: str | None = None

    has_kitchen: bool = False
    has_washing_machine: bool = False
    has_breakfast: bool = False
    has_towels: bool = False
    has_toiletries: bool = False

    total_price: float | None = Field(None, ge=0)
    free_cancel_until: date | None = None

    tourist_sights: dict[str, Any] | None = None
    gpx_files: list[dict[str, Any]] = Field(default_factory=list)
    gpx_track_final: str | None = None

    total_distance_km: float | None = Field(None, ge=0)
    total_ascent_m: int | None = Field(None, ge=0)
    total_descent_m: int | None = Field(None, ge=0)
    max_elevation_m: int | None = None

    # Internal state for routing
    last_gpx_file: dict[str, Any] | None = Field(None, alias="_last_gpx_file")

    @field_validator("departure_date")
    @classmethod
    def departure_after_arrival(cls, v: date, info: Any) -> date:
        """Validates that departure date is after arrival date.

        Args:
            v: Departure date.
            info: Validation context.

        Returns:
            The validated departure date.

        Raises:
            ValueError: If departure is not after arrival.
        """
        if "arrival_date" in info.data and v <= info.data["arrival_date"]:
            raise ValueError("Departure must be after arrival")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
    )
