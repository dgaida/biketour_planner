"""BRouter API integration for offline routing."""

import gpxpy
import requests

from .config import get_config
from .exceptions import RoutingError
from .logger import get_logger

logger = get_logger()


def check_brouter_availability() -> bool:
    """Checks if the BRouter server is reachable and responding.

    Returns:
        True if the server is available, False otherwise.
    """
    config = get_config()
    base_url = config.routing.brouter_url.rstrip("/")
    url = f"{base_url}/brouter"
    try:
        logger.debug(f"Checking BRouter availability at {url}")
        r = requests.get(url, timeout=5)
        # BRouter might return 400 (Bad Request) if called without parameters,
        # which is still a sign that the server is up and responding.
        return r.status_code < 500
    except requests.exceptions.RequestException as e:
        logger.debug(f"BRouter not reachable at {url}: {e}")
        return False


def route_to_address(lat_from: float, lon_from: float, lat_to: float, lon_to: float) -> str:
    """Computes a route between two points using BRouter.

    Args:
        lat_from: Latitude of the start point.
        lon_from: Longitude of the start point.
        lat_to: Latitude of the destination point.
        lon_to: Longitude of the destination point.

    Returns:
        The routing response as a GPX string.

    Raises:
        RoutingError: If BRouter is unreachable or the request fails.
    """
    if not check_brouter_availability():
        raise RoutingError("BRouter server not reachable")

    config = get_config()
    base_url = config.routing.brouter_url.rstrip("/")
    url = f"{base_url}/brouter"
    lonlats = f"{lon_from:.15g},{lat_from:.15g}|{lon_to:.15g},{lat_to:.15g}"
    try:
        r = requests.get(url, params={"lonlats": lonlats, "profile": "trekking", "format": "gpx"}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        raise RoutingError(str(e)) from e


def get_route2address_as_points(
    start_lat: float, start_lon: float, target_lat: float, target_lon: float
) -> list[gpxpy.gpx.GPXTrackPoint]:
    """Computes a route between two points and returns it as a list of GPX points.

    Args:
        start_lat: Latitude of the start point.
        start_lon: Longitude of the start point.
        target_lat: Latitude of the target point.
        target_lon: Longitude of the target point.

    Returns:
        A list of GPXTrackPoint objects.

    Raises:
        RoutingError: If routing fails or the response is invalid.
    """
    gpx_str = route_to_address(start_lat, start_lon, target_lat, target_lon)
    if not gpx_str:
        raise RoutingError("Empty response")
    try:
        gpx = gpxpy.parse(gpx_str)
        if not gpx.tracks or not gpx.tracks[0].segments:
            raise RoutingError("No tracks or segments found in GPX")
        points = gpx.tracks[0].segments[0].points
        if not points:
            raise RoutingError("No points found in GPX")
        return points
    except RoutingError:
        raise
    except Exception as e:
        raise RoutingError(f"Failed to parse GPX: {e}") from e
