import gpxpy
import math
from pathlib import Path
from typing import Dict, Optional, List, Tuple

GPXIndex = Dict[str, Dict]
PointDict = Dict[str, float]
StartPosResult = Tuple[Optional[str], Optional[int], Optional[str]]
TargetPosResult = Tuple[Optional[str], Optional[int], Optional[float], Optional[float]]
TrackStats = Tuple[float, float, float]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Berechnet die Distanz zwischen zwei Koordinaten in Metern.

    Args:
        lat1: Breitengrad Punkt 1
        lon1: Längengrad Punkt 1
        lat2: Breitengrad Punkt 2
        lon2: Längengrad Punkt 2

    Returns:
        Distanz in Metern
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_gpx_file(gpx_file: Path) -> Optional[gpxpy.gpx.GPX]:
    """Liest eine GPX-Datei mit robustem Encoding-Handling.

    Args:
        gpx_file: Pfad zur GPX-Datei

    Returns:
        Geparste GPX-Datei oder None bei Fehler
    """
    # Versuche verschiedene Encoding-Strategien
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            content = gpx_file.read_text(encoding=encoding)

            # Entferne BOM falls vorhanden
            if content.startswith("\ufeff"):
                content = content[1:]

            # Entferne führende Whitespaces/Newlines
            content = content.lstrip()

            # Parse GPX
            gpx = gpxpy.parse(content)
            return gpx

        except (UnicodeDecodeError, gpxpy.gpx.GPXXMLSyntaxException):
            continue
        except Exception as e:
            print(f"Unerwarteter Fehler beim Lesen von {gpx_file.name}: {e}")
            continue

    # Wenn alle Encodings fehlschlagen, versuche binär zu lesen
    try:
        with open(gpx_file, "rb") as f:
            content = f.read()

        # Versuche UTF-8 mit Fehlerbehandlung
        text = content.decode("utf-8", errors="ignore")

        # Entferne BOM
        if text.startswith("\ufeff"):
            text = text[1:]

        text = text.lstrip()

        return gpxpy.parse(text)

    except Exception as e:
        print(f"Fehler beim Parsen von {gpx_file.name}: {e}")
        return None


def get_base_filename(filename: str) -> str:
    """Extrahiert den Basis-Dateinamen ohne Richtungssuffix.

    Entfernt Suffixe wie '_inverted', '_reversed', '_rev' etc.

    Args:
        filename: GPX-Dateiname

    Returns:
        Basis-Dateiname ohne Richtungsinformationen
    """
    # Entferne häufige Suffixe für invertierte Tracks
    for suffix in ["_inverted", "_reversed", "_rev", "_inverse", "_backward"]:
        if filename.lower().endswith(f"{suffix}.gpx"):
            return filename[: -len(suffix) - 4] + ".gpx"

    return filename


def find_closest_point_in_track(points: List[Dict], target_lat: float, target_lon: float) -> Tuple[int, float]:
    """Findet den nächsten Punkt innerhalb eines Tracks.

    Args:
        points: Liste von Punkt-Dictionaries mit 'lat', 'lon', 'index'
        target_lat: Ziel-Breitengrad
        target_lon: Ziel-Längengrad

    Returns:
        Tuple (index des nächsten Punkts, Distanz in Metern)
    """
    best_idx = None
    best_dist = float("inf")

    for point in points:
        d = haversine(target_lat, target_lon, point["lat"], point["lon"])
        if d < best_dist:
            best_dist = d
            best_idx = point["index"]

    return best_idx, best_dist


