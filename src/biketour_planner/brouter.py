"""BRouter API integration for offline routing."""

import json

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


def route_to_address(lat_from: float, lon_from: float, lat_to: float, lon_to: float, format: str = "gpx") -> str:
    """Computes a route between two points using BRouter.

    Args:
        lat_from: Latitude of the start point.
        lon_from: Longitude of the start point.
        lat_to: Latitude of the destination point.
        lon_to: Longitude of the destination point.
        format: Format of the response (gpx, geojson, json, csv).

    Returns:
        The routing response as a string.

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
        r = requests.get(url, params={"lonlats": lonlats, "profile": "trekking", "format": format}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        raise RoutingError(str(e)) from e


def parse_brouter_geojson(geojson_str: str) -> tuple[list[gpxpy.gpx.GPXTrackPoint], dict[str, float]]:
    """Parses BRouter GeoJSON output to extract points and surface statistics.

    Args:
        geojson_str: BRouter GeoJSON response string.

    Returns:
        Tuple of:
            - List of GPXTrackPoint objects.
            - Dictionary with 'paved', 'unpaved' and 'other' distances in meters.
    """
    if not geojson_str:
        return [], {"paved": 0.0, "unpaved": 0.0, "other": 0.0}

    try:
        data = json.loads(geojson_str)
    except json.JSONDecodeError as e:
        raise RoutingError(f"Failed to parse GeoJSON: {e}") from e

    # Extract points
    points = []
    if "features" in data and len(data["features"]) > 0:
        feature = data["features"][0]
        if "geometry" in feature and "coordinates" in feature["geometry"]:
            for coord in feature["geometry"]["coordinates"]:
                # GeoJSON coordinates are [lon, lat, ele]
                lon, lat = coord[0], coord[1]
                ele = coord[2] if len(coord) > 2 else None
                points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=ele))

    # Extract surface statistics from messages
    # BRouter GeoJSON messages property contains segment details
    paved_dist = 0.0
    unpaved_dist = 0.0
    other_dist = 0.0

    paved_surfaces = {"asphalt", "concrete", "paved", "paving_stones"}
    unpaved_surfaces = {
        "gravel",
        "fine_gravel",
        "compacted",
        "unpaved",
        "ground",
        "dirt",
        "earth",
        "grass",
        "sand",
        "cobblestone",
        "sett",
        "shingle",
        "pebblestone",
    }

    if "features" in data and len(data["features"]) > 0:
        props = data["features"][0].get("properties", {})
        # BRouter supports both JSON 'messages' and 'message' in properties
        messages = props.get("messages") or props.get("message")

        if messages:
            # First message is often the header
            header = messages[0]
            try:
                dist_idx = header.index("Distance")
                surface_idx = header.index("surface") if "surface" in header else None
            except ValueError:
                dist_idx, surface_idx = None, None

            if dist_idx is not None:
                prev_cum_dist = 0.0
                for i in range(1, len(messages)):
                    msg = messages[i]
                    try:
                        cum_dist = float(msg[dist_idx])
                        segment_dist = cum_dist - prev_cum_dist
                        prev_cum_dist = cum_dist

                        surface = msg[surface_idx].lower() if surface_idx is not None else "unknown"

                        if any(s in surface for s in paved_surfaces):
                            paved_dist += segment_dist
                        elif any(s in surface for s in unpaved_surfaces):
                            unpaved_dist += segment_dist
                        else:
                            other_dist += segment_dist
                    except (ValueError, IndexError):
                        continue

    return points, {"paved": paved_dist, "unpaved": unpaved_dist, "other": other_dist}


def get_route2address_with_stats(
    start_lat: float, start_lon: float, target_lat: float, target_lon: float
) -> tuple[list[gpxpy.gpx.GPXTrackPoint], dict[str, float]]:
    """Computes a route between two points and returns points and surface statistics.

    Args:
        start_lat: Latitude of the start point.
        start_lon: Longitude of the start point.
        target_lat: Latitude of the target point.
        target_lon: Longitude of the target point.

    Returns:
        Tuple of (points, surface_stats).

    Raises:
        RoutingError: If routing fails or the response is invalid.
    """
    geojson_str = route_to_address(start_lat, start_lon, target_lat, target_lon, format="geojson")
    if not geojson_str:
        raise RoutingError("Empty response")

    return parse_brouter_geojson(geojson_str)


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
    points, _ = get_route2address_with_stats(start_lat, start_lon, target_lat, target_lon)
    return points
