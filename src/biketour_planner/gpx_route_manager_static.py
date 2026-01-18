import gpxpy
import math
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from .elevation_calc import calculate_elevation_gain_segment_based
from .logger import get_logger

# Initialisiere Logger
logger = get_logger()

TrackStats = tuple[float, float, float, float]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Berechnet die Distanz zwischen zwei Koordinaten in Metern.

    Verwendet die Haversine-Formel für Großkreisberechnungen auf einer Kugel.
    Diese Formel liefert gute Näherungswerte für Distanzen auf der Erdoberfläche.

    Args:
        lat1: Breitengrad Punkt 1 in Dezimalgrad.
        lon1: Längengrad Punkt 1 in Dezimalgrad.
        lat2: Breitengrad Punkt 2 in Dezimalgrad.
        lon2: Längengrad Punkt 2 in Dezimalgrad.

    Returns:
        Distanz in Metern als float.

    Example:
        >>> distance = haversine(52.5200, 13.4050, 48.1351, 11.5820)  # Berlin -> München
        >>> print(f"{distance / 1000:.1f} km")
        504.2 km
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_gpx_file(gpx_file: Path) -> Optional[gpxpy.gpx.GPX]:
    """Liest eine GPX-Datei mit robustem Encoding-Handling.

    Probiert verschiedene Encoding-Strategien (UTF-8, Latin-1, CP1252) und
    behandelt BOM (Byte Order Mark) sowie führende Whitespaces. Bei allen
    Fehlschlägen wird ein binärer Leseversuch mit Fehlertoleranz durchgeführt.

    Args:
        gpx_file: Pfad zur GPX-Datei.

    Returns:
        Geparste GPX-Datei als gpxpy.gpx.GPX Objekt oder None bei Fehler.

    Note:
        Die Funktion gibt Fehlermeldungen auf stdout aus, wirft aber keine
        Exceptions, um die Verarbeitung weiterer Dateien nicht zu blockieren.
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
            logger.error(f"Unerwarteter Fehler beim Lesen von {gpx_file.name}: {e}")
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
        logger.error(f"Fehler beim Parsen von {gpx_file.name}: {e}")
        return None


def get_base_filename(filename: str) -> str:
    """Extrahiert den Basis-Dateinamen ohne Richtungssuffix.

    Entfernt Suffixe wie '_inverted', '_reversed', '_rev' etc. um zu verhindern,
    dass derselbe Track in verschiedenen Richtungen mehrfach verwendet wird.

    Args:
        filename: GPX-Dateiname mit potenziellem Richtungssuffix.

    Returns:
        Basis-Dateiname ohne Richtungsinformationen.

    Example:
        >>> get_base_filename("route_München_Garmisch_reversed.gpx")
        'route_München_Garmisch.gpx'
    """
    # Entferne häufige Suffixe für invertierte Tracks
    for suffix in ["_inverted", "_reversed", "_rev", "_inverse", "_backward"]:
        if filename.lower().endswith(f"{suffix}.gpx"):
            return filename[: -len(suffix) - 4] + ".gpx"

    return filename


def find_closest_point_in_track(points: List[Dict], target_lat: float, target_lon: float) -> Tuple[int, float]:
    """Findet den nächsten Punkt innerhalb eines Tracks zu einer Zielkoordinate.

    Durchsucht eine Liste von Punkten und berechnet für jeden die Haversine-Distanz
    zur Zielkoordinate. Gibt den Index des nächstgelegenen Punkts zurück.

    Args:
        points: Liste von Punkt-Dictionaries mit Keys 'lat', 'lon', 'index'.
        target_lat: Ziel-Breitengrad in Dezimalgrad.
        target_lon: Ziel-Längengrad in Dezimalgrad.

    Returns:
        Tuple bestehend aus:
            - index: Index des nächsten Punkts in der ursprünglichen Points-Liste.
            - distance: Distanz zum nächsten Punkt in Metern.

    Raises:
        ValueError: Wenn points leer ist (implizit durch float('inf') Rückgabe).
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
    """Berechnet Statistiken für einen Track-Abschnitt zwischen zwei Indizes.

    Lädt die GPX-Datei, extrahiert den relevanten Abschnitt und berechnet:
    - Maximale Höhe
    - Distanz (aufsummiert über Punktabstände)
    - Positiver Höhenunterschied (nur Anstiege)
    - Negativer Höhenunterschied (nur Abfahrten)

    Args:
        gpx: GPX-Objekt.
        start_index: Startindex des Abschnitts.
        end_index: Endindex des Abschnitts.
        max_elevation: Bisherige maximale Höhe in Metern (wird aktualisiert).
        total_distance: Bisherige Gesamtdistanz in Metern (wird aktualisiert).
        total_ascent: Bisheriger Gesamtanstieg in Metern (wird aktualisiert).
        reversed_direction: Wenn True, wird der Track-Abschnitt rückwärts
                           durchlaufen (Punkte in umgekehrter Reihenfolge).

    Returns:
        Tuple aus (max_elevation, total_distance, total_ascent, total_descent)
        mit aktualisierten Werten.

    Note:
        Die Statistiken werden kumulativ berechnet, d.h. die übergebenen Werte
        werden mit den Werten des aktuellen Abschnitts erweitert.
    """
    if not end_index:
        end_index = float("inf")

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
    max_elevation = max(elevations)
    total_ascent += calculate_elevation_gain_segment_based(elevations, calculate_descent=False)
    total_descent += calculate_elevation_gain_segment_based(elevations, calculate_descent=True)

    logger.debug(f"   Punkte: {end_index - start_index + 1}")

    return max_elevation, total_distance, total_ascent, total_descent


# def find_closest_gpx_point(gpx_dir: Path, lat: float, lon: float) -> Optional[Dict]:
#     """Findet den nächsten Punkt in allen GPX-Dateien zu einer gegebenen Koordinate.
#
#     Durchsucht alle GPX-Dateien im angegebenen Verzeichnis und findet den Punkt,
#     der der Zielkoordinate am nächsten liegt.
#
#     Args:
#         gpx_dir: Verzeichnis mit GPX-Dateien.
#         lat: Ziel-Breitengrad in Dezimalgrad.
#         lon: Ziel-Längengrad in Dezimalgrad.
#
#     Returns:
#         Dictionary mit folgenden Keys:
#             - file (Path): Pfad zur GPX-Datei
#             - segment: GPX-Segment-Objekt mit dem nächsten Punkt
#             - index (int): Index des Punkts im Segment
#             - distance (float): Distanz zum Punkt in Metern
#
#     Raises:
#         ValueError: Wenn keine gültigen GPX-Punkte im Verzeichnis gefunden wurden.
#
#     Note:
#         Diese Funktion ist für Kompatibilität mit älterem Code vorhanden.
#         Für neue Implementierungen sollte GPXRouteManager verwendet werden.
#     """
#     best = None
#
#     for gpx_file in Path(gpx_dir).glob("*.gpx"):
#         gpx = read_gpx_file(gpx_file)
#
#         if gpx is None:
#             print(f"Überspringe {gpx_file.name} - Parsing fehlgeschlagen")
#             continue
#
#         for track in gpx.tracks:
#             for seg in track.segments:
#                 for i, p in enumerate(seg.points):
#                     d = haversine(lat, lon, p.latitude, p.longitude)
#                     if best is None or d < best["distance"]:
#                         best = {"file": gpx_file, "segment": seg, "index": i, "distance": d}
#
#     if best is None:
#         raise ValueError(f"Keine gültigen GPX-Punkte in {gpx_dir} gefunden")
#
#     return best
