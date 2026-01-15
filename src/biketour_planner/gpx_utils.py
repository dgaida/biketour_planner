import gpxpy
import math
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from .gpx_route_manager import GPXRouteManager


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


def find_closest_gpx_point(gpx_dir: Path, lat: float, lon: float) -> Optional[Dict]:
    """Findet den nächsten Punkt in allen GPX-Dateien zu einer gegebenen Koordinate.

    Durchsucht alle GPX-Dateien im angegebenen Verzeichnis und findet den Punkt,
    der der Zielkoordinate am nächsten liegt.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien.
        lat: Ziel-Breitengrad in Dezimalgrad.
        lon: Ziel-Längengrad in Dezimalgrad.

    Returns:
        Dictionary mit folgenden Keys:
            - file (Path): Pfad zur GPX-Datei
            - segment: GPX-Segment-Objekt mit dem nächsten Punkt
            - index (int): Index des Punkts im Segment
            - distance (float): Distanz zum Punkt in Metern

    Raises:
        ValueError: Wenn keine gültigen GPX-Punkte im Verzeichnis gefunden wurden.

    Note:
        Diese Funktion ist für Kompatibilität mit älterem Code vorhanden.
        Für neue Implementierungen sollte GPXRouteManager verwendet werden.
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
