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
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

    for encoding in encodings:
        try:
            content = gpx_file.read_text(encoding=encoding)

            # Entferne BOM falls vorhanden
            if content.startswith('\ufeff'):
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
        with open(gpx_file, 'rb') as f:
            content = f.read()

        # Versuche UTF-8 mit Fehlerbehandlung
        text = content.decode('utf-8', errors='ignore')

        # Entferne BOM
        if text.startswith('\ufeff'):
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
                        best = {
                            "file": gpx_file,
                            "segment": seg,
                            "index": i,
                            "distance": d
                        }

    if best is None:
        raise ValueError(f"Keine gültigen GPX-Punkte in {gpx_dir} gefunden")

    return best


def extend_gpx_route(
        closest_point: Dict,
        target_lat: float,
        target_lon: float,
        route_provider_func,
        output_dir: Path,
        filename_suffix: str
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
                    if (abs(p.latitude - target_point.latitude) < 0.000001 and
                            abs(p.longitude - target_point.longitude) < 0.000001):
                        found_seg = seg
                        found_idx = i
                        break
                if found_seg:
                    break
            if found_seg:
                break

        if found_seg is None:
            raise ValueError(f"Konnte Einfügepunkt in neu geladener GPX nicht finden")

        seg = found_seg
        idx = found_idx

        if idx >= len(seg.points):
            raise ValueError(f"Index {idx} außerhalb des gültigen Bereichs")

        p = seg.points[idx]

        # Route zur Zieladresse berechnen
        route_gpx_str = route_provider_func(
            p.latitude, p.longitude, target_lat, target_lon
        )

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
        seg.points[idx + 1:idx + 1] = new_points

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
