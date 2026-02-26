"""Parsing logic for extracting booking information from HTML confirmations.

Supports Booking.com and Airbnb confirmation formats.
"""

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .exceptions import ParsingError
from .geoapify import find_top_tourist_sights
from .geocode import geocode_address
from .logger import get_logger

# Initialize Logger
logger = get_logger()

MONTHS_DE = {
    "Januar": "01",
    "Februar": "02",
    "März": "03",
    "April": "04",
    "Mai": "05",
    "Juni": "06",
    "Juli": "07",
    "August": "08",
    "September": "09",
    "Oktober": "10",
    "November": "11",
    "Dezember": "12",
}


def parse_date(text: str) -> str | None:
    """Parse a German date in format 'Day, D. Month Year'.

    Args:
        text: String with date information, e.g., "So., 8. März 2026"

    Returns:
        ISO-formatted date (YYYY-MM-DD) or None on error.
    """
    if not text:
        return None
    # e.g., "So., 8. März 2026"
    m = re.search(r"(\d{1,2})\. ([A-Za-zäöüÄÖÜ]+) (\d{4})", text)
    if not m:
        return None
    day, month, year = m.groups()
    if month in MONTHS_DE:
        return f"{year}-{MONTHS_DE[month]}-{int(day):02d}"
    return None


def parse_gps_coordinates(gps_text: str) -> tuple[float | None, float | None]:
    """Convert GPS coordinates from degrees/minutes to decimal degrees.

    Args:
        gps_text: GPS string in format "N 043° 56.181, E 15° 26.645"

    Returns:
        Tuple of (latitude, longitude) in decimal degrees or (None, None).
    """
    if not gps_text:
        return None, None

    # Extract N/S degrees and minutes
    lat_match = re.search(r"([NS])\s*(\d+)[°&deg;]+\s*([\d.]+)", gps_text)
    # Extract E/W degrees and minutes
    lon_match = re.search(r"([EW])\s*(\d+)[°&deg;]+\s*([\d.]+)", gps_text)

    if not lat_match or not lon_match:
        return None, None

    # Convert to decimal degrees: Degrees + (Minutes / 60)
    lat_deg = int(lat_match.group(2))
    lat_min = float(lat_match.group(3))
    lat = lat_deg + (lat_min / 60)
    if lat_match.group(1) == "S":
        lat = -lat

    lon_deg = int(lon_match.group(2))
    lon_min = float(lon_match.group(3))
    lon = lon_deg + (lon_min / 60)
    if lon_match.group(1) == "W":
        lon = -lon

    return lat, lon


