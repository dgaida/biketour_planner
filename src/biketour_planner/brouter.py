"""BRouter API integration for offline routing."""

import requests
import gpxpy
from .exceptions import RoutingError
from .logger import get_logger

logger = get_logger()


def check_brouter_availability() -> bool:
    try:
        r = requests.get("http://localhost:17777/brouter", timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def route_to_address(lat_from: float, lon_from: float, lat_to: float, lon_to: float) -> str:
    if not check_brouter_availability():
        raise RoutingError("BRouter server not reachable")
    url = "http://localhost:17777/brouter"
    lonlats = f"{lon_from:.15g},{lat_from:.15g}|{lon_to:.15g},{lat_to:.15g}"
    try:
        r = requests.get(url, params={"lonlats": lonlats, "profile": "trekking", "format": "gpx"}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        raise RoutingError(str(e))


def get_route2address_as_points(start_lat: float, start_lon: float, target_lat: float, target_lon: float) -> list[gpxpy.gpx.GPXTrackPoint]:
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
        raise RoutingError(f"Failed to parse GPX: {e}")
