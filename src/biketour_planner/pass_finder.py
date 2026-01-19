"""Pass-Finder Modul für automatische Zuordnung von Pass-Tracks zu Buchungen.

Dieses Modul findet GPS-Tracks die zu bestimmten Pässen führen und ordnet
sie den nächstgelegenen Hotels zu.
"""

import json
from pathlib import Path
from typing import Any, Optional, Union

from .config import get_config
from .geocode import geocode_address
from .gpx_route_manager_static import get_statistics4track, haversine, read_gpx_file
from .logger import get_logger

logger = get_logger()

JsonData = Union[dict[str, Any], list[dict[str, Any]]]


def load_json(file_path: Union[Path, str]) -> JsonData:
    """Lädt eine JSON-Datei mit Error-Handling.

    Die Funktion sucht die Datei relativ zum 'src/data/' Verzeichnis.

    Args:
        file_path: Path oder String zur JSON-Datei (relativ zu src/data/).

    Returns:
        Dictionary oder Liste mit den JSON-Daten.

    Raises:
        FileNotFoundError: Wenn die JSON-Datei nicht existiert.
        json.JSONDecodeError: Wenn das JSON-Format ungültig ist.

    Example:
        >>> data = load_json("german_cities.json")
        Loaded JSON from german_cities.json
        >>> print(type(data))
        <class 'list'>
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded JSON from {file_path.name}")
        return data
    except Exception as e:
        print(f"Error loading JSON {file_path}: {e}")
        raise


def get_gpx_endpoints(gpx_file: Path) -> Optional[tuple[float, float, float, float]]:
    """Extrahiert Start- und Endpunkt aus einer GPX-Datei.

    Args:
        gpx_file: Pfad zur GPX-Datei.

    Returns:
        Tuple (start_lat, start_lon, end_lat, end_lon) oder None bei Fehler.
    """
    gpx = read_gpx_file(gpx_file)

    if gpx is None or not gpx.tracks:
        return None

    first_point = None
    last_point = None

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if first_point is None:
                    first_point = point
                last_point = point

    if first_point is None or last_point is None:
        return None

    return (
        first_point.latitude,
        first_point.longitude,
        last_point.latitude,
        last_point.longitude,
    )


def find_nearest_hotel(pass_lat: float, pass_lon: float, bookings: list[dict]) -> Optional[dict]:
    """Findet das nächstgelegene Hotel zu einem Pass.

    Args:
        pass_lat: Breitengrad des Passes.
        pass_lon: Längengrad des Passes.
        bookings: Liste mit Buchungs-Dictionaries.

    Returns:
        Nächstgelegenes Buchungs-Dictionary oder None.
    """
    nearest_booking = None
    min_distance = float("inf")

    for booking in bookings:
        hotel_lat = booking.get("latitude")
        hotel_lon = booking.get("longitude")

        if hotel_lat is None or hotel_lon is None:
            continue

        distance = haversine(pass_lat, pass_lon, hotel_lat, hotel_lon)

        if distance < min_distance:
            min_distance = distance
            nearest_booking = booking

    if nearest_booking:
        logger.info(f"Nächstes Hotel zu Pass: {nearest_booking.get('hotel_name')} " f"({min_distance / 1000:.1f} km entfernt)")

    return nearest_booking


def find_pass_track(
    hotel_lat: float,
    hotel_lon: float,
    pass_lat: float,
    pass_lon: float,
    gpx_dir: Path,
    hotel_radius_km: float = None,
    pass_radius_km: float = None,
) -> Optional[Path]:
    """Findet einen GPS-Track der vom Hotel zum Pass führt.

    Sucht nach GPX-Dateien deren:
    - Startpunkt im Umkreis von hotel_radius_km vom Hotel liegt
    - Endpunkt im Umkreis von pass_radius_km vom Pass liegt

    Args:
        hotel_lat: Breitengrad des Hotels.
        hotel_lon: Längengrad des Hotels.
        pass_lat: Breitengrad des Passes.
        pass_lon: Längengrad des Passes.
        gpx_dir: Verzeichnis mit GPX-Dateien.
        hotel_radius_km: Suchradius um Hotel in Kilometern. Falls None, wird config.passes.hotel_radius_km verwendet.
        pass_radius_km: Suchradius um Pass in Kilometern. Falls None, wird config.passes.pass_radius_km verwendet.

    Returns:
        Pfad zur GPX-Datei oder None wenn keine passende Datei gefunden.
    """
    # Lade Config für Defaults
    config = get_config()

    if hotel_radius_km is None:
        hotel_radius_km = config.passes.hotel_radius_km

    if pass_radius_km is None:
        pass_radius_km = config.passes.pass_radius_km

    hotel_radius_m = hotel_radius_km * 1000
    pass_radius_m = pass_radius_km * 1000

    best_track = None
    best_score = float("inf")  # Geringste Summe der Abstände

    for gpx_file in gpx_dir.glob("*.gpx"):
        endpoints = get_gpx_endpoints(gpx_file)

        if endpoints is None:
            continue

        start_lat, start_lon, end_lat, end_lon = endpoints

        # Prüfe ob Start in Hotel-Nähe und Ende in Pass-Nähe
        dist_start_to_hotel = haversine(start_lat, start_lon, hotel_lat, hotel_lon)
        dist_end_to_pass = haversine(end_lat, end_lon, pass_lat, pass_lon)

        if dist_start_to_hotel <= hotel_radius_m and dist_end_to_pass <= pass_radius_m:
            score = dist_start_to_hotel + dist_end_to_pass
            if score < best_score:
                best_score = score
                best_track = gpx_file
                logger.debug(
                    f"Kandidat: {gpx_file.name} " f"(Hotel: {dist_start_to_hotel:.0f}m, Pass: {dist_end_to_pass:.0f}m)"
                )

        # Prüfe auch umgekehrte Richtung (Ende bei Hotel, Start bei Pass)
        dist_end_to_hotel = haversine(end_lat, end_lon, hotel_lat, hotel_lon)
        dist_start_to_pass = haversine(start_lat, start_lon, pass_lat, pass_lon)

        if dist_end_to_hotel <= hotel_radius_m and dist_start_to_pass <= pass_radius_m:
            score = dist_end_to_hotel + dist_start_to_pass
            if score < best_score:
                best_score = score
                best_track = gpx_file
                logger.debug(
                    f"Kandidat (reversed): {gpx_file.name} "
                    f"(Hotel: {dist_end_to_hotel:.0f}m, Pass: {dist_start_to_pass:.0f}m)"
                )

    if best_track:
        logger.info(f"✅ Pass-Track gefunden: {best_track.name}")
    else:
        logger.warning(
            f"⚠️  Kein passender Track gefunden " f"(Hotel-Radius: {hotel_radius_km}km, Pass-Radius: {pass_radius_km}km)"
        )

    return best_track


def process_passes(
    passes_json_path: Path,
    gpx_dir: Path,
    bookings: list[dict],
    hotel_radius_km: float = None,
    pass_radius_km: float = None,
) -> list[dict]:
    """Verarbeitet alle Pässe und ordnet GPS-Tracks zu Hotels zu.

    Für jeden Pass in passes.json:
    1. Geocodiert den Passnamen
    2. Findet das nächstgelegene Hotel
    3. Sucht einen GPS-Track vom Hotel zum Pass
    4. Berechnet Statistiken für den Pass-Track
    5. Fügt den Track zum Buchungs-Dictionary hinzu

    Args:
        passes_json_path: Pfad zur passes.json Datei.
        gpx_dir: Verzeichnis mit GPX-Dateien.
        bookings: Liste mit Buchungs-Dictionaries (wird modifiziert).
        hotel_radius_km: Suchradius um Hotel in Kilometern. Falls None, wird config.passes.hotel_radius_km verwendet.
        pass_radius_km: Suchradius um Pass in Kilometern. Falls None, wird config.passes.pass_radius_km verwendet.

    Returns:
        Modifizierte bookings-Liste mit "paesse_tracks" Keys.

    Example:
        >>> bookings = process_passes(
        ...     Path("gpx/Paesse.json"),
        ...     Path("gpx/"),
        ...     bookings
        ... )
        >>> print(bookings[0].get("paesse_tracks"))
        [{"file": "Sveti_Jure.gpx", "passname": "Sveti Jure", "total_ascent_m": 1234, "total_descent_m": 567}]
    """
    # Lade Config für Defaults
    config = get_config()

    if hotel_radius_km is None:
        hotel_radius_km = config.passes.hotel_radius_km

    if pass_radius_km is None:
        pass_radius_km = config.passes.pass_radius_km

    if not passes_json_path.exists():
        logger.warning(f"Keine Pässe-Datei gefunden: {passes_json_path}")
        return bookings

    # Lade Pässe
    passes = load_json(passes_json_path)

    if not passes:
        logger.info("Keine Pässe in der JSON-Datei")
        return bookings

    logger.info(f"\n{'='*80}")
    logger.info(f"Verarbeite {len(passes)} Pass/Pässe")
    logger.info(f"{'='*80}\n")

    # Initialisiere paesse_tracks für alle Buchungen
    for booking in bookings:
        if "paesse_tracks" not in booking:
            booking["paesse_tracks"] = []

    # Verarbeite jeden Pass
    for pass_info in passes:
        passname = pass_info.get("passname")

        if not passname:
            logger.warning("Pass ohne Namen gefunden, überspringe")
            continue

        logger.info(f"\n🏔️  Verarbeite Pass: {passname}")

        # Geocodiere Pass
        try:
            pass_lat, pass_lon = geocode_address(passname)
            logger.info(f"   Koordinaten: {pass_lat:.6f}, {pass_lon:.6f}")
        except ValueError as e:
            logger.error(f"   ❌ Geocoding fehlgeschlagen: {e}")
            continue

        # Finde nächstes Hotel
        nearest_hotel = find_nearest_hotel(pass_lat, pass_lon, bookings)

        if nearest_hotel is None:
            logger.warning(f"   ⚠️  Kein Hotel gefunden für {passname}")
            continue

        hotel_lat = nearest_hotel["latitude"]
        hotel_lon = nearest_hotel["longitude"]
        hotel_name = nearest_hotel.get("hotel_name", "Unbekannt")

        logger.info(f"   🏨 Nächstes Hotel: {hotel_name}")

        # Finde GPS-Track
        track_file = find_pass_track(hotel_lat, hotel_lon, pass_lat, pass_lon, gpx_dir, hotel_radius_km, pass_radius_km)

        if track_file:
            # Berechne Statistiken für Pass-Track
            gpx = read_gpx_file(track_file)

            if gpx and gpx.tracks:
                max_elevation, total_distance, total_ascent, total_descent = get_statistics4track(gpx)

                # Füge Track zum Buchungs-Dictionary hinzu mit Statistiken
                pass_track_entry = {
                    "file": track_file.name,
                    "passname": passname,
                    "latitude": pass_lat,
                    "longitude": pass_lon,
                    "total_distance_km": round(total_distance / 1000, 2),
                    "total_ascent_m": int(round(total_ascent)),
                    "total_descent_m": int(round(total_descent)),
                    "max_elevation_m": int(round(max_elevation)) if max_elevation != float("-inf") else None,
                }

                nearest_hotel["paesse_tracks"].append(pass_track_entry)

                logger.info(f"   ✅ Track zugeordnet: {track_file.name} → {hotel_name}")
                logger.info(
                    f"      Statistiken: {total_distance/1000:.1f} km, {int(total_ascent)} hm↑, {int(total_descent)} hm↓"
                )
            else:
                logger.warning(f"   ⚠️  Konnte GPX-Datei {track_file.name} nicht lesen")
        else:
            logger.warning(f"   ⚠️  Kein passender GPS-Track für {passname} gefunden")

    # Zusammenfassung
    total_pass_tracks = sum(len(b.get("paesse_tracks", [])) for b in bookings)
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ {total_pass_tracks} Pass-Track(s) zugeordnet")
    logger.info(f"{'='*80}\n")

    return bookings


if __name__ == "__main__":
    # Beispielaufruf
    from pathlib import Path

    config = get_config()

    # Verwende Config-Werte für Pfade
    passes_json = config.directories.gpx / config.passes.passes_file
    gpx_directory = config.directories.gpx
    bookings_json = Path("output/bookings.json")

    # Lade Buchungen
    with open(bookings_json, encoding="utf-8") as f:
        bookings = json.load(f)

    # Verarbeite Pässe (verwendet Config-Defaults für Radien)
    bookings = process_passes(passes_json, gpx_directory, bookings)

    # Speichere aktualisierte Buchungen
    with open(bookings_json, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=2, ensure_ascii=False)

    print("Fertig!")