def parse_airbnb_booking(soup: BeautifulSoup) -> dict[str, Any] | None:
    """Extract booking information from an Airbnb HTML confirmation.

    Args:
        soup: BeautifulSoup object of the HTML page.

    Returns:
        Dictionary with booking information or None on error.
    """
    # Search for script tag with Airbnb data (metadata)
    script_tag = soup.find("script", string=re.compile(r'"metadata".*"title".*"check_in_date"'))

    if not script_tag:
        return None

    script_text = script_tag.string

    # Extract title (accommodation name)
    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', script_text)
    hotel_name = title_match.group(1) if title_match else None

    # Extract check_in_date
    checkin_match = re.search(r'"check_in_date"\s*:\s*"([^"]*)"', script_text)
    arrival_date = checkin_match.group(1) if checkin_match else None

    # Extract check_out_date
    checkout_match = re.search(r'"check_out_date"\s*:\s*"([^"]*)"', script_text)
    departure_date = checkout_match.group(1) if checkout_match else None

    # Extract GPS coordinates
    lat_match = re.search(r'"lat"\s*:\s*([\d.]+)', script_text)
    gps_lat = float(lat_match.group(1)) if lat_match else None

    lng_match = re.search(r'"lng"\s*:\s*([\d.]+)', script_text)
    gps_lon = float(lng_match.group(1)) if lng_match else None

    # Validate critical fields
    if not (hotel_name and arrival_date and departure_date):
        logger.warning("Airbnb Parser: Critical fields missing")
        return None

    # Search for additional information in SSRUIStateToken
    city_name = ""
    country_name = ""
    address = None
    checkin_time = None
    total_price = None

    # Search in all script tags for specific JSON structures
    for script in soup.find_all("script"):
        if not script.string:
            continue

        script_content = script.string

        # Search for checkin_checkout_arrival_guide
        if '"id":"checkin_checkout_arrival_guide"' in script_content:
            checkin_m = re.search(
                r'"leading_kicker"\s*:\s*"Check-in".*?"leading_subtitle"\s*:\s*"([^"]*)"', script_content, re.DOTALL
            )
            if checkin_m:
                checkin_time = checkin_m.group(1)

        # Search for header_action.direction for address
        if '"id":"header_action.direction"' in script_content:
            address_m = re.search(
                r'"id"\s*:\s*"header_action\.direction".*?"subtitle"\s*:\s*"([^"]*)"', script_content, re.DOTALL
            )
            if address_m:
                address = address_m.group(1).strip()
                address_parts = address.split(",")
                if len(address_parts) >= 2:
                    city_name = address_parts[-1].strip()
                elif len(address_parts) == 1:
                    city_name = address_parts[0].strip()

        # Search for total price
        if '"id":"payment_summary"' in script_content:
            price_m = re.search(r"Gesamtkosten:\s*([\d,]+(?:\.\d{2})?)\s*€", script_content)
            if price_m:
                try:
                    price_str = price_m.group(1).replace(",", ".")
                    total_price = float(price_str)
                except ValueError:
                    pass

    address_div = soup.find("div", class_="rz78adb")
    if address_div:
        address_p = address_div.find("p", class_="_yz1jt7x", string=re.compile(r".+,.+"))
        if address_p:
            address_new = address_p.get_text().strip()
            if not address:
                address = address_new
            if address_new and ", " in address_new:
                address_parts = [part.strip() for part in address.split(",")]
                if len(address_parts) >= 1:
                    country_name = address_parts[-1]
                    if not city_name:
                        city_name = address_parts[-2] if len(address_parts) >= 2 else ""

    # Try to find phone number
    phone = None
    phone_match = re.search(r"tel:(\+[\d]+)", script_text)
    if phone_match:
        phone = phone_match.group(1)

    logger.info(f"Airbnb booking detected: {hotel_name}")

    # Search for amenities in the whole text as fallback for Airbnb
    all_text = soup.get_text()
    has_towels = "Handtücher" in all_text or "Grundausstattung" in all_text
    has_kitchen = "Küche" in all_text
    has_washing_machine = "Waschmaschine" in all_text
    has_breakfast = "Frühstück" in all_text

    return {
        "hotel_name": hotel_name,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "latitude": gps_lat,
        "longitude": gps_lon,
        "city_name": city_name,
        "country_name": country_name,
        "checkin_time": checkin_time,
        "address": address,
        "phone": phone,
        "has_kitchen": has_kitchen,
        "has_washing_machine": has_washing_machine,
        "has_breakfast": has_breakfast,
        "has_towels": has_towels,
        "total_price": total_price,
        "free_cancel_until": None,
    }


