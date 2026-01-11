import gpxpy
import math
from pathlib import Path
from typing import Dict, Optional


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
        # print(gpx_file, lat, lon)

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
        # (verwende die gleiche Logik wie find_closest_gpx_point)
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

        # print(new_points)

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


def preprocess_gpx_directory(gpx_dir: Path) -> Dict[str, Dict]:
    """
    Liest alle GPX-Dateien genau einmal ein und speichert relevante
    Metadaten in einer Hashtabelle.

    Key: Dateiname (str)
    Value: Dict mit:
        - file (Path)
        - start_lat, start_lon
        - end_lat, end_lon
        - total_distance_m
        - total_ascent_m
        - max_elevation_m
    """
    gpx_index: Dict[str, Dict] = {}

    for gpx_file in Path(gpx_dir).glob("*.gpx"):
        gpx = read_gpx_file(gpx_file)
        if gpx is None or not gpx.tracks:
            continue

        total_distance = 0.0
        total_ascent = 0.0
        max_elevation = float("-inf")

        first_point = None
        last_point = None

        for track in gpx.tracks:
            for seg in track.segments:
                prev = None
                for p in seg.points:
                    if first_point is None:
                        first_point = p
                    last_point = p

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
        }

    return gpx_index


def collect_gpx_route_between_locations(
    gpx_index: Dict[str, Dict],
    gpx_dir: Path,
    start_lat: float,
    start_lon: float,
    target_lat: float,
    target_lon: float,
    booking: Dict,
    max_chain_length: int = 10,
    max_connection_distance_m: float = 1000.0,
) -> None:
    """
    Collects and chains GPX files between a start and a target location
    using preprocessed GPX metadata.

    The function automatically detects GPX direction (forward/reverse),
    enforces a maximum connection distance between consecutive GPX files,
    and accumulates distance, ascent, and maximum elevation.

    Results are written in-place into the booking dictionary.

    Args:
        gpx_index: Preprocessed GPX metadata (start/end coords, stats).
        gpx_dir: Directory containing GPX files.
        start_lat: Latitude of the start location.
        start_lon: Longitude of the start location.
        target_lat: Latitude of the target location.
        target_lon: Longitude of the target location.
        booking: Booking/day dictionary to enrich.
        max_chain_length: Maximum number of GPX files to chain.
        max_connection_distance_m: Maximum allowed distance (meters)
            between end of one GPX and start/end of the next.
    """

    start_cp = find_closest_gpx_point(gpx_dir, start_lat, start_lon)
    target_cp = find_closest_gpx_point(gpx_dir, target_lat, target_lon)

    start_file = start_cp["file"].name
    target_file = target_cp["file"].name

    visited = set()
    route_files = []

    current_file = start_file
    current_lat = start_lat
    current_lon = start_lon

    total_distance = 0.0
    total_ascent = 0.0
    max_elevation = float("-inf")

    for _ in range(max_chain_length):
        if current_file in visited:
            break

        meta = gpx_index.get(current_file)
        if meta is None:
            break

        # Direction detection for current GPX
        d_forward = haversine(current_lat, current_lon, meta["start_lat"], meta["start_lon"])
        d_reverse = haversine(current_lat, current_lon, meta["end_lat"], meta["end_lon"])

        reversed_direction = d_reverse < d_forward

        visited.add(current_file)
        route_files.append({"file": current_file, "reversed": reversed_direction})

        # Accumulate stats
        total_distance += meta["total_distance_m"]
        total_ascent += meta["total_ascent_m"]
        if meta["max_elevation_m"] is not None:
            max_elevation = max(max_elevation, meta["max_elevation_m"])

        # Update current position
        if reversed_direction:
            current_lat = meta["start_lat"]
            current_lon = meta["start_lon"]
        else:
            current_lat = meta["end_lat"]
            current_lon = meta["end_lon"]

        if current_file == target_file:
            break

        # Find next GPX with distance constraint
        next_file = None
        best_dist = None

        for name, cand in gpx_index.items():
            if name in visited:
                continue

            d_to_start = haversine(current_lat, current_lon, cand["start_lat"], cand["start_lon"])
            d_to_end = haversine(current_lat, current_lon, cand["end_lat"], cand["end_lon"])

            d = min(d_to_start, d_to_end)

            if d > max_connection_distance_m:
                continue

            if best_dist is None or d < best_dist:
                best_dist = d
                next_file = name

        if next_file is None:
            break

        current_file = next_file

    booking["gpx_files"] = route_files
    booking["total_distance_km"] = round(total_distance / 1000, 2)
    booking["total_ascent_m"] = int(round(total_ascent))
    booking["max_elevation_m"] = int(round(max_elevation)) if max_elevation != float("-inf") else None


def get_gps_tracks4day_4alldays(gpx_dir, bookings, output_path):
    gpx_index = preprocess_gpx_directory(gpx_dir)

    # Nach Anreisedatum sortieren
    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    prev_lat = prev_lon = None

    for booking in bookings_sorted:
        print(booking.get("hotel_name"))

        lat = booking.get("latitude", None)
        lon = booking.get("longitude", None)

        if prev_lon and lon and lat:
            collect_gpx_route_between_locations(gpx_index, gpx_dir, prev_lat, prev_lon, lat, lon, booking)

            merge_gpx_files_with_direction(gpx_dir, booking.get("gpx_files"), output_path)

        prev_lat = lat
        prev_lon = lon

    return bookings_sorted


def merge_gpx_files_with_direction(gpx_dir: Path, route_files: list, output_dir: Path) -> Optional[Path]:
    """
    Merges multiple GPX files into a single GPX track, respecting
    per-file direction information.

    Args:
        gpx_dir: Directory containing GPX files.
        route_files: List of dicts with keys:
            - file: GPX filename
            - reversed: bool indicating direction
        output_dir: Path to write merged GPX file.

    Returns:
        Path to the written GPX file.
    """
    if route_files is None:
        print(f"route_files: {route_files}")
        return None

    merged_gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    merged_gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for entry in route_files:
        gpx_file = gpx_dir / entry["file"]
        reversed_dir = entry["reversed"]

        gpx = read_gpx_file(gpx_file)
        if gpx is None or not gpx.tracks:
            continue

        for trk in gpx.tracks:
            for seg in trk.segments:
                points = seg.points[::-1] if reversed_dir else seg.points
                for p in points:
                    segment.points.append(
                        gpxpy.gpx.GPXTrackPoint(latitude=p.latitude, longitude=p.longitude, elevation=p.elevation, time=p.time)
                    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)

    out_name = f"{route_files[0]['file']}_merged.gpx"
    output_path = output_dir / out_name

    output_path.write_text(merged_gpx.to_xml(), encoding="utf-8")

    return output_path
