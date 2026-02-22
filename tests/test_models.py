from datetime import date

import pytest
from pydantic import ValidationError

from biketour_planner.models import Booking, RouteStatistics


def test_route_statistics_update():
    stats1 = RouteStatistics(max_elevation=1000, total_distance=100, total_ascent=500, total_descent=200)
    stats2 = RouteStatistics(max_elevation=1200, total_distance=50, total_ascent=300, total_descent=100)

    stats1.update(stats2)

    assert stats1.max_elevation == 1200
    assert stats1.total_distance == 150
    assert stats1.total_ascent == 800
    assert stats1.total_descent == 300


def test_booking_validation_success():
    booking = Booking(
        hotel_name="Test Hotel",
        arrival_date=date(2026, 5, 15),
        departure_date=date(2026, 5, 16),
        latitude=45.0,
        longitude=15.0,
    )
    assert booking.hotel_name == "Test Hotel"


def test_booking_validation_fail_date():
    with pytest.raises(ValidationError):
        Booking(
            hotel_name="Test Hotel",
            arrival_date=date(2026, 5, 15),
            departure_date=date(2026, 5, 14),  # Before arrival
            latitude=45.0,
            longitude=15.0,
        )


def test_booking_validation_fail_lat():
    with pytest.raises(ValidationError):
        Booking(
            hotel_name="Test Hotel",
            arrival_date=date(2026, 5, 15),
            departure_date=date(2026, 5, 16),
            latitude=100.0,  # Invalid lat
            longitude=15.0,
        )
