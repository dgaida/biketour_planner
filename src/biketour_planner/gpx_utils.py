import gpxpy
import math
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from gpx_route_manager import GPXRouteManager


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


def extend_gpx_route(
    closest_point: Dict, target_lat: float, target_lon: float, route_provider_func, output_dir: Path, filename_suffix: str
) -> Optional[Path]:
    """Erweitert eine GPX-Route um eine berechnete Strecke zu einer Zieladresse.

    Fügt eine neue Route vom nächstgelegenen Punkt in der GPX-Datei zur Zieladresse
    ein und speichert die modifizierte GPX-Datei. Die Route wird vom route_provider_func
    berechnet (z.B. BRouter).

    **Anwendungsfall:**
    Diese Funktion wird verwendet, um GPX-Tracks direkt zu Unterkünften zu verlängern,
    wenn die Unterkunft nicht auf dem Track liegt. Die Hauptverwendung ist jedoch durch
    GPXRouteManager.collect_route_between_locations ersetzt worden.

    Args:
        closest_point: Dictionary mit Informationen zum nächstgelegenen Punkt.
                      Muss folgende Keys enthalten:
                      - file (Path): Pfad zur GPX-Datei
                      - segment: GPX-Segment-Objekt
                      - index (int): Index des Punkts im Segment
                      Typischerweise von find_closest_gpx_point() zurückgegeben.
        target_lat: Ziel-Breitengrad in Dezimalgrad.
        target_lon: Ziel-Längengrad in Dezimalgrad.
        route_provider_func: Funktion zur Routenberechnung. Muss die Signatur
                            (lat_from, lon_from, lat_to, lon_to) haben und einen
                            GPX-String zurückgeben. Beispiel: route_to_address von BRouter.
        output_dir: Ausgabeverzeichnis für die modifizierte GPX-Datei.
        filename_suffix: Suffix für den Dateinamen (z.B. Anreisedatum im Format YYYY-MM-DD).

    Returns:
        Path zur gespeicherten GPX-Datei oder None bei Fehler.

    Raises:
        ValueError: Wenn die Route nicht berechnet werden kann oder die GPX-Datei
                   nicht geladen werden kann.

    Note:
        Diese Funktion ist für Kompatibilität mit älterem Code vorhanden.
        Für neue Implementierungen sollte GPXRouteManager verwendet werden.
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
