import json
from pathlib import Path
import shutil
from typing import Dict, Union, List

from biketour_planner.parse_booking import extract_booking_info
from biketour_planner.geocode import geocode_address
from biketour_planner.gpx_utils import get_gps_tracks4day_4alldays
from biketour_planner.excel_export import export_bookings_to_excel

BOOKING_DIR = Path("../2026_Kroatien/booking")
GPX_DIR = Path("../2026_Kroatien/gpx")
OUT_DIR = Path("../2026_Kroatien/gpx_modified")
if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir(parents=True, exist_ok=True)

create_bookings_json = False  # False


def load_json(file_path: Union[Path, str]) -> Union[Dict, List[Dict]]:
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
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded JSON from {file_path.name}")
        return data
    except Exception as e:
        print(f"Error loading JSON {file_path}: {e}")
        raise


if __name__ == "__main__":
    if create_bookings_json:
        all_bookings = []

        for html_file in BOOKING_DIR.glob("*.htm"):
            booking = extract_booking_info(html_file)
            print(booking)

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

            all_bookings.append(booking)
    else:
        all_bookings = load_json(Path("output/bookings.json"))

    all_bookings = get_gps_tracks4day_4alldays(GPX_DIR, all_bookings, OUT_DIR)

    # JSON speichern mit UTF-8 Encoding
    Path("output/bookings.json").write_text(json.dumps(all_bookings, indent=2, ensure_ascii=False), encoding="utf-8")

    export_bookings_to_excel(
        json_path=Path("output/bookings.json"),
        template_path=Path("Reiseplanung_Fahrrad template.xlsx"),
        output_path=Path("output/Reiseplanung_Kroatien_2026.xlsx"),
        start_row=2,  # Ab Zeile 2 einfügen (anpassbar)
    )
