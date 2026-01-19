import argparse
import json
import shutil
from pathlib import Path

from biketour_planner.geoapify import find_top_tourist_sights
from biketour_planner.geocode import geocode_address
from biketour_planner.gpx_utils import get_gps_tracks4day_4alldays
from biketour_planner.parse_booking import extract_booking_info
from biketour_planner.pass_finder import load_json, process_passes

# from biketour_planner.excel_export import export_bookings_to_excel
from biketour_planner.pdf_export import export_bookings_to_pdf

parser = argparse.ArgumentParser(description="Bike Tour Planner")
parser.add_argument("--booking-dir", type=Path, default=Path("../2026_Kroatien/booking"))
parser.add_argument("--gpx-dir", type=Path, default=Path("../2026_Kroatien/gpx"))
parser.add_argument("--output-dir", type=Path, default=Path("../2026_Kroatien/gpx_modified"))
args = parser.parse_args()

BOOKING_DIR = args.booking_dir
GPX_DIR = args.gpx_dir
OUT_DIR = args.output_dir

if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir(parents=True, exist_ok=True)

create_bookings_json = True  # False


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
        all_bookings = []

        for html_file in BOOKING_DIR.glob("*.htm"):
            booking = extract_booking_info(html_file)

            if booking.get("latitude") is not None:
                lat = booking.get("latitude")
                lon = booking.get("longitude")
            else:
                try:
                    lat, lon = geocode_address(booking["address"])
                except ValueError as e:
                    print(e)
                    all_bookings.append(booking)
                    continue

                booking["latitude"] = lat
                booking["longitude"] = lon

            data_sights = find_top_tourist_sights(lat, lon)
            booking["tourist_sights"] = data_sights

            all_bookings.append(booking)

            # TODO: delete: just for debugging in here
            # if len(all_bookings) > 7:
            #     break
    else:
        all_bookings = load_json(Path("output/bookings.json"))

    all_bookings = get_gps_tracks4day_4alldays(GPX_DIR, all_bookings, OUT_DIR)

    # NEU: Verarbeite Pässe
    all_bookings = process_passes(passes_json_path=GPX_DIR / "Paesse.json", gpx_dir=GPX_DIR, bookings=all_bookings)

    # JSON speichern mit UTF-8 Encoding
    Path("output/bookings.json").write_text(json.dumps(all_bookings, indent=2, ensure_ascii=False), encoding="utf-8")

    export_bookings_to_pdf(
        json_path=Path("output/bookings.json"),
        output_path=Path("output/Reiseplanung_Kroatien_2026.pdf"),
        output_dir=OUT_DIR,
        gpx_dir=GPX_DIR,  # NEU!
        title="Reiseplanung Kroatien 2026",
        excel_info_path=BOOKING_DIR / "Reiseplanung_Fahrrad.xlsx",  # NEU
    )

    # export_bookings_to_excel(
    #     json_path=Path("output/bookings.json"),
    #     template_path=Path("Reiseplanung_Fahrrad template.xlsx"),
    #     output_path=Path("output/Reiseplanung_Kroatien_2026.xlsx"),
    #     start_row=2,  # Ab Zeile 2 einfügen (anpassbar)
    # )
