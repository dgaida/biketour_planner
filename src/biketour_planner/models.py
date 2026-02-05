from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

@dataclass
class RoutePosition:
    """Current position in route calculation."""
    file: str
    index: int
    lat: float
    lon: float

@dataclass
class RouteStatistics:
    """Accumulated route statistics."""
    max_elevation: float = 0.0
    total_distance: float = 0.0
    total_ascent: float = 0.0
    total_descent: float = 0.0

    def update(self, other: RouteStatistics) -> None:
        """Update statistics with another statistics object."""
        self.max_elevation = max(self.max_elevation, other.max_elevation)
        self.total_distance += other.total_distance
        self.total_ascent += other.total_ascent
        self.total_descent += other.total_descent

@dataclass
class RouteContext:
    """Context for route iteration."""
    iteration: int
    target: RoutePosition
    visited: set[str] = field(default_factory=set)
    used_base_files: set[str] = field(default_factory=set)
    route_files: list[dict[str, Any]] = field(default_factory=list)
    force_direction: Optional[str] = None

class Booking(BaseModel):
    """Validated booking model."""
    hotel_name: str = Field(..., min_length=1)
    arrival_date: date
    departure_date: date
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    address: Optional[str] = None
    phone: Optional[str] = None
    city_name: Optional[str] = None
    country_name: Optional[str] = None

    has_kitchen: bool = False
    has_washing_machine: bool = False
    has_breakfast: bool = False

    total_price: Optional[float] = Field(None, ge=0)
    free_cancel_until: Optional[date] = None

    tourist_sights: Optional[dict[str, Any]] = None
    gpx_files: list[dict[str, Any]] = Field(default_factory=list)
    gpx_track_final: Optional[str] = None

    total_distance_km: Optional[float] = Field(None, ge=0)
    total_ascent_m: Optional[int] = Field(None, ge=0)
    total_descent_m: Optional[int] = Field(None, ge=0)
    max_elevation_m: Optional[int] = None

    # Internal state for routing
    last_gpx_file: Optional[dict[str, Any]] = Field(None, alias="_last_gpx_file")

    @field_validator('departure_date')
    @classmethod
    def departure_after_arrival(cls, v: date, info: Any) -> date:
        if 'arrival_date' in info.data and v <= info.data['arrival_date']:
            raise ValueError('Departure must be after arrival')
        return v

    model_config = ConfigDict(
        populate_by_name=True,
    )