def extract_booking_info(html_path: Path) -> dict[str, Any]:
    """Extract booking info from a Booking.com or Airbnb HTML confirmation.

    Args:
        html_path: Path to the HTML file.

    Returns:
        Dictionary with booking information.
    """
    try:
        content = html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "lxml")
    except Exception as e:
        raise ParsingError(f"Failed to read/parse {html_path}: {e}") from e

    text = soup.get_text(" ", strip=True)

    # Try utag_data first (Booking.com)
    hotel_name = ""
    city_name = ""
    country_name = ""
    arrival_date = None
    departure_date = None
    checkin_time = None
    address = None
    phone = None
    gps_lat = gps_lon = None

    script_tag = soup.find("script", string=re.compile(r"window\.utag_data"))

    if not script_tag:
        airbnb_data = parse_airbnb_booking(soup)
        if airbnb_data:
            return airbnb_data

    if script_tag:
        script_text = script_tag.string
        h_m = re.search(r"hotel_name:\s*'([^']*)'", script_text)
        if h_m:
            hotel_name = h_m.group(1)
        c_m = re.search(r"city_name:\s*'([^']*)'", script_text)
        if c_m:
            city_name = c_m.group(1)
        co_m = re.search(r"country_name:\s*'([^']*)'", script_text)
        if co_m:
            country_name = co_m.group(1)
        di_m = re.search(r"date_in:\s*'([^']*)'", script_text)
        if di_m:
            arrival_date = di_m.group(1)
        do_m = re.search(r"date_out:\s*'([^']*)'", script_text)
        if do_m:
            departure_date = do_m.group(1)

    # Primary: hotel-details__address (new format)
    hotel_details_div = soup.find("div", class_="hotel-details__address")
    if hotel_details_div:
        if not hotel_name:
            h2_tag = hotel_details_div.find("h2")
            if h2_tag:
                hotel_name = h2_tag.text.strip()
        if not address:
            addr_strong = hotel_details_div.find("strong", string="Adresse:")
            if addr_strong and addr_strong.next_sibling:
                address = addr_strong.next_sibling.strip()
        phone_strong = hotel_details_div.find("strong", string="Telefon:")
        if phone_strong:
            phone_span = phone_strong.find_next("span", class_="u-phone")
            if phone_span:
                phone = phone_span.text.strip()
        gps_strong = hotel_details_div.find("strong", string="GPS-Koordinaten:")
        if gps_strong and gps_strong.next_sibling:
            gps_lat, gps_lon = parse_gps_coordinates(gps_strong.next_sibling.strip())

    # Dates section
    dates_section = soup.find("div", class_="row dates")
    if dates_section:
        arrival_col = dates_section.find("div", class_="col-6 dates__item")
        if arrival_col:
            if not arrival_date:
                day_elem = arrival_col.find("div", class_="summary__big-num")
                month_elem = arrival_col.find("div", class_="dates__month")
                if day_elem and month_elem:
                    year_m = re.search(r"\d{4}", text)
                    year = year_m.group(0) if year_m else "2026"
                    arrival_date = f"{year}-{MONTHS_DE.get(month_elem.text.strip(), '01')}-{int(day_elem.text.strip()):02d}"
            time_div = arrival_col.find("div", class_="dates__time")
            if time_div:
                time_m = re.search(r"(\d{1,2}:\d{2})\s*-", time_div.text.strip())
                if time_m:
                    checkin_time = time_m.group(1)

        departure_cols = dates_section.find_all("div", class_="col-6 dates__item")
        if len(departure_cols) > 1 and not departure_date:
            departure_col = departure_cols[1]
            day_elem = departure_col.find("div", class_="summary__big-num")
            month_elem = departure_col.find("div", class_="dates__month")
            if day_elem and month_elem:
                year_m = re.search(r"\d{4}", text)
                year = year_m.group(0) if year_m else "2026"
                departure_date = f"{year}-{MONTHS_DE.get(month_elem.text.strip(), '01')}-{int(day_elem.text.strip()):02d}"

    # Backup: old methods
    if not arrival_date:
        arr_elem = soup.find("h3", string="Anreise")
        if arr_elem:
            arrival_date = parse_date(arr_elem.find_next("div").text)

    if not departure_date:
        dep_elem = soup.find("h3", string="Abreise")
        if dep_elem:
            departure_date = parse_date(dep_elem.find_next("div").text)

    if not checkin_time:
        try:
            checkin_elem = soup.find("h3", string="Anreise")
            if checkin_elem:
                checkin_raw = checkin_elem.find_next("div").find_next("div").text
                checkin_time = checkin_raw.split("-")[0].strip()
        except (AttributeError, IndexError):
            pass

    if not address:
        addr_label = soup.find("div", string="Adresse")
        if addr_label:
            address = addr_label.find_next("div").text.strip()

    # Amenities
    has_kitchen = has_washing_machine = has_breakfast = has_towels = False
    amenities_header = soup.find("h5", string="Ausstattung")
    if amenities_header:
        parent = amenities_header.find_parent(["tr", "th"])
        td = parent.find_next("td") if parent else amenities_header.find_next("td")
        if td:
            txt = td.get_text(" ")
            has_kitchen, has_washing_machine = "Küche" in txt, "Waschmaschine" in txt
            has_towels = "Handtücher" in txt

    # General towel check if not found in amenities
    if not has_towels:
        has_towels = "Handtücher" in soup.get_text()

    meals_header = soup.find("h5", string="Mahlzeiten")
    if meals_header:
        parent = meals_header.find_parent(["tr", "th"])
        td = parent.find_next("td") if parent else meals_header.find_next("td")
        if td:
            has_breakfast = "Frühstück" in td.get_text(" ")

    # Price
    total_price = None
    price_elem = soup.find("div", attrs={"data-total-price": True})
    if price_elem:
        try:
            total_price = float(price_elem.get("data-total-price"))
        except (ValueError, TypeError):
            pass

    # Cancellation
    cancel_m = re.search(r"bis (\d{1,2}\. [A-Za-zäöüÄÖÜ]+ \d{4})", text)
    free_cancel_until = parse_date(cancel_m.group(1)) if cancel_m else None

    # Fallback for hotel_name
    if not hotel_name:
        h_elem = soup.select_one(".gta-modal-preview__hotel-name .bui-text")
        if h_elem:
            hotel_name = h_elem.text.strip()
        if not hotel_name:
            container = soup.find("div", class_="gta-modal-preview__hotel-name")
            if container:
                bui = container.find("div", class_="bui-text")
                if bui:
                    hotel_name = bui.text.strip()

    return {
        "hotel_name": hotel_name,
        "city_name": city_name,
        "country_name": country_name,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "checkin_time": checkin_time,
        "address": address,
        "phone": phone,
        "latitude": gps_lat,
        "longitude": gps_lon,
        "has_kitchen": has_kitchen,
        "has_washing_machine": has_washing_machine,
        "has_breakfast": has_breakfast,
        "has_towels": has_towels,
        "total_price": total_price,
        "free_cancel_until": free_cancel_until,
    }


