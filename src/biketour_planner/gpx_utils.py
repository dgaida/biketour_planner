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
    """Liest alle GPX-Dateien genau einmal ein und speichert relevante Metadaten in einer Hashtabelle.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien

    Returns:
        Dictionary mit Dateinamen als Key und Metadaten als Value:
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


def collect_gpx_route_between_locations(
    gpx_index: Dict[str, Dict],
    start_lat: float,
    start_lon: float,
    target_lat: float,
    target_lon: float,
    booking: Dict,
    previous_last_file: Optional[Dict] = None,
    max_chain_length: int = 10,
    max_connection_distance_m: float = 1000.0,
) -> None:
    """Sammelt und verkettet GPX-Dateien zwischen Start- und Zielort.

    Die Funktion erkennt automatisch die GPX-Richtung (vorwärts/rückwärts),
    erzwingt eine maximale Verbindungsdistanz zwischen aufeinanderfolgenden
    GPX-Dateien und akkumuliert Distanz, Aufstieg und maximale Höhe.

    Verhindert, dass invertierte Versionen derselben Datei verwendet werden.
    Wenn die Route mit der letzten Datei der vorherigen Suche fortgesetzt wird,
    wird die gleiche Richtung beibehalten.

    Ergebnisse werden direkt in das booking-Dictionary geschrieben.

    Args:
        gpx_index: Vorverarbeitete GPX-Metadaten (Start/End-Koordinaten, Statistiken).
        start_lat: Breitengrad des Startorts.
        start_lon: Längengrad des Startorts.
        target_lat: Breitengrad des Zielorts.
        target_lon: Längengrad des Zielorts.
        booking: Buchungs-/Tages-Dictionary zum Anreichern.
        previous_last_file: Dict mit 'file' und 'reversed' der letzten Datei
            der vorherigen Suche (falls vorhanden).
        max_chain_length: Maximale Anzahl zu verkettender GPX-Dateien.
        max_connection_distance_m: Maximal erlaubte Distanz (Meter)
            zwischen Ende einer GPX und Start/Ende der nächsten.
    """
    print(f"\n{'=' * 80}")
    print(f"Route-Suche: ({start_lat:.6f}, {start_lon:.6f}) -> ({target_lat:.6f}, {target_lon:.6f})")
    if previous_last_file:
        print(
            f"🔗 Fortsetzung von: {previous_last_file['file']} ({'rückwärts' if previous_last_file['reversed'] else 'vorwärts'})"
        )
    print(f"{'=' * 80}")

    # Finde Start- und Ziel-GPX durch direkte Suche im Index
    start_file = None
    start_distance = float("inf")
    start_reversed = False
    target_file = None
    target_distance = float("inf")

    for filename, meta in gpx_index.items():
        # Prüfe Start-Distanz (zu beiden Enden der Datei)
        d_to_start = haversine(start_lat, start_lon, meta["start_lat"], meta["start_lon"])
        d_to_end = haversine(start_lat, start_lon, meta["end_lat"], meta["end_lon"])

        # Wenn dies die letzte Datei der vorherigen Suche ist,
        # MUSS die gleiche Richtung verwendet werden
        if previous_last_file and filename == previous_last_file["file"]:
            if previous_last_file["reversed"]:
                # Bei rückwärts müssen wir am Start weitermachen
                min_start_dist = d_to_start
                temp_reversed = True
            else:
                # Bei vorwärts müssen wir am Ende weitermachen
                min_start_dist = d_to_end
                temp_reversed = False

            if min_start_dist < start_distance:
                start_distance = min_start_dist
                start_file = filename
                start_reversed = temp_reversed
        else:
            # Normale Logik für andere Dateien
            if d_to_start < d_to_end:
                min_start_dist = d_to_start
                temp_reversed = False
            else:
                min_start_dist = d_to_end
                temp_reversed = True

            if min_start_dist < start_distance:
                start_distance = min_start_dist
                start_file = filename
                start_reversed = temp_reversed

        # Prüfe Ziel-Distanz
        d_to_start = haversine(target_lat, target_lon, meta["start_lat"], meta["start_lon"])
        d_to_end = haversine(target_lat, target_lon, meta["end_lat"], meta["end_lon"])
        min_target_dist = min(d_to_start, d_to_end)

        if min_target_dist < target_distance:
            target_distance = min_target_dist
            target_file = filename

    if not start_file or not target_file:
        print("⚠️  Keine passenden GPX-Dateien gefunden!")
        booking["gpx_files"] = []
        booking["total_distance_km"] = 0
        booking["total_ascent_m"] = 0
        booking["max_elevation_m"] = None
        return

    print(
        f"📍 Start-Datei: {start_file} (Distanz: {start_distance:.1f}m, Richtung: {'rückwärts' if start_reversed else 'vorwärts'})"
    )
    print(f"🎯 Ziel-Datei: {target_file} (Distanz: {target_distance:.1f}m)")
    print()

    visited = set()
    used_base_files = set()  # Verhindert Nutzung invertierter Versionen
    route_files = []

    current_file = start_file
    current_lat = start_lat
    current_lon = start_lon
    current_reversed = start_reversed

    total_distance = 0.0
    total_ascent = 0.0
    max_elevation = float("-inf")

    for iteration in range(max_chain_length):
        if current_file in visited:
            print(f"⚠️  Iteration {iteration + 1}: Datei {current_file} bereits besucht - Abbruch")
            break

        meta = gpx_index.get(current_file)
        if meta is None:
            print(f"⚠️  Iteration {iteration + 1}: Keine Metadaten für {current_file} - Abbruch")
            break

        # Prüfe ob Basis-Dateiname bereits verwendet wurde
        base_name = get_base_filename(current_file)
        if base_name in used_base_files:
            print(f"⚠️  Iteration {iteration + 1}: Basis-Datei {base_name} bereits verwendet - Abbruch")
            break

        # Für die erste Iteration: Verwende die vorgegebene Richtung
        if iteration == 0:
            reversed_direction = current_reversed
        else:
            # Richtungserkennung für aktuelle GPX
            d_forward = haversine(current_lat, current_lon, meta["start_lat"], meta["start_lon"])
            d_reverse = haversine(current_lat, current_lon, meta["end_lat"], meta["end_lon"])
            reversed_direction = d_reverse < d_forward

        d_forward = haversine(current_lat, current_lon, meta["start_lat"], meta["start_lon"])
        d_reverse = haversine(current_lat, current_lon, meta["end_lat"], meta["end_lon"])

        direction_str = "rückwärts" if reversed_direction else "vorwärts"
        print(f"📁 Iteration {iteration + 1}: {current_file}")
        print(f"   Richtung: {direction_str} (forward: {d_forward:.1f}m, reverse: {d_reverse:.1f}m)")

        visited.add(current_file)
        used_base_files.add(base_name)
        route_files.append({"file": current_file, "reversed": reversed_direction})

        # Statistiken akkumulieren
        total_distance += meta["total_distance_m"]
        total_ascent += meta["total_ascent_m"]
        if meta["max_elevation_m"] is not None:
            max_elevation = max(max_elevation, meta["max_elevation_m"])

        print(f"   Distanz: {meta['total_distance_m']:.1f}m, Aufstieg: {meta['total_ascent_m']:.1f}m")

        # Aktuelle Position aktualisieren
        if reversed_direction:
            current_lat = meta["start_lat"]
            current_lon = meta["start_lon"]
        else:
            current_lat = meta["end_lat"]
            current_lon = meta["end_lon"]

        print(f"   Neue Position: ({current_lat:.6f}, {current_lon:.6f})")

        # Prüfe ob Ziel erreicht
        if current_file == target_file:
            print("✅ Ziel erreicht!")
            break

        # Finde nächste GPX mit Distanz-Constraint
        next_file = None
        best_dist = None

        print("   Suche nächste GPX-Datei...")
        for name, cand in gpx_index.items():
            if name in visited:
                continue

            # Prüfe ob Basis-Dateiname bereits verwendet wurde
            cand_base = get_base_filename(name)
            if cand_base in used_base_files:
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
            print(f"⚠️  Keine passende nächste GPX gefunden (max. Distanz: {max_connection_distance_m}m)")
            break

        print(f"   ➡️  Nächste: {next_file} (Distanz: {best_dist:.1f}m)")
        print()

        current_file = next_file

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
        booking["_last_gpx_file"] = route_files[-1]


def get_gps_tracks4day_4alldays(gpx_dir, bookings, output_path):
    """Verarbeitet alle Buchungen und sammelt GPS-Tracks für jeden Tag.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien
        bookings: Liste mit Buchungen
        output_path: Ausgabepfad für merged GPX-Dateien

    Returns:
        Sortierte Liste der Buchungen mit GPS-Track-Informationen
    """
    gpx_index = preprocess_gpx_directory(gpx_dir)

    # Nach Anreisedatum sortieren
    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    prev_lat = prev_lon = None
    previous_last_file = None

    for booking in bookings_sorted:
        print(booking.get("hotel_name"))

        lat = booking.get("latitude", None)
        lon = booking.get("longitude", None)

        if prev_lon and lon and lat:
            collect_gpx_route_between_locations(
                gpx_index, prev_lat, prev_lon, lat, lon, booking, previous_last_file=previous_last_file
            )

            merge_gpx_files_with_direction(gpx_dir, booking.get("gpx_files"), output_path, booking)

            # Speichere letzte Datei für nächste Iteration
            previous_last_file = booking.get("_last_gpx_file")

        prev_lat = lat
        prev_lon = lon

    return bookings_sorted


def merge_gpx_files_with_direction(gpx_dir: Path, route_files: list, output_dir: Path, booking: Dict) -> Optional[Path]:
    """Merged mehrere GPX-Dateien zu einem einzelnen GPX-Track unter Berücksichtigung der Richtung.

    Args:
        gpx_dir: Verzeichnis mit GPX-Dateien
        route_files: Liste von Dicts mit Keys:
            - file: GPX-Dateiname
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

    # Erstelle aussagekräftigen Dateinamen
    arrival_date = booking.get("arrival_date", "unknown_date")
    hotel_name = booking.get("hotel_name", "unknown_hotel")
    # Entferne problematische Zeichen aus Hotelnamen
    hotel_name_clean = "".join(c for c in hotel_name if c.isalnum() or c in (" ", "-", "_")).strip()
    hotel_name_clean = hotel_name_clean.replace(" ", "_")[:30]  # Maximale Länge begrenzen

    out_name = f"{arrival_date}_{hotel_name_clean}_merged.gpx"
    output_path = output_dir / out_name

    output_path.write_text(merged_gpx.to_xml(), encoding="utf-8")

    print(f"💾 Merged GPX gespeichert: {output_path.name}")

    return output_path
