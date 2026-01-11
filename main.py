import json
from pathlib import Path

from biketour_planner.parse_booking import extract_booking_info
from biketour_planner.geocode import geocode_address
from biketour_planner.gpx_utils import find_closest_gpx_point, extend_gpx_route
from biketour_planner.brouter import route_to_address
from biketour_planner.excel_export import export_bookings_to_excel

BOOKING_DIR = Path("../2026_Kroatien/booking")
GPX_DIR = Path("../2026_Kroatien/gpx")
OUT_DIR = Path("../2026_Kroatien/gpx_modified")
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_bookings = []

for html_file in BOOKING_DIR.glob("*.htm"):
    booking = extract_booking_info(html_file)
    print(booking)

    try:
        lat, lon = geocode_address(booking["address"])
    except ValueError as e:
        print(e)
        all_bookings.append(booking)
        continue

    booking["latitude"] = lat
    booking["longitude"] = lon

    closest = find_closest_gpx_point(GPX_DIR, lat, lon)

    output_path = extend_gpx_route(
        closest_point=closest,
        target_lat=lat,
        target_lon=lon,
        route_provider_func=route_to_address,
        output_dir=OUT_DIR,
        filename_suffix=booking['arrival_date']
    )

    if output_path:
        print(f"GPX erweitert: {output_path}")
    else:
        print(f"Fehler beim Erweitern der Route für {booking['hotel_name']}")

    all_bookings.append(booking)

# JSON speichern mit UTF-8 Encoding
Path("output/bookings.json").write_text(
    json.dumps(all_bookings, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

export_bookings_to_excel(
    json_path=Path("output/bookings.json"),
    template_path=Path("Reiseplanung_Fahrrad template.xlsx"),
    output_path=Path("output/Reiseplanung_Kroatien_2026.xlsx"),
    start_row=2  # Ab Zeile 2 einfügen (anpassbar)
)
