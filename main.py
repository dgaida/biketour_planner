import json
from pathlib import Path
import gpxpy

from biketour_planner.parse_booking import extract_booking_info
from biketour_planner.geocode import geocode_address
from biketour_planner.gpx_utils import find_closest_gpx_point
from biketour_planner.brouter import route_to_address

BOOKING_DIR = Path("../2026_Kroatien/booking")
GPX_DIR = Path("../2026_Kroatien/gpx")
OUT_DIR = Path("output/gpx_modified")
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

    gpx = gpxpy.parse(closest["file"].read_text())
    seg = closest["segment"]
    idx = closest["index"]
    p = seg.points[idx]

    route_gpx = gpxpy.parse(
        route_to_address(p.latitude, p.longitude, lat, lon)
    )

    # Route einfügen
    new_points = route_gpx.tracks[0].segments[0].points
    seg.points[idx+1:idx+1] = new_points

    out_name = f"{closest['file'].stem}_{booking['arrival_date']}.gpx"
    (OUT_DIR / out_name).write_text(gpx.to_xml())

    all_bookings.append(booking)

# JSON speichern
Path("output/bookings.json").write_text(
    json.dumps(all_bookings, indent=2, ensure_ascii=False)
)
