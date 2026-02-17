"""Static helper functions for GPX route management."""

import math
from pathlib import Path

import gpxpy

from .elevation_calc import calculate_elevation_gain_segment_based, calculate_elevation_gain_smoothed
from .logger import get_logger

# Initialize Logger
logger = get_logger()

TrackStats = tuple[float, float, float, float]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the distance between two coordinates in meters.

    Uses the Haversine formula for great-circle distances on a sphere.
    This formula provides good approximations for distances on the Earth's surface.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        The distance in meters.

    Example:
        >>> distance = haversine(52.5200, 13.4050, 48.1351, 11.5820)  # Berlin -> Munich
        >>> print(f"{distance / 1000:.1f} km")
        504.2 km
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_gpx_file(gpx_file: Path) -> gpxpy.gpx.GPX | None:
    """Reads a GPX file with robust encoding handling.

    Tries different encoding strategies (UTF-8, Latin-1, CP1252) and
    handles BOM (Byte Order Mark) and leading whitespaces.

    Args:
        gpx_file: Path to the GPX file.

    Returns:
        The parsed GPX object or None on error.
    """
    # Try different encoding strategies
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            content = gpx_file.read_text(encoding=encoding)

            # Remove BOM if present
            if content.startswith("\ufeff"):
                content = content[1:]

            # Remove leading whitespaces/newlines
            content = content.lstrip()

            # Parse GPX
            gpx = gpxpy.parse(content)
            return gpx

        except (UnicodeDecodeError, gpxpy.gpx.GPXXMLSyntaxException):
            continue
        except Exception as e:
            logger.error(f"Unexpected error reading {gpx_file.name}: {e}")
            continue

    # If all encodings fail, try binary reading
    try:
        with open(gpx_file, "rb") as f:
            content = f.read()

        # Try UTF-8 with error handling
        text = content.decode("utf-8", errors="ignore")

        # Remove BOM
        if text.startswith("\ufeff"):
            text = text[1:]

        text = text.lstrip()

        return gpxpy.parse(text)

    except Exception as e:
        logger.error(f"Error parsing {gpx_file.name}: {e}")
        return None


def get_base_filename(filename: str) -> str:
    """Extracts the base filename without direction suffixes.

    Removes suffixes like '_inverted', '_reversed', '_rev' etc. to prevent
    using the same track multiple times in different directions.

    Args:
        filename: GPX filename with potential direction suffix.

    Returns:
        Base filename without direction info.

    Example:
        >>> get_base_filename("route_Munich_Garmisch_reversed.gpx")
        'route_Munich_Garmisch.gpx'
    """
    # Remove common suffixes for inverted tracks
    for suffix in ["_inverted", "_reversed", "_rev", "_inverse", "_backward"]:
        if filename.lower().endswith(f"{suffix}.gpx"):
            return filename[: -len(suffix) - 4] + ".gpx"

    return filename


def find_closest_point_in_track(points: list[dict], target_lat: float, target_lon: float) -> tuple[int, float]:
    """Finds the closest point within a track to a target coordinate.

    Args:
        points: List of point dictionaries with keys 'lat', 'lon', 'index'.
        target_lat: Target latitude.
        target_lon: Target longitude.

    Returns:
        A tuple of (index, distance) for the closest point.
    """
    best_idx = None
    best_dist = float("inf")

    for point in points:
        d = haversine(target_lat, target_lon, point["lat"], point["lon"])
        if d < best_dist:
            best_dist = d
            best_idx = point["index"]

    return best_idx, best_dist


def get_statistics4track(
    gpx,
    start_index: int = 0,
    end_index: int = None,
    max_elevation: float = 0.0,
    total_distance: float = 0.0,
    total_ascent: float = 0.0,
    total_descent: float = 0.0,
    reversed_direction: bool = False,
) -> TrackStats:
    """Calculates statistics for a track section between two indices.

    Args:
        gpx: GPX object.
        start_index: Start index of the section.
        end_index: End index of the section.
        max_elevation: Previous max elevation.
        total_distance: Previous total distance.
        total_ascent: Previous total ascent.
        total_descent: Previous total descent.
        reversed_direction: If True, the section is traversed backward.

    Returns:
        Tuple of (max_elevation, total_distance, total_ascent, total_descent).
    """
    if not end_index or end_index == float("inf"):
        # Determine total number of points
        num_points = 0
        for track in gpx.tracks:
            for seg in track.segments:
                num_points += len(seg.points)
        end_index = num_points - 1

    segment_points = []
    point_counter = 0
    for track in gpx.tracks:
        for seg in track.segments:
            if reversed_direction:
                for p in seg.points[::-1]:
                    if start_index <= point_counter <= end_index:
                        segment_points.append(p)
                    point_counter += 1
            else:
                for p in seg.points:
                    if start_index <= point_counter <= end_index:
                        segment_points.append(p)
                    point_counter += 1

    prev = None
    for p in segment_points:
        if prev:
            d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
            total_distance += d
        prev = p

    elevations = [p.elevation for p in segment_points if p.elevation is not None]
    if elevations:
        max_elevation = max(max(elevations), max_elevation)

        # take mean of elevation calculations as both are not accurate
        ascent_segment = calculate_elevation_gain_segment_based(elevations, calculate_descent=False)
        ascent_smoothed = calculate_elevation_gain_smoothed(elevations, calculate_descent=False)
        total_ascent += (ascent_segment + ascent_smoothed) / 2

        descent_segment = calculate_elevation_gain_segment_based(elevations, calculate_descent=True)
        descent_smoothed = calculate_elevation_gain_smoothed(elevations, calculate_descent=True)
        total_descent += (descent_segment + descent_smoothed) / 2

    logger.debug(f"   Points: {len(segment_points)}")

    return max_elevation, total_distance, total_ascent, total_descent
