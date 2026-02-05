from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

import gpxpy
from tqdm import tqdm

from .brouter import get_route2address_as_points
from .config import get_config
from .gpx_route_manager_static import (
    find_closest_point_in_track,
    get_base_filename,
    get_statistics4track,
    haversine,
    read_gpx_file,
)
from .logger import get_logger
from .models import RouteContext, RoutePosition, RouteStatistics

if TYPE_CHECKING:
    pass

# Initialize Logger
logger = get_logger()

GPXIndex = dict[str, dict[str, Any]]


class GPXRouteManager:
    """Manages GPX routes and enables chaining of tracks between locations.

    This class implements an intelligent algorithm for route planning of
    multi-day bike tours. The core algorithm works as follows:

    1. **Target Side Determination**: Finds out which side (start or end) of the
       target track is closer to the starting point. This is crucial for
       determining the correct direction of travel through intermediate tracks.

    2. **Start Point Optimization**: In the start track, the algorithm does not
       simply navigate to the point closest to the target, but to the point
       closest to the relevant target side. This prevents inefficient routes.

    3. **Track Chaining**: Connects multiple GPX tracks considering:
       - Spatial proximity (max_connection_distance_m)
       - Avoiding duplicates (same base filenames)
       - Continuing previous routes (for multi-day tours)

    4. **Direction Detection**: Automatically determines whether a track must be
       traversed forward or backward.

    Attributes:
        gpx_dir: Directory with GPX files.
        gpx_index: Preprocessed metadata of all GPX files with start/end points,
                   distances, elevation profiles, and all track points.
        max_connection_distance_m: Maximum distance in meters for automatic
                                   chaining of tracks. Tracks further apart will
                                   not be connected.
        max_chain_length: Maximum number of tracks to chain. Prevents infinite
                         loops during routing problems.
        verbose: If True, enables detailed logging.
    """

    def __init__(
        self,
        gpx_dir: Path,
        output_path: Path,
        max_connection_distance_m: float | None = None,
        max_chain_length: int | None = None,
        start_search_radius_km: float | None = None,
        verbose: bool = False,
    ):
        """Initializes the GPXRouteManager and loads all GPX files.

        Args:
            gpx_dir: Directory with GPX files.
            output_path: Output directory for merged files.
            max_connection_distance_m: Max distance for track chaining in meters.
                                       Default from config if None.
            max_chain_length: Maximum number of tracks to chain. Default from config if None.
            start_search_radius_km: Search radius for start track in km.
                                   Default from config if None.
            verbose: Enable detailed logging.
        """
        config = get_config()

        self.gpx_dir = gpx_dir
        self.output_path = output_path
        self.verbose = verbose

        self.max_connection_distance_m = (
            max_connection_distance_m if max_connection_distance_m is not None else config.routing.max_connection_distance_m
        )
        self.max_chain_length = max_chain_length if max_chain_length is not None else config.routing.max_chain_length
        self.start_search_radius_km = (
            start_search_radius_km if start_search_radius_km is not None else config.routing.start_search_radius_km
        )
        self.target_search_radius_km = config.routing.target_search_radius_km

        self.gpx_index: GPXIndex = {}
        self._preprocess_gpx_directory()

    def _preprocess_gpx_directory(self) -> None:
        """Reads all GPX files exactly once and stores relevant metadata.

        This preprocessing avoids repeatedly parsing the same GPX files during
        route search and significantly speeds up processing.

        Note:
            Files that cannot be parsed are silently skipped.
        """
        gpx_files = list(Path(self.gpx_dir).glob("*.gpx"))

        def process_file(gpx_file: Path) -> tuple[str, dict[str, Any]] | None:
            gpx = read_gpx_file(gpx_file)
            if gpx is None or not gpx.tracks:
                return None

            first_point = None
            last_point = None
            all_points = []

            point_index = 0
            for track in gpx.tracks:
                for seg in track.segments:
                    for p in seg.points:
                        if first_point is None:
                            first_point = p
                        last_point = p
                        all_points.append(
                            {"lat": p.latitude, "lon": p.longitude, "elevation": p.elevation, "index": point_index}
                        )
                        point_index += 1

            max_elevation, total_distance, total_ascent, total_descent = get_statistics4track(gpx)

            if first_point is None or last_point is None:
                return None

            return gpx_file.name, {
                "file": gpx_file,
                "start_lat": first_point.latitude,
                "start_lon": first_point.longitude,
                "end_lat": last_point.latitude,
                "end_lon": last_point.longitude,
                "total_distance_m": total_distance,
                "total_ascent_m": total_ascent,
                "max_elevation_m": (int(round(max_elevation)) if max_elevation != float("-inf") else None),
                "points": all_points,
            }

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = executor.map(process_file, gpx_files)

        for result in results:
            if result:
                filename, metadata = result
                self.gpx_index[filename] = metadata

    def _find_start_pos(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
        previous_last_file: dict[str, Any] | None = None,
    ) -> tuple[str | None, int | None, str | None]:
        """Determines the starting position for the route search.

        If multiple tracks are within the search radius of the starting location,
        the one whose start or end point is closer to the target location is chosen.
        This optimizes route planning by ensuring the start track already points
        in the right direction.

        If a previous route exists (multi-day tour), it is continued.
        In this case, the previous day's direction of travel is enforced to
        ensure consistent routes.

        Args:
            start_lat: Latitude of the start point in decimal degrees.
            start_lon: Longitude of the start point in decimal degrees.
            target_lat: Latitude of the target point in decimal degrees.
            target_lon: Longitude of the target point in decimal degrees.
            previous_last_file: Optional. Dictionary of the last GPX file used
                            the previous day with keys:
                            - 'file' (str): filename
                            - 'end_index' (int): last index used
                            - 'reversed' (bool): whether track was traversed backward

        Returns:
            Tuple of:
                - start_file (str): filename of the starting GPX file.
                - start_index (int): starting index in the track.
                - force_direction (str|None): enforced direction ('forward'/'backward')
                  if continuation from previous day, else None.
        """
        if previous_last_file:
            filename = previous_last_file["file"]
            meta = self.gpx_index.get(filename)
            if meta:
                start_file = filename
                start_index = previous_last_file["end_index"]
                last_point = meta["points"][start_index]
                start_distance = haversine(start_lat, start_lon, last_point["lat"], last_point["lon"])

                force_direction = "backward" if previous_last_file.get("reversed", False) else "forward"

                logger.debug(f"🔗 Continuation detected: {start_file} from index {start_index}")
                logger.debug(f"🔗 Enforced direction: {force_direction} (from previous day)")
                logger.debug(f"🔗 Distance to continuation point: {start_distance:.1f}m")

                return start_file, start_index, force_direction

        candidates = []
        start_radius_m = self.start_search_radius_km * 1000

        for filename, meta in self.gpx_index.items():
            idx, dist_to_start = find_closest_point_in_track(meta["points"], start_lat, start_lon)
            if dist_to_start > start_radius_m:
                continue

            dist_track_start_to_target = haversine(meta["start_lat"], meta["start_lon"], target_lat, target_lon)
            dist_track_end_to_target = haversine(meta["end_lat"], meta["end_lon"], target_lat, target_lon)
            min_dist_to_target = min(dist_track_start_to_target, dist_track_end_to_target)

            candidates.append(
                {"filename": filename, "index": idx, "dist_to_start": dist_to_start, "dist_to_target": min_dist_to_target}
            )

            if self.verbose:
                logger.debug(
                    f"   Candidate: {filename}, "
                    f"Dist to start: {dist_to_start:.0f}m, "
                    f"Min-dist to target: {min_dist_to_target:.0f}m"
                )

        if not candidates:
            logger.warning("⚠️  No tracks found within radius!")
            return None, None, None

        # Sort by distance to target (primary), then by distance to start (secondary)
        best = min(candidates, key=lambda c: (c["dist_to_target"], c["dist_to_start"]))

        logger.info(f"✅ Selected start track: {best['filename']}")
        logger.debug(
            f"   📍 Start index: {best['index']}, "
            f"Dist to start: {best['dist_to_start']:.0f}m, "
            f"Dist to target: {best['dist_to_target']:.0f}m"
        )

        return best["filename"], best["index"], None

    def _find_target_pos(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
    ) -> tuple[str | None, int | None, float | None, float | None]:
        """Determines the target position and the relevant target side for the route search.

        This method implements the central logic for efficient routing:
        1. Finds the track closest to the target (within target_search_radius_km).
        2. Determines which side of this track (start or end) is closer to the start point.
        3. This "target side" becomes the reference for all intermediate steps.

        Args:
            start_lat: Latitude of the start point in decimal degrees.
            start_lon: Longitude of the start point in decimal degrees.
            target_lat: Latitude of the target point (accommodation) in decimal degrees.
            target_lon: Longitude of the target point (accommodation) in decimal degrees.

        Returns:
            Tuple of:
                - target_file (str): filename of the target GPX file.
                - target_index (int): index of the point closest to the target.
                - target_side_lat (float): latitude of the relevant target side.
                - target_side_lon (float): longitude of the relevant target side.
        """
        target_file = None
        target_index = None
        target_distance = float("inf")
        start_point = None
        end_point = None
        target_radius_m = self.target_search_radius_km * 1000

        for filename, meta in self.gpx_index.items():
            idx, dist = find_closest_point_in_track(meta["points"], target_lat, target_lon)
            if dist < target_distance and dist <= target_radius_m:
                target_distance = dist
                target_file = filename
                target_index = idx
                start_point = meta["points"][0]
                end_point = meta["points"][-1]

        if not target_file:
            logger.warning(f"⚠️  No target track found within {self.target_search_radius_km}km!")
            return None, None, None, None

        dist_to_start = haversine(start_lat, start_lon, start_point["lat"], start_point["lon"])
        dist_to_end = haversine(start_lat, start_lon, end_point["lat"], end_point["lon"])

        if dist_to_start < dist_to_end:
            target_side_lat = start_point["lat"]
            target_side_lon = start_point["lon"]
            logger.debug(f"🎯 Target track {target_file}: Start side closer to start location")
        else:
            target_side_lat = end_point["lat"]
            target_side_lon = end_point["lon"]
            logger.debug(f"🎯 Target track {target_file}: End side closer to start location")

        logger.debug(f"🎯 Target: {target_file} (Index {target_index}, Distance: {target_distance:.1f}m)")
        logger.debug(f"🎯 Target side position: ({target_side_lat:.6f}, {target_side_lon:.6f})")

        return target_file, target_index, target_side_lat, target_side_lon

    def _init_end_index(
        self,
        current_index: int,
        meta: dict[str, Any],
        force_direction: str,
        target_side_lat: float,
        target_side_lon: float,
    ) -> int:
        """Initializes the end index when the driving direction is forced (multi-day tour continuation).

        In multi-day tours, the direction from the previous day must be maintained.
        This method finds the point in the forced direction that is closest to
        the relevant target side.

        Args:
            current_index: Current starting index in the track.
            meta: Metadata of the current GPX track.
            force_direction: Forced direction - either 'forward' or 'backward'.
            target_side_lat: Latitude of the relevant target side.
            target_side_lon: Longitude of the relevant target side.

        Returns:
            Calculated end index in the track.
        """
        best_idx = current_index
        best_dist = float("inf")

        for point in meta["points"]:
            if force_direction == "forward" and point["index"] <= current_index:
                continue
            if force_direction == "backward" and point["index"] >= current_index:
                continue
            dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
            if dist < best_dist:
                best_dist = dist
                best_idx = point["index"]

        if self.verbose:
            direction_str = "Forward" if force_direction == "forward" else "Backward"
            logger.debug(f"   🔍 {direction_str} (forced): Index {best_idx} (Distance: {best_dist:.1f}m)")

        return best_idx

    def _set_end_index(
        self,
        current_index: int,
        meta: dict[str, Any],
        force_direction: str | None,
        target_side_lat: float,
        target_side_lon: float,
        iteration: int,
    ) -> int:
        """Determines the end index for the current track section.

        In the first iteration with a continuation from the previous day, the
        forced direction is used. In all other cases, the point in the entire
        track closest to the target side is searched (independent of the
        direction of travel).

        Args:
            current_index: Current starting index in the track.
            meta: Metadata of the current GPX track.
            force_direction: Optional forced direction ('forward'/'backward').
            target_side_lat: Latitude of the relevant target side.
            target_side_lon: Longitude of the relevant target side.
            iteration: Current iteration number (0-based).

        Returns:
            Calculated end index in the track.
        """
        if iteration == 0 and force_direction is not None:
            return self._init_end_index(current_index, meta, force_direction, target_side_lat, target_side_lon)
        else:
            idx, best_dist = find_closest_point_in_track(meta["points"], target_side_lat, target_side_lon)
            if self.verbose:
                logger.debug(f"   🔍 Closest point to target side: Index {idx} (Distance: {best_dist:.1f}m)")
            return idx

    def _get_statistics4track(
        self,
        meta: dict[str, Any],
        current_index: int,
        end_index: int,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
        total_descent: float,
        reversed_direction: bool,
    ) -> tuple[float, float, float, float]:
        """Calculates statistics for a track section between two indices.

        Args:
            meta: Metadata of the GPX track.
            current_index: Start index of the section.
            end_index: End index of the section.
            max_elevation: Previous max elevation in meters (will be updated).
            total_distance: Previous total distance in meters (will be updated).
            total_ascent: Previous total ascent in meters (will be updated).
            total_descent: Previous total descent in meters (will be updated).
            reversed_direction: If True, section is traversed backward.

        Returns:
            Tuple of (max_elevation, total_distance, total_ascent, total_descent)
            with updated values.
        """
        mystart_index = min(current_index, end_index)
        myend_index = max(current_index, end_index)

        gpx = read_gpx_file(meta["file"])
        if gpx:
            return get_statistics4track(
                gpx, mystart_index, myend_index, max_elevation, total_distance, total_ascent, total_descent, reversed_direction
            )
        return max_elevation, total_distance, total_ascent, total_descent

    def _find_next_gpx_file(
        self,
        visited: set[str],
        used_base_files: set[str],
        current_lat: float,
        current_lon: float,
    ) -> tuple[str | None, int | None]:
        """Finds the next GPX file in the route chain.

        Args:
            visited: Set of already visited filenames to avoid loops.
            used_base_files: Set of already used base filenames to prevent using
                            the same track in different directions.
            current_lat: Current latitude in decimal degrees.
            current_lon: Current longitude in decimal degrees.

        Returns:
            Tuple of:
                - next_file (str|None): filename of the next GPX file.
                - next_index (int|None): starting index in the next track.
        """
        next_file = None
        next_index = None
        best_dist = float("inf")
        best_length = float("inf")

        if self.verbose:
            logger.debug("   Searching for next GPX file...")

        for name, meta in self.gpx_index.items():
            if name in visited:
                continue
            if get_base_filename(name) in used_base_files:
                continue

            idx, dist = find_closest_point_in_track(meta["points"], current_lat, current_lon)

            if self.verbose:
                logger.debug(f"      {meta['total_distance_m']:.0f}m {name} {dist:.1f}m")

            if dist > self.max_connection_distance_m:
                continue

            length = meta["total_distance_m"]
            if dist < best_dist or (dist <= best_dist + 300 and length < best_length):
                best_dist = dist
                next_file = name
                next_index = idx
                best_length = length

        if next_file:
            logger.debug(f"   ➡️  Next: {next_file} (Index {next_index}, Distance: {best_dist:.1f}m)")

        return next_file, next_index

    def _process_route_iteration(
        self,
        iteration: int,
        current_file: str,
        current_index: int,
        target_file: str,
        target_index: int,
        visited: set[str],
        used_base_files: set[str],
        route_files: list[dict[str, Any]],
        force_direction: str | None,
        target_side_lat: float,
        target_side_lon: float,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
        total_descent: float,
    ) -> tuple[bool, str | None, int | None, float, float, float, float, float, float]:
        """Processes a single iteration of the route search (compatibility wrapper).

        Args:
            iteration: Current iteration number.
            current_file: Name of current GPX file.
            current_index: Current start index in the track.
            target_file: Name of target GPX file.
            target_index: Index of target point.
            visited: Set of visited files.
            used_base_files: Set of used base filenames.
            route_files: List of route segments.
            force_direction: Optional forced direction.
            target_side_lat: Latitude of target side.
            target_side_lon: Longitude of target side.
            max_elevation: Current max elevation.
            total_distance: Current total distance.
            total_ascent: Current total ascent.
            total_descent: Current total descent.

        Returns:
            Tuple with continue flag, next file/index, updated position and stats.
        """
        current = RoutePosition(file=current_file, index=current_index, lat=0, lon=0)
        target = RoutePosition(file=target_file, index=target_index, lat=target_side_lat, lon=target_side_lon)
        context = RouteContext(
            iteration=iteration,
            target=target,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=force_direction,
        )
        stats = RouteStatistics(
            max_elevation=max_elevation, total_distance=total_distance, total_ascent=total_ascent, total_descent=total_descent
        )

        should_continue, next_pos, updated_stats = self._process_route_iteration_new(current, context, stats)

        next_file = next_pos.file if next_pos else None
        next_index = next_pos.index if next_pos else None

        meta = self.gpx_index.get(current_file)
        if meta:
            if current_file == target_file:
                end_index = target_index
            else:
                end_index = self._set_end_index(
                    current_index, meta, force_direction, target_side_lat, target_side_lon, iteration
                )
            end_pt = meta["points"][end_index]
            current_lat, current_lon = end_pt["lat"], end_pt["lon"]
        else:
            current_lat, current_lon = 0, 0

        return (
            should_continue,
            next_file,
            next_index,
            current_lat,
            current_lon,
            updated_stats.max_elevation,
            updated_stats.total_distance,
            updated_stats.total_ascent,
            updated_stats.total_descent,
        )

    def _process_route_iteration_new(
        self,
        current: RoutePosition,
        context: RouteContext,
        stats: RouteStatistics,
    ) -> tuple[bool, RoutePosition | None, RouteStatistics]:
        """Processes a single iteration of the route search.

        Performs the following steps for a single track section:
        1. Validation (already visited? metadata available?)
        2. Determination of the end index (where to go in the track?)
        3. Determination of the travel direction (forward/backward)
        4. Update of statistics (distance, elevation)
        5. Search for the next track (if target not yet reached)

        Args:
            current: Current position in route calculation.
            context: Context for route iteration.
            stats: Accumulated route statistics.

        Returns:
            Tuple of:
                - should_continue (bool): True if more iterations are needed.
                - next_pos (RoutePosition|None): Next position to start from.
                - stats (RouteStatistics): Updated statistics.
        """
        # Validations
        if current.file in context.visited:
            logger.debug(f"⚠️  Iteration {context.iteration + 1}: File {current.file} already visited - aborting")
            return False, None, stats

        meta = self.gpx_index.get(current.file)
        if not meta:
            logger.debug(f"⚠️  Iteration {context.iteration + 1}: No metadata for {current.file} - aborting")
            return False, None, stats

        base_name = get_base_filename(current.file)
        if base_name in context.used_base_files:
            logger.debug(f"⚠️  Iteration {context.iteration + 1}: Base file {base_name} already used - aborting")
            return False, None, stats

        logger.debug(f"📁 Iteration {context.iteration + 1}: {current.file} (current index: {current.index})")

        # Determine end index
        if current.file == context.target.file:
            end_index = context.target.index
            logger.debug(f"   ✅ Target file reached! Going to index {end_index}")
            should_stop = True
        else:
            end_index = self._set_end_index(
                current.index, meta, context.force_direction, context.target.lat, context.target.lon, context.iteration
            )
            should_stop = False

        # Determine direction
        reversed_dir = current.index > end_index
        direction_str = "backward" if reversed_dir else "forward"
        logger.debug(f"   Direction: {direction_str} (Index {current.index} -> {end_index})")

        # Mark as visited
        context.visited.add(current.file)
        context.used_base_files.add(base_name)

        # Add to route
        context.route_files.append(
            {"file": current.file, "start_index": current.index, "end_index": end_index, "reversed": reversed_dir}
        )

        # Update statistics
        max_el, dist, asc, desc = self._get_statistics4track(
            meta,
            current.index,
            end_index,
            stats.max_elevation,
            stats.total_distance,
            stats.total_ascent,
            stats.total_descent,
            reversed_dir,
        )
        stats.max_elevation = max_el
        stats.total_distance = dist
        stats.total_ascent = asc
        stats.total_descent = desc

        # Update position
        end_pt = meta["points"][end_index]
        current_lat, current_lon = end_pt["lat"], end_pt["lon"]
        logger.debug(f"   New position: ({current_lat:.6f}, {current_lon:.6f})")

        if should_stop:
            print("✅ Target reached!")
            return False, None, stats

        # Find next GPX
        next_file, next_index = self._find_next_gpx_file(context.visited, context.used_base_files, current_lat, current_lon)

        if not next_file:
            logger.debug(f"⚠️  No suitable next GPX found (max distance: {self.max_connection_distance_m}m)")
            if context.target.file not in context.visited:
                self._add_target_track_to_route(
                    context.target.file, context.target.index, current_lat, current_lon, context.route_files
                )
            return False, None, stats

        next_pt = self.gpx_index[next_file]["points"][next_index]
        next_pos = RoutePosition(file=next_file, index=next_index, lat=next_pt["lat"], lon=next_pt["lon"])
        return True, next_pos, stats

    def _add_target_track_to_route(
        self,
        target_file: str,
        target_index: int,
        current_lat: float,
        current_lon: float,
        route_files: list[dict[str, Any]],
    ) -> None:
        """Adds the target track to the route when no intermediate track is found.

        This method is called when the automatic route search finds no more
        suitable intermediate tracks, but the target track has not yet been
        reached. The target track is then directly appended.

        Args:
            target_file: Filename of the target GPX file.
            target_index: Index of the target point (accommodation) in the target track.
            current_lat: Current latitude in decimal degrees.
            current_lon: Current longitude in decimal degrees.
            route_files: List of route dictionaries to be extended.
        """
        logger.debug(f"   ➕ Adding target track: {target_file}")
        meta = self.gpx_index[target_file]

        dist_to_start = haversine(current_lat, current_lon, meta["points"][0]["lat"], meta["points"][0]["lon"])
        dist_to_end = haversine(current_lat, current_lon, meta["points"][-1]["lat"], meta["points"][-1]["lon"])

        if dist_to_end < dist_to_start:
            start_idx = len(meta["points"]) - 1
            reversed_dir = True
        else:
            start_idx = 0
            reversed_dir = False

        route_files.append(
            {
                "file": target_file,
                "start_index": min(start_idx, target_index) if not reversed_dir else max(start_idx, target_index),
                "end_index": target_index,
                "reversed": reversed_dir,
            }
        )

    def collect_route_between_locations(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
        booking: dict[str, Any],
        previous_last_file: dict[str, Any] | None = None,
    ) -> None:
        """Calculates and chains GPX files between start and target locations.

        This is the main method for route planning. It implements an intelligent
        algorithm for chaining multiple GPX tracks.

        Args:
            start_lat: Latitude of the start location.
            start_lon: Longitude of the start location.
            target_lat: Latitude of the target location (accommodation).
            target_lon: Longitude of the target location (accommodation).
            booking: Booking/Day dictionary to be enriched with route information.
            previous_last_file: Optional. Dictionary of the last used GPX file
                               from the previous day.
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Route search: ({start_lat:.6f}, {start_lon:.6f}) -> ({target_lat:.6f}, {target_lon:.6f})")
        if previous_last_file:
            logger.info(f"🔗 Continuation from: {previous_last_file['file']} (Index {previous_last_file['end_index']})")
        logger.info(f"{'=' * 80}")

        start_file, start_idx, force_dir = self._find_start_pos(
            start_lat, start_lon, target_lat, target_lon, previous_last_file
        )
        target_file, target_idx, target_side_lat, target_side_lon = self._find_target_pos(
            start_lat, start_lon, target_lat, target_lon
        )

        if not start_file or not target_file:
            logger.warning("⚠️  No matching GPX files found!")
            booking.update({"gpx_files": [], "total_distance_km": 0, "total_ascent_m": 0, "max_elevation_m": None})
            return

        start_pt = self.gpx_index[start_file]["points"][start_idx]
        start_pos = RoutePosition(file=start_file, index=start_idx, lat=start_pt["lat"], lon=start_pt["lon"])
        target_pos = RoutePosition(file=target_file, index=target_idx, lat=target_side_lat, lon=target_side_lon)

        context = RouteContext(iteration=0, target=target_pos, force_direction=force_dir)
        stats = RouteStatistics()
        current_pos = start_pos

        for i in range(self.max_chain_length):
            context.iteration = i
            should_continue, current_pos, stats = self._process_route_iteration_new(current_pos, context, stats)
            if not should_continue:
                break

        logger.info("\n📊 Summary:")
        logger.info(f"   Files: {len(context.route_files)}")
        logger.info(f"   Total distance: {stats.total_distance / 1000:.2f} km")
        logger.info(f"   Total ascent: {stats.total_ascent:.0f} m")
        logger.info(f"   Max elevation: {stats.max_elevation:.0f} m" if stats.max_elevation != 0 else "   Max elevation: N/A")
        logger.info(f"{'=' * 80}\n")

        booking["gpx_files"] = context.route_files
        booking["total_distance_km"] = round(stats.total_distance / 1000, 2)
        booking["total_ascent_m"] = int(round(stats.total_ascent))
        booking["total_descent_m"] = int(round(stats.total_descent))
        booking["max_elevation_m"] = int(round(stats.max_elevation)) if stats.max_elevation != 0 else None

        if context.route_files:
            last = context.route_files[-1]
            booking["_last_gpx_file"] = {"file": last["file"], "end_index": last["end_index"], "reversed": last["reversed"]}

    def merge_gpx_files(self, route_files: list[dict[str, Any]], output_dir: Path, booking: dict[str, Any]) -> Path | None:
        """Merges multiple GPX track segments into a single GPX file.

        Args:
            route_files: List of dictionaries with track section information.
            output_dir: Output directory for the merged GPX file.
            booking: Booking dictionary for filename generation.

        Returns:
            Path to the written GPX file or None on error.
        """
        if not route_files:
            logger.warning(f"route_files is empty or None: {route_files}")
            return None

        merged_gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        merged_gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for i, entry in enumerate(route_files):
            if i == len(route_files) - 1 and entry.get("is_to_hotel"):
                gpx_file = output_dir / entry["file"]
            else:
                gpx_file = self.gpx_dir / entry["file"]
                if not gpx_file.exists():
                    gpx_file = output_dir / entry["file"]

            if not gpx_file.exists():
                logger.warning(f"⚠️  File not found: {entry['file']}")
                continue

            gpx = read_gpx_file(gpx_file)
            if not gpx or not gpx.tracks:
                continue

            s_idx, e_idx = entry["start_index"], entry["end_index"]
            rev = entry["reversed"]
            if rev:
                s_idx, e_idx = e_idx, s_idx

            all_pts = []
            cnt = 0
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for p in seg.points:
                        if s_idx <= cnt <= e_idx:
                            all_pts.append(p)
                        cnt += 1

            if rev:
                all_pts = all_pts[::-1]

            for p in all_pts:
                segment.points.append(gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, elevation=p.elevation, time=p.time))

        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = booking.get("arrival_date", "unknown_date")
        hotel_name = booking.get("hotel_name", "unknown_hotel")
        hotel_name_clean = "".join(c for c in hotel_name if c.isalnum() or c in (" ", "-", "_")).strip()
        hotel_name_clean = hotel_name_clean.replace(" ", "_")[:30]

        out_name = f"{date_str}_{hotel_name_clean}_merged.gpx"
        out_path = output_dir / out_name
        out_path.write_text(merged_gpx.to_xml(), encoding="utf-8")

        booking["gpx_track_final"] = out_name
        logger.info(f"💾 Merged GPX saved: {out_path.name}")

        return out_path

    def process_all_bookings(self, bookings: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
        """Processes all bookings and creates GPS tracks for each day."""
        bookings_sorted = sorted(bookings, key=lambda x: str(x.get("arrival_date", "9999-12-31")))
        prev_lat = prev_lon = None
        prev_last = None

        for booking in tqdm(bookings_sorted, desc="Processing bookings"):
            logger.debug(booking.get("hotel_name"))
            lat, lon = booking.get("latitude"), booking.get("longitude")
            if prev_lat is not None and lat is not None:
                self.collect_route_between_locations(prev_lat, prev_lon, lat, lon, booking, previous_last_file=prev_last)
                self.extend_track2hotel(booking, output_dir)
                self.merge_gpx_files(booking.get("gpx_files", []), output_dir, booking)
                prev_last = booking.get("_last_gpx_file")
            prev_lat, prev_lon = lat, lon

        return bookings_sorted

    def extend_track2hotel(self, booking: dict[str, Any], output_path: Path) -> Path | None:
        """Extends the route to the hotel using BRouter."""
        if not booking.get("gpx_files") or "latitude" not in booking:
            if "gpx_files" not in booking or not booking["gpx_files"]:
                logger.warning("⚠️  No previous route available - cannot extend to accommodation")
            else:
                logger.warning("⚠️  No hotel coordinates available")
            return None

        try:
            last_seg = booking["gpx_files"][-1]
            gpx_file = self.gpx_dir / last_seg["file"]
            if not gpx_file.exists():
                gpx_file = output_path / last_seg["file"]

            gpx = read_gpx_file(gpx_file)
            if not gpx:
                logger.error(f"Could not read {gpx_file.name}")
                return None

            extended_gpx = gpxpy.gpx.GPX()
            track = gpxpy.gpx.GPXTrack()
            extended_gpx.tracks.append(track)
            segment = gpxpy.gpx.GPXTrackSegment()
            track.segments.append(segment)

            s_idx, e_idx, rev = last_seg.get("start_index", 0), last_seg["end_index"], last_seg.get("reversed", False)
            pts = []
            cnt = 0
            m_idx, ma_idx = min(s_idx, e_idx), max(s_idx, e_idx)
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for p in seg.points:
                        if m_idx <= cnt <= ma_idx:
                            pts.append(p)
                        cnt += 1
            if rev:
                pts = pts[::-1]

            for p in pts:
                segment.points.append(gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, elevation=p.elevation, time=p.time))

            new_pts = get_route2address_as_points(
                pts[-1].latitude, pts[-1].longitude, booking["latitude"], booking["longitude"]
            )
            for p in new_pts:
                segment.points.append(gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, elevation=p.elevation, time=p.time))

            output_path.mkdir(parents=True, exist_ok=True)
            date_str = booking.get("arrival_date", "unknown_date")
            hotel_name = booking.get("hotel_name", "unknown_hotel")
            hotel_name_clean = "".join(c for c in hotel_name if c.isalnum() or c in (" ", "-", "_")).strip()
            hotel_name_clean = hotel_name_clean.replace(" ", "_")[:30]

            out_name = f"{date_str}_{hotel_name_clean}_to_hotel.gpx"
            out_file = output_path / out_name
            out_file.write_text(extended_gpx.to_xml(), encoding="utf-8")

            booking["gpx_files"][-1] = {
                "file": out_name,
                "start_index": 0,
                "end_index": len(segment.points) - 1,
                "reversed": False,
                "is_to_hotel": True,
            }
            booking["_last_gpx_file"] = {"file": out_name, "end_index": len(segment.points) - 1, "reversed": False}

            logger.info(f"   ✅ Hotel point added. Total: {len(segment.points)} points")
            logger.info(f"   💾 Saved as: {out_name}")

            return out_file
        except Exception as e:
            logger.error(f"❌ Error extending route: {e}")
            return None

    def _update_gpx_index_entry(self, old_filename: str, new_gpx_file: Path) -> None:
        """Updates a single entry in the GPX index with a new file.

        Args:
            old_filename: Filename of the entry to be replaced.
            new_gpx_file: Path to the new GPX file.
        """
        if old_filename in self.gpx_index:
            del self.gpx_index[old_filename]
            logger.debug(f"   🗑️  Old entry '{old_filename}' removed from index")

        gpx = read_gpx_file(new_gpx_file)
        if not gpx or not gpx.tracks:
            logger.warning(f"   ⚠️  Could not read new file '{new_gpx_file.name}'")
            return

        total_distance = 0.0
        total_ascent = 0.0
        max_elevation = float("-inf")
        first_point = None
        last_point = None
        all_points = []
        point_index = 0

        for track in gpx.tracks:
            for seg in track.segments:
                prev = None
                for p in seg.points:
                    if first_point is None:
                        first_point = p
                    last_point = p
                    all_points.append({"lat": p.latitude, "lon": p.longitude, "elevation": p.elevation, "index": point_index})
                    point_index += 1
                    if p.elevation is not None:
                        max_elevation = max(max_elevation, p.elevation)
                    if prev:
                        d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
                        total_distance += d
                        if prev.elevation is not None and p.elevation is not None and p.elevation > prev.elevation:
                            total_ascent += p.elevation - prev.elevation
                    prev = p

        if first_point and last_point:
            self.gpx_index[new_gpx_file.name] = {
                "file": new_gpx_file,
                "start_lat": first_point.latitude,
                "start_lon": first_point.longitude,
                "end_lat": last_point.latitude,
                "end_lon": last_point.longitude,
                "total_distance_m": total_distance,
                "total_ascent_m": total_ascent,
                "max_elevation_m": (int(round(max_elevation)) if max_elevation != float("-inf") else None),
                "points": all_points,
            }
            logger.info(f"   ✅ New entry '{new_gpx_file.name}' added to index")
            logger.debug(f"      Points: {len(all_points)}, Distance: {total_distance / 1000:.2f} km")
