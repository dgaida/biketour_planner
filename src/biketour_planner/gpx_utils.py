from pathlib import Path
from .gpx_route_manager import GPXRouteManager


def get_gps_tracks4day_4alldays(gpx_dir: Path, bookings: list[dict], output_path: Path) -> list[dict]:
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
    manager = GPXRouteManager(gpx_dir, output_path)
    return manager.process_all_bookings(bookings, output_path)
