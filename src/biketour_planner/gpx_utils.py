"""Utility functions for GPX track management in the Bike Tour Planner."""

from pathlib import Path

from .gpx_route_manager import GPXRouteManager


def get_gps_tracks4day_4alldays(gpx_dir: Path, bookings: list[dict], output_path: Path) -> list[dict]:
    """Processes all bookings and collects GPS tracks for each day.

    This function is a wrapper around GPXRouteManager.process_all_bookings()
    for compatibility with existing code.

    Args:
        gpx_dir: Directory with GPX files.
        bookings: List of bookings.
        output_path: Output path for merged GPX files.

    Returns:
        Sorted list of bookings enriched with GPS track information.
    """
    manager = GPXRouteManager(gpx_dir, output_path)
    return manager.process_all_bookings(bookings, output_path)