def create_all_bookings(booking_dir: Path, search_radius_m: int, max_pois: int) -> list[dict[str, Any]]:
    """Create all bookings from HTML files in a directory.

    Args:
        booking_dir: Directory containing HTML booking confirmations.
        search_radius_m: Search radius for tourist sights in meters.
        max_pois: Maximum number of POIs to find per booking.

    Returns:
        List of dictionaries containing booking information.
    """
    all_bookings = []
    logger.debug("Start create_all_bookings")

    # Support both .htm and .html extensions
    html_files = list(booking_dir.glob("*.htm")) + list(booking_dir.glob("*.html"))

    for html_file in html_files:
        booking = extract_booking_info(html_file)

        if booking.get("latitude") is not None:
            lat, lon = booking["latitude"], booking["longitude"]
        else:
            try:
                lat, lon = geocode_address(booking["address"])
                booking["latitude"], booking["longitude"] = lat, lon
            except Exception as e:
                logger.error(f"Geocoding failed for {booking.get('address')}: {e}")
                all_bookings.append(booking)
                continue

        # Find tourist sights
        booking["tourist_sights"] = find_top_tourist_sights(lat, lon, radius=search_radius_m, limit=max_pois)
        all_bookings.append(booking)

    logger.debug("End create_all_bookings")
    return all_bookings
