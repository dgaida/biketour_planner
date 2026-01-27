import argparse
import json
import shutil
from pathlib import Path

from biketour_planner.config import get_config
from biketour_planner.gpx_utils import get_gps_tracks4day_4alldays
from biketour_planner.parse_booking import create_all_bookings
from biketour_planner.pass_finder import load_json, process_passes
from biketour_planner.pdf_export import export_bookings_to_pdf
from biketour_planner.ics_export import export_bookings_to_ics

# Lade Konfiguration
config = get_config()

# Argumente können Config überschreiben
parser = argparse.ArgumentParser(description="Bike Tour Planner")
parser.add_argument("--booking-dir", type=Path, default=None)
parser.add_argument("--gpx-dir", type=Path, default=None)
parser.add_argument("--output-dir", type=Path, default=None)
args = parser.parse_args()

# Verwende CLI-Argumente falls gesetzt, sonst Config
BOOKING_DIR = args.booking_dir or config.directories.booking
GPX_DIR = args.gpx_dir or config.directories.gpx
OUT_DIR = args.output_dir or config.directories.output

if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir(parents=True, exist_ok=True)

create_bookings_json = True


def validate_directories() -> None:
    """Validiert dass alle benötigten Verzeichnisse existieren."""
    if not BOOKING_DIR.exists():
        raise FileNotFoundError(f"Booking-Verzeichnis nicht gefunden: {BOOKING_DIR}")

    if not GPX_DIR.exists():
        raise FileNotFoundError(f"GPX-Verzeichnis nicht gefunden: {GPX_DIR}")

    # Prüfe ob überhaupt Dateien vorhanden
    if not list(BOOKING_DIR.glob("*.htm*")):
        raise ValueError(f"Keine HTML-Dateien in {BOOKING_DIR} gefunden")

    if not list(GPX_DIR.glob("*.gpx")):
        raise ValueError(f"Keine GPX-Dateien in {GPX_DIR} gefunden")


if __name__ == "__main__":
    validate_directories()

    if create_bookings_json:
        all_bookings = create_all_bookings(BOOKING_DIR, config.geoapify.search_radius_m, config.geoapify.max_pois)
    else:
        all_bookings = load_json(Path("output/bookings.json"))

    all_bookings = get_gps_tracks4day_4alldays(GPX_DIR, all_bookings, OUT_DIR)

    # Verwende Config-Werte für Pass-Finder
    passes_file = GPX_DIR / config.passes.passes_file
    all_bookings = process_passes(
        passes_json_path=passes_file,
        gpx_dir=GPX_DIR,
        bookings=all_bookings,
        hotel_radius_km=config.passes.hotel_radius_km,
        pass_radius_km=config.passes.pass_radius_km,
    )

    # JSON speichern mit UTF-8 Encoding
    Path("output/bookings.json").write_text(json.dumps(all_bookings, indent=2, ensure_ascii=False), encoding="utf-8")

    # Verwende Config-Werte für Export
    excel_info_path = BOOKING_DIR / config.export.excel_info_file
    export_bookings_to_pdf(
        json_path=Path("output/bookings.json"),
        output_path=Path("output/Reiseplanung_Kroatien_2026.pdf"),
        output_dir=OUT_DIR,
        gpx_dir=GPX_DIR,
        title=config.export.title,
        excel_info_path=excel_info_path if excel_info_path.exists() else None,
    )

    # ICS-Kalender exportieren
    export_bookings_to_ics(
        bookings=all_bookings,
        output_path=Path("output/Reiseplanung_Kroatien_2026.ics"),
    )