class GPXRouteManager:
    """Verwaltet GPX-Routen und ermöglicht die Verkettung von Tracks zwischen Standorten.

    Diese Klasse bietet Funktionen zum:
    - Vorverarbeiten von GPX-Dateien in einem Verzeichnis
    - Finden von optimalen Routen zwischen zwei Koordinaten
    - Zusammenführen mehrerer GPX-Tracks zu einer Route
    - Berechnen von Statistiken (Distanz, Höhenmeter, etc.)

    Attributes:
        gpx_dir: Verzeichnis mit GPX-Dateien
        gpx_index: Vorverarbeitete Metadaten aller GPX-Dateien
        max_connection_distance_m: Maximale Distanz für Track-Verkettung
        max_chain_length: Maximale Anzahl zu verkettender Tracks
    """

    def __init__(
        self,
        gpx_dir: Path,
        max_connection_distance_m: float = 1000.0,
        max_chain_length: int = 20,
    ):
        """Initialisiert den GPXRouteManager.

        Args:
            gpx_dir: Verzeichnis mit GPX-Dateien
            max_connection_distance_m: Maximale Distanz für Track-Verkettung in Metern
            max_chain_length: Maximale Anzahl zu verkettender Tracks
        """
        self.gpx_dir = gpx_dir
        self.max_connection_distance_m = max_connection_distance_m
        self.max_chain_length = max_chain_length
        self.gpx_index = self._preprocess_gpx_directory()

    def _preprocess_gpx_directory(self) -> GPXIndex:
        """Liest alle GPX-Dateien genau einmal ein und speichert relevante Metadaten.

        Returns:
            Dictionary mit Dateinamen als Key und Metadaten als Value:
                - file (Path)
                - start_lat, start_lon
                - end_lat, end_lon
                - total_distance_m
                - total_ascent_m
                - max_elevation_m
                - points: Liste aller Punkte mit (lat, lon, elevation, index)
        """
        gpx_index: GPXIndex = {}

        for gpx_file in Path(self.gpx_dir).glob("*.gpx"):
            gpx = read_gpx_file(gpx_file)
            if gpx is None or not gpx.tracks:
                continue

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

                        # Speichere alle Punkte mit Index
                        all_points.append(
                            {"lat": p.latitude, "lon": p.longitude, "elevation": p.elevation, "index": point_index}
                        )
                        point_index += 1

                        if p.elevation is not None:
                            max_elevation = max(max_elevation, p.elevation)

                        if prev:
                            d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
                            total_distance += d

                            if prev.elevation is not None and p.elevation is not None and p.elevation > prev.elevation:
                                total_ascent += p.elevation - prev.elevation
                        prev = p

            if first_point is None or last_point is None:
                continue

            gpx_index[gpx_file.name] = {
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

        return gpx_index

    def _find_start_pos(
        self,
        start_lat: float,
        start_lon: float,
        previous_last_file: Optional[Dict],
    ) -> StartPosResult:
        """Bestimmt die Startposition in den GPX-Daten.

        Berücksichtigt optional eine Fortsetzung aus der vorherigen Route
        und erzwingt dabei ggf. die Fahrtrichtung.

        Args:
            start_lat: Breitengrad des Startpunkts.
            start_lon: Längengrad des Startpunkts.
            previous_last_file: Letzte verwendete GPX-Datei mit Endindex und Richtung.

        Returns:
            Tuple aus (Dateiname, Startindex, erzwungene Richtung).
        """
        start_file = None
        start_index = None
        start_distance = float("inf")
        force_direction = None

        for filename, meta in self.gpx_index.items():
            if previous_last_file and filename == previous_last_file["file"]:
                start_file = filename
                start_index = previous_last_file["end_index"]
                last_point = meta["points"][start_index]
                start_distance = haversine(start_lat, start_lon, last_point["lat"], last_point["lon"])

                force_direction = "backward" if previous_last_file.get("reversed", False) else "forward"

                print(f"🔗 Fortsetzung erkannt: {start_file} ab Index {start_index}")
                print(f"🔗 Erzwungene Richtung: {force_direction} (vom Vortag)")
                break
            else:
                idx, dist = find_closest_point_in_track(meta["points"], start_lat, start_lon)
                if dist < start_distance:
                    start_distance = dist
                    start_file = filename
                    start_index = idx

        print(f"📍 Start: {start_file} (Index {start_index}, Distanz: {start_distance:.1f}m)")

        return start_file, start_index, force_direction

    def _find_target_pos(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
    ) -> TargetPosResult:
        """Bestimmt die Zielposition in den GPX-Daten.

        Zusätzlich wird ermittelt, welche Seite des Ziel-Tracks
        näher am Startpunkt liegt.

        Args:
            start_lat: Breitengrad des Startpunkts.
            start_lon: Längengrad des Startpunkts.
            target_lat: Breitengrad des Zielpunkts.
            target_lon: Längengrad des Zielpunkts.

        Returns:
            Tuple aus (Dateiname, Zielindex, Breitengrad der Ziel-Seite,
            Längengrad der Ziel-Seite).
        """
        target_file = None
        target_index = None
        target_distance = float("inf")
        start_point = None
        end_point = None

        for filename, meta in self.gpx_index.items():
            idx, dist = find_closest_point_in_track(meta["points"], target_lat, target_lon)
            if dist < target_distance:
                target_distance = dist
                target_file = filename
                target_index = idx

                start_point = meta["points"][0]
                end_point = meta["points"][-1]

        dist_to_start = haversine(start_lat, start_lon, start_point["lat"], start_point["lon"])
        dist_to_end = haversine(start_lat, start_lon, end_point["lat"], end_point["lon"])

        if dist_to_start < dist_to_end:
            target_side_lat = start_point["lat"]
            target_side_lon = start_point["lon"]
            print(f"🎯 Ziel-Track {target_file}: Start-Seite näher am Startort")
        else:
            target_side_lat = end_point["lat"]
            target_side_lon = end_point["lon"]
            print(f"🎯 Ziel-Track {target_file}: End-Seite näher am Startort")

        print(f"🎯 Ziel: {target_file} (Index {target_index}, Distanz: {target_distance:.1f}m)")
        print(f"🎯 Ziel-Seite Position: ({target_side_lat:.6f}, {target_side_lon:.6f})")
        print()

        return target_file, target_index, target_side_lat, target_side_lon

    def _init_end_index(
        self,
        current_index: int,
        meta: Dict,
        force_direction: str,
        target_side_lat: float,
        target_side_lon: float,
    ) -> int:
        """Initialisiert den Endindex bei erzwungener Fahrtrichtung.

        Args:
            current_index: Aktueller Startindex im Track.
            meta: Metadaten des aktuellen GPX-Tracks.
            force_direction: Erzwungene Richtung ('forward' oder 'backward').
            target_side_lat: Breitengrad der relevanten Ziel-Seite.
            target_side_lon: Längengrad der relevanten Ziel-Seite.

        Returns:
            Berechneter Endindex im Track.
        """
        if force_direction == "forward":
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                if point["index"] <= current_index:
                    continue
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Vorwärts (erzwungen): Index {end_index} (Distanz: {best_dist:.1f}m)")

        else:  # backward
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                if point["index"] >= current_index:
                    continue
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Rückwärts (erzwungen): Index {end_index} (Distanz: {best_dist:.1f}m)")

        return end_index

    def _set_end_index(
        self,
        current_index: int,
        meta: Dict,
        force_direction: Optional[str],
        target_side_lat: float,
        target_side_lon: float,
        iteration: int,
    ) -> int:
        """Bestimmt den Endindex für den aktuellen Track.

        Args:
            current_index: Aktueller Startindex.
            meta: Metadaten des aktuellen GPX-Tracks.
            force_direction: Optional erzwungene Richtung.
            target_side_lat: Breitengrad der Ziel-Seite.
            target_side_lon: Längengrad der Ziel-Seite.
            iteration: Aktuelle Iterationsnummer.

        Returns:
            Berechneter Endindex im Track.
        """
        if iteration == 0 and force_direction is not None:
            end_index = self._init_end_index(current_index, meta, force_direction, target_side_lat, target_side_lon)
        else:
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Nächster Punkt zur Ziel-Seite: Index {end_index} (Distanz: {best_dist:.1f}m)")

        return end_index

    def _get_statistics4track(
        self,
        meta: Dict,
        current_index: int,
        end_index: int,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
        reversed_direction: bool,
    ) -> TrackStats:
        """Berechnet Statistiken für einen Track-Abschnitt.

        Args:
            meta: Metadaten des GPX-Tracks.
            current_index: Startindex des Abschnitts.
            end_index: Endindex des Abschnitts.
            max_elevation: Bisherige maximale Höhe.
            total_distance: Bisherige Gesamtdistanz in Metern.
            total_ascent: Bisheriger Gesamtanstieg in Metern.
            reversed_direction: Ob der Track rückwärts durchlaufen wird.

        Returns:
            Tuple aus (maximale Höhe, Gesamtdistanz, Gesamtanstieg).
        """
        mystart_index = min(current_index, end_index)
        myend_index = max(current_index, end_index)

        gpx = read_gpx_file(meta["file"])
        if gpx:
            segment_points = []
            point_counter = 0
            for track in gpx.tracks:
                for seg in track.segments:
                    if reversed_direction:
                        for p in seg.points[::-1]:
                            if mystart_index <= point_counter <= myend_index:
                                segment_points.append(p)
                            point_counter += 1
                    else:
                        for p in seg.points:
                            if mystart_index <= point_counter <= myend_index:
                                segment_points.append(p)
                            point_counter += 1

            prev = None
            for p in segment_points:
                if p.elevation is not None:
                    max_elevation = max(max_elevation, p.elevation)

                if prev:
                    d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
                    total_distance += d

                    if prev.elevation is not None and p.elevation is not None and p.elevation > prev.elevation:
                        total_ascent += p.elevation - prev.elevation
                prev = p

        print(f"   Punkte: {myend_index - mystart_index + 1}")

        return max_elevation, total_distance, total_ascent

    def _find_next_gpx_file(
        self,
        visited: set,
        used_base_files: set,
        current_lat: float,
        current_lon: float,
    ) -> Tuple[Optional[str], Optional[int]]:
        """Findet die nächste GPX-Datei in der Routenkette.

        Args:
            visited: Set mit bereits besuchten Dateinamen.
            used_base_files: Set mit bereits verwendeten Basis-Dateinamen.
            current_lat: Aktueller Breitengrad.
            current_lon: Aktueller Längengrad.

        Returns:
            Tuple aus (Dateiname der nächsten GPX-Datei, Startindex) oder (None, None).
        """
        next_file = None
        next_index = None
        best_dist = None
        length_best_file = float("inf")

        print("   Suche nächste GPX-Datei...")
        for name, cand in self.gpx_index.items():
            if name in visited:
                continue

            cand_base = get_base_filename(name)
            if cand_base in used_base_files:
                continue

            length_file = cand["total_distance_m"]

            idx, dist = find_closest_point_in_track(cand["points"], current_lat, current_lon)

            print(length_file, name, dist)

            if dist > self.max_connection_distance_m:
                continue

            if best_dist is None or dist < best_dist or (dist <= best_dist + 300 and length_file < length_best_file):
                best_dist = dist
                next_file = name
                next_index = idx
                length_best_file = length_file

        if next_file:
            print(f"   ➡️  Nächste: {next_file} (Index {next_index}, Distanz: {best_dist:.1f}m)")
            print()

        return next_file, next_index

    def _add_target_track_to_route(
        self,
        target_file: str,
        target_index: int,
        current_lat: float,
        current_lon: float,
        route_files: List[Dict],
    ) -> None:
        """Fügt den Ziel-Track zur Route hinzu.

        Args:
            target_file: Dateiname der Ziel-GPX-Datei.
            target_index: Index des Zielpunkts im Ziel-Track.
            current_lat: Aktueller Breitengrad.
            current_lon: Aktueller Längengrad.
            route_files: Liste von Route-Dictionaries die erweitert wird (in-place).
        """
        print(f"   ➕ Füge Ziel-Track hinzu: {target_file}")

        target_meta = self.gpx_index[target_file]
        target_start_idx = 0
        target_end_idx = target_index

        dist_to_start = haversine(current_lat, current_lon, target_meta["points"][0]["lat"], target_meta["points"][0]["lon"])
        dist_to_end = haversine(current_lat, current_lon, target_meta["points"][-1]["lat"], target_meta["points"][-1]["lon"])

        if dist_to_end < dist_to_start:
            target_start_idx = len(target_meta["points"]) - 1
            target_end_idx = target_index
            reversed_dir = True
        else:
            target_start_idx = 0
            target_end_idx = target_index
            reversed_dir = False

        if reversed_dir:
            route_files.append(
                {
                    "file": target_file,
                    "end_index": min(target_start_idx, target_end_idx),
                    "start_index": max(target_start_idx, target_end_idx),
                    "reversed": reversed_dir,
                }
            )
        else:
            route_files.append(
                {
                    "file": target_file,
                    "start_index": min(target_start_idx, target_end_idx),
                    "end_index": max(target_start_idx, target_end_idx),
                    "reversed": reversed_dir,
                }
            )

    def _process_route_iteration(
        self,
        iteration: int,
        current_file: str,
        current_index: int,
        target_file: str,
        target_index: int,
        visited: set,
        used_base_files: set,
        route_files: List[Dict],
        force_direction: Optional[str],
        target_side_lat: float,
        target_side_lon: float,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
    ) -> Tuple[bool, Optional[str], Optional[int], float, float, float, float, float]:
        """Verarbeitet eine einzelne Iteration der Routensuche.

        Args:
            iteration: Aktuelle Iterationsnummer (0-basiert).
            current_file: Name der aktuellen GPX-Datei.
            current_index: Aktueller Startindex im Track.
            target_file: Name der Ziel-GPX-Datei.
            target_index: Index des Zielpunkts im Ziel-Track.
            visited: Set mit bereits besuchten Dateinamen (wird modifiziert).
            used_base_files: Set mit bereits verwendeten Basis-Dateinamen (wird modifiziert).
            route_files: Liste von Route-Dictionaries (wird erweitert).
            force_direction: Optional erzwungene Richtung.
            target_side_lat: Breitengrad der Ziel-Seite.
            target_side_lon: Längengrad der Ziel-Seite.
            max_elevation: Bisherige maximale Höhe in Metern.
            total_distance: Bisherige Gesamtdistanz in Metern.
            total_ascent: Bisheriger Gesamtanstieg in Metern.

        Returns:
            Tuple aus (should_continue, next_file, next_index, current_lat, current_lon,
            max_elevation, total_distance, total_ascent).
        """
        # Validierungen
        if current_file in visited:
            print(f"⚠️  Iteration {iteration + 1}: Datei {current_file} bereits besucht - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        meta = self.gpx_index.get(current_file)
        if meta is None:
            print(f"⚠️  Iteration {iteration + 1}: Keine Metadaten für {current_file} - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        base_name = get_base_filename(current_file)
        if base_name in used_base_files:
            print(f"⚠️  Iteration {iteration + 1}: Basis-Datei {base_name} bereits verwendet - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        print(f"📁 Iteration {iteration + 1}: {current_file} (aktueller Index: {current_index})")

        # Bestimme Endindex
        if current_file == target_file:
            end_index = target_index
            print(f"   ✅ Zieldatei erreicht! Fahre zu Index {end_index}")
        else:
            end_index = self._set_end_index(current_index, meta, force_direction, target_side_lat, target_side_lon, iteration)

        # Bestimme Richtung
        if current_index <= end_index:
            reversed_direction = False
            direction_str = "vorwärts"
        else:
            reversed_direction = True
            direction_str = "rückwärts"

        print(f"   Richtung: {direction_str} (Index {current_index} -> {end_index})")

        # Markiere als besucht
        visited.add(current_file)
        used_base_files.add(base_name)

        # Füge zur Route hinzu
        route_files.append(
            {"file": current_file, "start_index": current_index, "end_index": end_index, "reversed": reversed_direction}
        )

        # Berechne Statistiken
        max_elevation, total_distance, total_ascent = self._get_statistics4track(
            meta, current_index, end_index, max_elevation, total_distance, total_ascent, reversed_direction
        )

        # Aktualisiere Position
        end_point = meta["points"][end_index]
        current_lat = end_point["lat"]
        current_lon = end_point["lon"]

        print(f"   Neue Position: ({current_lat:.6f}, {current_lon:.6f})")

        # Prüfe ob Ziel erreicht
        if current_file == target_file:
            print("✅ Ziel erreicht!")
            return False, None, None, current_lat, current_lon, max_elevation, total_distance, total_ascent

        # Finde nächste GPX
        next_file, next_index = self._find_next_gpx_file(visited, used_base_files, current_lat, current_lon)

        if next_file is None:
            print(f"⚠️  Keine passende nächste GPX gefunden (max. Distanz: {self.max_connection_distance_m}m)")

            if target_file not in visited:
                self._add_target_track_to_route(target_file, target_index, current_lat, current_lon, route_files)
            return False, None, None, current_lat, current_lon, max_elevation, total_distance, total_ascent

        return True, next_file, next_index, current_lat, current_lon, max_elevation, total_distance, total_ascent

    def collect_route_between_locations(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
        booking: Dict,
        previous_last_file: Optional[Dict] = None,
    ) -> None:
        """Sammelt und verkettet GPX-Dateien zwischen Start- und Zielort.

        Die Funktion arbeitet rückwärts vom Ziel zum Start:
        1. Findet die Seite des Ziel-Tracks die näher am Start ist
        2. Findet im Start-Track den Punkt der dieser Ziel-Seite am nächsten ist
        3. Fährt nur bis zu diesem Punkt
        4. Sucht von dort den nächsten Track
        5. Wiederholt dies bis zum Ziel

        Args:
            start_lat: Breitengrad des Startorts.
            start_lon: Längengrad des Startorts.
            target_lat: Breitengrad des Zielorts.
            target_lon: Längengrad des Zielorts.
            booking: Buchungs-/Tages-Dictionary zum Anreichern.
            previous_last_file: Dict mit 'file', 'end_index' der letzten Datei.
        """
        print(f"\n{'=' * 80}")
        print(f"Route-Suche: ({start_lat:.6f}, {start_lon:.6f}) -> ({target_lat:.6f}, {target_lon:.6f})")
        if previous_last_file:
            print(f"🔗 Fortsetzung von: {previous_last_file['file']} (Index {previous_last_file['end_index']})")
        print(f"{'=' * 80}")

        # 1. Finde Start-Position
        start_file, start_index, force_direction = self._find_start_pos(start_lat, start_lon, previous_last_file)

        # 2. Finde Ziel-Position UND welche Seite des Ziel-Tracks näher am Start ist
        target_file, target_index, target_side_lat, target_side_lon = self._find_target_pos(
            start_lat, start_lon, target_lat, target_lon
        )

        if not start_file or not target_file:
            print("⚠️  Keine passenden GPX-Dateien gefunden!")
            booking["gpx_files"] = []
            booking["total_distance_km"] = 0
            booking["total_ascent_m"] = 0
            booking["max_elevation_m"] = None
            return

        visited = set()
        used_base_files = set()
        route_files = []

        current_file = start_file
        current_index = start_index

        total_distance = 0.0
        total_ascent = 0.0
        max_elevation = float("-inf")

        # Hauptschleife: Fahre von Start Richtung Ziel
        for iteration in range(self.max_chain_length):
            should_continue, next_file, next_index, current_lat, current_lon, max_elevation, total_distance, total_ascent = (
                self._process_route_iteration(
                    iteration=iteration,
                    current_file=current_file,
                    current_index=current_index,
                    target_file=target_file,
                    target_index=target_index,
                    visited=visited,
                    used_base_files=used_base_files,
                    route_files=route_files,
                    force_direction=force_direction,
                    target_side_lat=target_side_lat,
                    target_side_lon=target_side_lon,
                    max_elevation=max_elevation,
                    total_distance=total_distance,
                    total_ascent=total_ascent,
                )
            )

            if not should_continue:
                break

            current_file = next_file
            current_index = next_index

        print("\n📊 Zusammenfassung:")
        print(f"   Dateien: {len(route_files)}")
        print(f"   Gesamt-Distanz: {total_distance / 1000:.2f} km")
        print(f"   Gesamt-Aufstieg: {total_ascent:.0f} m")
        print(f"   Max. Höhe: {max_elevation:.0f} m" if max_elevation != float("-inf") else "   Max. Höhe: N/A")
        print(f"{'=' * 80}\n")

        booking["gpx_files"] = route_files
        booking["total_distance_km"] = round(total_distance / 1000, 2)
        booking["total_ascent_m"] = int(round(total_ascent))
        booking["max_elevation_m"] = int(round(max_elevation)) if max_elevation != float("-inf") else None

        # Speichere letzte Datei für nächste Suche
        if route_files:
            last = route_files[-1]
            booking["_last_gpx_file"] = {
                "file": last["file"],
                "end_index": last["end_index"],
                "reversed": last["reversed"],
            }

    def merge_gpx_files(self, route_files: List[Dict], output_dir: Path, booking: Dict) -> Optional[Path]:
        """Merged mehrere GPX-Dateien zu einem einzelnen GPX-Track.

        Berücksichtigt Start- und End-Indizes für Teilstrecken.

        Args:
            route_files: Liste von Dicts mit Keys:
                - file: GPX-Dateiname
                - start_index: Start-Index im Track
                - end_index: End-Index im Track
                - reversed: bool für Richtung
            output_dir: Pfad für merged GPX-Datei
            booking: Buchungs-Dictionary für Dateinamen-Generierung

        Returns:
            Pfad zur geschriebenen GPX-Datei oder None bei Fehler
        """
        if route_files is None or len(route_files) == 0:
            print(f"route_files: {route_files}")
            return None

        merged_gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        merged_gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for entry in route_files:
            gpx_file = self.gpx_dir / entry["file"]
            start_idx = entry["start_index"]
            end_idx = entry["end_index"]
            reversed_dir = entry["reversed"]
            if reversed_dir:
                start_idx, end_idx = end_idx, start_idx

            gpx = read_gpx_file(gpx_file)
            if gpx is None or not gpx.tracks:
                continue

            # Sammle alle Punkte mit Index
            all_points = []
            point_counter = 0
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for p in seg.points:
                        if start_idx <= point_counter <= end_idx:
                            all_points.append(p)
                        point_counter += 1

            # Invertiere falls nötig
            if reversed_dir:
                all_points = all_points[::-1]

            # Füge Punkte zum merged Track hinzu
            for p in all_points:
                segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(latitude=p.latitude, longitude=p.longitude, elevation=p.elevation, time=p.time)
                )

        output_dir.parent.mkdir(parents=True, exist_ok=True)

        # Erstelle aussagekräftigen Dateinamen
        arrival_date = booking.get("arrival_date", "unknown_date")
        hotel_name = booking.get("hotel_name", "unknown_hotel")
        # Entferne problematische Zeichen aus Hotelnamen
        hotel_name_clean = "".join(c for c in hotel_name if c.isalnum() or c in (" ", "-", "_")).strip()
        hotel_name_clean = hotel_name_clean.replace(" ", "_")[:30]

        out_name = f"{arrival_date}_{hotel_name_clean}_merged.gpx"
        output_path = output_dir / out_name

        output_path.write_text(merged_gpx.to_xml(), encoding="utf-8")

        print(f"💾 Merged GPX gespeichert: {output_path.name}")

        return output_path

    def process_all_bookings(self, bookings: List[Dict], output_dir: Path) -> List[Dict]:
        """Verarbeitet alle Buchungen und sammelt GPS-Tracks für jeden Tag.

        Args:
            bookings: Liste mit Buchungen
            output_dir: Ausgabepfad für merged GPX-Dateien

        Returns:
            Sortierte Liste der Buchungen mit GPS-Track-Informationen
        """
        # Nach Anreisedatum sortieren
        bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

        prev_lat = prev_lon = None
        previous_last_file = None

        for booking in bookings_sorted:
            print(booking.get("hotel_name"))

            lat = booking.get("latitude", None)
            lon = booking.get("longitude", None)

            if prev_lon and lon and lat:
                self.collect_route_between_locations(
                    prev_lat, prev_lon, lat, lon, booking, previous_last_file=previous_last_file
                )

                self.merge_gpx_files(booking.get("gpx_files"), output_dir, booking)

                # Speichere letzte Datei für nächste Iteration
                previous_last_file = booking.get("_last_gpx_file")

            prev_lat = lat
            prev_lon = lon

        return bookings_sorted


# Standalone-Funktionen für Kompatibilität mit bestehendem Code


def find_closest_gpx_point(gpx_dir: Path, lat: float, lon: float) -> Optional[Dict]:
    """Findet den nächsten Punkt in allen GPX-Dateien zu gegebener Koordinate.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien
        lat: Ziel-Breitengrad
        lon: Ziel-Längengrad

    Returns:
        Dictionary mit 'file', 'segment', 'index', 'distance' oder None
    """
    best = None

    for gpx_file in Path(gpx_dir).glob("*.gpx"):
        gpx = read_gpx_file(gpx_file)

        if gpx is None:
            print(f"Überspringe {gpx_file.name} - Parsing fehlgeschlagen")
            continue

        for track in gpx.tracks:
            for seg in track.segments:
                for i, p in enumerate(seg.points):
                    d = haversine(lat, lon, p.latitude, p.longitude)
                    if best is None or d < best["distance"]:
                        best = {"file": gpx_file, "segment": seg, "index": i, "distance": d}

    if best is None:
        raise ValueError(f"Keine gültigen GPX-Punkte in {gpx_dir} gefunden")

    return best


def extend_gpx_route(
    closest_point: Dict, target_lat: float, target_lon: float, route_provider_func, output_dir: Path, filename_suffix: str
) -> Optional[Path]:
    """Erweitert eine GPX-Route um eine Strecke zu einer Zieladresse.

    Fügt eine neue Route vom nächstgelegenen Punkt in der GPX-Datei
    zur Zieladresse ein und speichert die modifizierte GPX-Datei.

    Args:
        closest_point: Dictionary mit 'file', 'segment', 'index' vom
                       nächstgelegenen Punkt (von find_closest_gpx_point)
        target_lat: Ziel-Breitengrad
        target_lon: Ziel-Längengrad
        route_provider_func: Funktion die Route berechnet, z.B. route_to_address.
                            Muss (lat_from, lon_from, lat_to, lon_to) akzeptieren
                            und GPX-String zurückgeben
        output_dir: Ausgabeverzeichnis für modifizierte GPX-Datei
        filename_suffix: Suffix für Dateinamen (z.B. Anreisedatum)

    Returns:
        Pfad zur gespeicherten GPX-Datei oder None bei Fehler

    Raises:
        ValueError: Wenn Route nicht berechnet werden kann
    """
    try:
        # Original GPX laden
        gpx = read_gpx_file(closest_point["file"])
        if gpx is None:
            raise ValueError(f"Konnte {closest_point['file'].name} nicht lesen")

        # WICHTIG: closest_point["segment"] ist eine Referenz aus einer anderen
        # GPX-Instanz. Wir müssen das entsprechende Segment in der neu geladenen
        # GPX-Datei finden. Dazu nutzen wir den gespeicherten Index.
        idx = closest_point["index"]

        # Finde das richtige Segment durch erneutes Durchsuchen
        target_point = closest_point["segment"].points[idx]
        found_seg = None
        found_idx = None

        for track in gpx.tracks:
            for seg in track.segments:
                for i, p in enumerate(seg.points):
                    # Prüfe ob dies der gleiche Punkt ist (mit kleiner Toleranz)
                    if (
                        abs(p.latitude - target_point.latitude) < 0.000001
                        and abs(p.longitude - target_point.longitude) < 0.000001
                    ):
                        found_seg = seg
                        found_idx = i
                        break
                if found_seg:
                    break
            if found_seg:
                break

        if found_seg is None:
            raise ValueError("Konnte Einfügepunkt in neu geladener GPX nicht finden")

        seg = found_seg
        idx = found_idx

        if idx >= len(seg.points):
            raise ValueError(f"Index {idx} außerhalb des gültigen Bereichs")

        p = seg.points[idx]

        # Route zur Zieladresse berechnen
        route_gpx_str = route_provider_func(p.latitude, p.longitude, target_lat, target_lon)

        if not route_gpx_str or not route_gpx_str.strip():
            raise ValueError("Route-Provider gab leere Antwort zurück")

        # Route parsen
        route_gpx = gpxpy.parse(route_gpx_str)

        # Validierung: Route muss mindestens einen Track mit Segment haben
        if not route_gpx.tracks or not route_gpx.tracks[0].segments:
            raise ValueError("Berechnete Route enthält keine Tracks/Segmente")

        new_points = route_gpx.tracks[0].segments[0].points

        if not new_points:
            raise ValueError("Berechnete Route enthält keine Punkte")

        # Route in Original-GPX einfügen (nach dem nächsten Punkt)
        seg.points[idx + 1 : idx + 1] = new_points

        # Ausgabedatei speichern
        output_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{closest_point['file'].stem}_{filename_suffix}.gpx"
        output_path = output_dir / out_name

        output_path.write_text(gpx.to_xml(), encoding="utf-8")

        return output_path

    except gpxpy.gpx.GPXException as e:
        print(f"GPX-Fehler: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Erweitern der Route: {e}")
        return None


def get_gps_tracks4day_4alldays(gpx_dir: Path, bookings: List[Dict], output_path: Path) -> List[Dict]:
    """Verarbeitet alle Buchungen und sammelt GPS-Tracks für jeden Tag.

    Diese Funktion ist ein Wrapper um GPXRouteManager.process_all_bookings()
    für Kompatibilität mit bestehendem Code.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien
        bookings: Liste mit Buchungen
        output_path: Ausgabepfad für merged GPX-Dateien

    Returns:
        Sortierte Liste der Buchungen mit GPS-Track-Informationen
    """
    manager = GPXRouteManager(gpx_dir)
    return manager.process_all_bookings(bookings, output_path)
