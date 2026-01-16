import re
from bs4 import BeautifulSoup
from pathlib import Path

from .logger import get_logger

# Initialisiere Logger
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


def parse_date(text):
    """Parse ein deutsches Datum im Format 'Tag. Monat Jahr'.

    Args:
        text: String mit Datumsangabe, z.B. "So., 8. März 2026"

    Returns:
        ISO-formatiertes Datum (YYYY-MM-DD) oder None bei Fehler
    """
    # z.B. "So., 8. März 2026"
    m = re.search(r"(\d{1,2})\. ([A-Za-zäöüÄÖÜ]+) (\d{4})", text)
    if not m:
        return None
    day, month, year = m.groups()
    return f"{year}-{MONTHS_DE[month]}-{int(day):02d}"


def parse_gps_coordinates(gps_text: str) -> tuple:
    """Konvertiert GPS-Koordinaten von Grad/Minuten zu Dezimalgrad.

    Args:
        gps_text: GPS-String im Format "N 043° 56.181, E 15° 26.645"

    Returns:
        Tuple (latitude, longitude) in Dezimalgrad oder (None, None)
    """
    if not gps_text:
        return None, None

    # Extrahiere N/S Grad und Minuten
    lat_match = re.search(r"([NS])\s*(\d+)[°&deg;]+\s*([\d.]+)", gps_text)
    # Extrahiere E/W Grad und Minuten
    lon_match = re.search(r"([EW])\s*(\d+)[°&deg;]+\s*([\d.]+)", gps_text)

    if not lat_match or not lon_match:
        return None, None

    # Konvertiere zu Dezimalgrad: Grad + (Minuten / 60)
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


def parse_airbnb_booking(soup: BeautifulSoup) -> dict:
    """Extrahiert Buchungsinformationen aus einer Airbnb HTML-Bestätigung.

    Args:
        soup: BeautifulSoup-Objekt der HTML-Seite

    Returns:
        Dictionary mit Buchungsinformationen oder None bei Fehler
    """
    # Suche nach Script-Tag mit Airbnb-Daten (metadata)
    script_tag = soup.find("script", string=re.compile(r'"metadata".*"title".*"check_in_date"'))

    if not script_tag:
        return None

    script_text = script_tag.string

    # Extrahiere title (Name der Unterkunft)
    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', script_text)
    hotel_name = title_match.group(1) if title_match else None

    # Extrahiere check_in_date (Ankunftsdatum)
    checkin_match = re.search(r'"check_in_date"\s*:\s*"([^"]*)"', script_text)
    arrival_date = checkin_match.group(1) if checkin_match else None

    # Extrahiere check_out_date (Abreisedatum)
    checkout_match = re.search(r'"check_out_date"\s*:\s*"([^"]*)"', script_text)
    departure_date = checkout_match.group(1) if checkout_match else None

    # Extrahiere GPS-Koordinaten
    lat_match = re.search(r'"lat"\s*:\s*([\d.]+)', script_text)
    gps_lat = float(lat_match.group(1)) if lat_match else None

    lng_match = re.search(r'"lng"\s*:\s*([\d.]+)', script_text)
    gps_lon = float(lng_match.group(1)) if lng_match else None

    # Validiere dass mindestens die kritischen Felder gefunden wurden
    if not (hotel_name and arrival_date and departure_date):
        logger.warning("Airbnb-Parser: Kritische Felder fehlen")
        return None

    # Suche nach zusätzlichen Informationen in SSRUIStateToken
    city_name = ""
    country_name = ""
    address = None
    checkin_time = None
    total_price = None

    # Suche in allen Script-Tags nach den spezifischen JSON-Strukturen
    for script in soup.find_all("script"):
        if not script.string:
            continue

        script_content = script.string

        # Suche nach checkin_checkout_arrival_guide für Check-in/out Zeiten
        if '"id":"checkin_checkout_arrival_guide"' in script_content:
            # Extrahiere Check-in Zeit
            checkin_match = re.search(
                r'"leading_kicker"\s*:\s*"Check-in".*?"leading_subtitle"\s*:\s*"([^"]*)"', script_content, re.DOTALL
            )
            if checkin_match:
                checkin_time = checkin_match.group(1)

        # Suche nach header_action.direction für Adresse
        if '"id":"header_action.direction"' in script_content:
            # Extrahiere Adresse aus subtitle
            address_match = re.search(
                r'"id"\s*:\s*"header_action\.direction".*?"subtitle"\s*:\s*"([^"]*)"', script_content, re.DOTALL
            )
            if address_match:
                address = address_match.group(1).strip()
                # Extrahiere Stadt (letzter Teil nach Komma)
                address_parts = address.split(",")
                if len(address_parts) >= 2:
                    city_name = address_parts[-1].strip()
                elif len(address_parts) == 1:
                    city_name = address_parts[0].strip()

        # Suche nach Gesamtpreis
        if '"id":"payment_summary"' in script_content:
            price_match = re.search(r"Gesamtkosten:\s*([\d,]+(?:\.\d{2})?)\s*€", script_content)
            if price_match:
                try:
                    price_str = price_match.group(1).replace(",", ".")
                    total_price = float(price_str)
                except ValueError:
                    pass

    address_div = soup.find("div", class_="rz78adb")
    if address_div:
        # Suche nach Adresse in <p class="_yz1jt7x">
        address_p = address_div.find("p", class_="_yz1jt7x", string=re.compile(r".+,.+"))
        if address_p:
            address_new = address_p.get_text().strip()
            if not address:
                address = address_new
            #
            if address_new and ", " in address_new:
                address_parts = [part.strip() for part in address.split(",")]
                if len(address_parts) >= 1:
                    country_name = address_parts[-1]  # Letzter Teil ist das Land
                    if not city_name:
                        city_name = address_parts[-2] if len(address_parts) >= 2 else ""

    # Versuche Telefonnummer zu finden
    phone = None
    phone_match = re.search(r"tel:(\+[\d]+)", script_text)
    if phone_match:
        phone = phone_match.group(1)

    logger.info(f"Airbnb-Buchung erkannt: {hotel_name}")

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
        "has_kitchen": False,  # Airbnb liefert nicht alle Ausstattungsdetails
        "has_washing_machine": False,
        "total_price": total_price,
        "free_cancel_until": None,  # Airbnb hat andere Stornierungslogik
    }


def extract_booking_info(html_path: Path):
    """Extrahiert Buchungsinformationen aus einer Booking.com oder Airbnb HTML-Bestätigung.

    Args:
        html_path: Pfad zur HTML-Datei

    Returns:
        Dictionary mit Buchungsinformationen (hotel_name, arrival_date, etc.)
    """
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    text = soup.get_text(" ", strip=True)

    # Versuche zuerst Daten aus utag_data JavaScript zu extrahieren (Booking.com)
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

    # Falls kein Booking.com Format, versuche Airbnb
    if not script_tag:
        airbnb_data = parse_airbnb_booking(soup)
        if airbnb_data:
            return airbnb_data
        # Falls auch Airbnb fehlschlägt, fahre mit Booking.com Fallback-Logik fort

    if script_tag:
        script_text = script_tag.string

        # Extrahiere hotel_name
        hotel_match = re.search(r"hotel_name:\s*'([^']*)'", script_text)
        if hotel_match:
            hotel_name = hotel_match.group(1)

        # Extrahiere city_name
        city_match = re.search(r"city_name:\s*'([^']*)'", script_text)
        if city_match:
            city_name = city_match.group(1)

        # Extrahiere hotel_name
        country_match = re.search(r"country_name:\s*'([^']*)'", script_text)
        if country_match:
            country_name = country_match.group(1)

        # Extrahiere date_in (Anreise)
        date_in_match = re.search(r"date_in:\s*'([^']*)'", script_text)
        if date_in_match:
            arrival_date = date_in_match.group(1)

        # Extrahiere date_out (Abreise)
        date_out_match = re.search(r"date_out:\s*'([^']*)'", script_text)
        if date_out_match:
            departure_date = date_out_match.group(1)

    # PRIMÄR: Versuche Daten aus booking-details zu extrahieren (neues Format)
    hotel_details_div = soup.find("div", class_="hotel-details__address")
    if hotel_details_div:
        # Hotelname aus <h2> Tag
        if not hotel_name:
            h2_tag = hotel_details_div.find("h2")
            if h2_tag:
                hotel_name = h2_tag.text.strip()

        # Adresse
        if not address:
            address_strong = hotel_details_div.find("strong", string="Adresse:")
            if address_strong:
                address_text = address_strong.next_sibling
                if address_text:
                    address = address_text.strip()

        # Telefon
        phone_strong = hotel_details_div.find("strong", string="Telefon:")
        if phone_strong:
            phone_span = phone_strong.find_next("span", class_="u-phone")
            if phone_span:
                phone = phone_span.text.strip()

        # GPS-Koordinaten
        gps_strong = hotel_details_div.find("strong", string="GPS-Koordinaten:")
        if gps_strong:
            gps_text = gps_strong.next_sibling
            if gps_text:
                gps_coordinates = gps_text.strip()
                gps_lat, gps_lon = parse_gps_coordinates(gps_coordinates)

    # Anreise-/Abreisedatum und Check-in-Zeit aus dates-Sektion
    dates_section = soup.find("div", class_="row dates")
    if dates_section:
        # Anreise
        arrival_col = dates_section.find("div", class_="col-6 dates__item")
        if arrival_col and not arrival_date:
            day_elem = arrival_col.find("div", class_="summary__big-num")
            month_elem = arrival_col.find("div", class_="dates__month")

            if day_elem and month_elem:
                day = day_elem.text.strip()
                month = month_elem.text.strip()

                # Jahr aus Text extrahieren (Fallback)
                year_match = re.search(r"\d{4}", text)
                year = year_match.group(0) if year_match else "2026"

                arrival_date = f"{year}-{MONTHS_DE.get(month, '01')}-{int(day):02d}"

            # Check-in-Zeit - FIX: Nur wenn noch nicht gesetzt
            if not checkin_time:
                time_div = arrival_col.find("div", class_="dates__time")
                if time_div:
                    time_text = time_div.text.strip()
                    time_match = re.search(r"(\d{1,2}:\d{2})\s*-", time_text)
                    if time_match:
                        checkin_time = time_match.group(1)

        # Abreise
        departure_cols = dates_section.find_all("div", class_="col-6 dates__item")
        if len(departure_cols) > 1 and not departure_date:
            departure_col = departure_cols[1]
            day_elem = departure_col.find("div", class_="summary__big-num")
            month_elem = departure_col.find("div", class_="dates__month")

            if day_elem and month_elem:
                day = day_elem.text.strip()
                month = month_elem.text.strip()

                # Jahr aus Text extrahieren (Fallback)
                year_match = re.search(r"\d{4}", text)
                year = year_match.group(0) if year_match else "2026"

                departure_date = f"{year}-{MONTHS_DE.get(month, '01')}-{int(day):02d}"

    # BACKUP: Fallback zu alten Extraktionsmethoden
    if not arrival_date:
        arrival_elem = soup.find("h3", string="Anreise")
        if arrival_elem:
            arrival_date = parse_date(arrival_elem.find_next("div").text)

    if not departure_date:
        departure_elem = soup.find("h3", string="Abreise")
        if departure_elem:
            departure_date = parse_date(departure_elem.find_next("div").text)

    # früheste Check-in-Zeit (alter Fallback) - FIX: Nur wenn noch nicht gesetzt
    if not checkin_time:
        try:
            checkin_elem = soup.find("h3", string="Anreise")
            if checkin_elem:
                checkin_raw = checkin_elem.find_next("div").find_next("div").text
                checkin_time = checkin_raw.split("-")[0].strip()
        except (AttributeError, IndexError):
            pass

    # Adresse (alter Fallback)
    if not address:
        address_label = soup.find("div", string="Adresse")
        if address_label:
            address = address_label.find_next("div").text.strip()

    # Ausstattung - FIX: Suche im richtigen Parent-Element
    has_kitchen = False
    has_washing_machine = False
    amenities_header = soup.find("h5", string="Ausstattung")
    if amenities_header:
        # Finde das parent <tr> oder <th> Element und dann das nächste <td>
        amenities_parent = amenities_header.find_parent(["tr", "th"])
        if amenities_parent:
            amenities_td = amenities_parent.find_next("td")
            if amenities_td:
                amenities_text = amenities_td.get_text(" ")
                has_kitchen = "Küche" in amenities_text
                has_washing_machine = "Waschmaschine" in amenities_text

    # Gesamtpreis
    total_price = None
    price_elem = soup.find("div", attrs={"data-total-price": True})
    if price_elem:
        try:
            total_price = float(price_elem.get("data-total-price"))
        except (ValueError, TypeError):
            pass

    # kostenlose Stornierung
    cancel_match = re.search(r"bis (\d{1,2}\. [A-Za-zäöüÄÖÜ]+ \d{4})", text)
    free_cancel_until = parse_date(cancel_match.group(1)) if cancel_match else None

    # Fallback für hotel_name falls nicht in utag_data
    if not hotel_name:
        # Versuch 1: CSS-Klasse mit select_one (unterstützt CSS-Selektoren)
        hotel_elem = soup.select_one(".gta-modal-preview__hotel-name .bui-text")
        if hotel_elem:
            hotel_name = hotel_elem.text.strip()

        # Versuch 2: Alternative Schreibweise
        if not hotel_name:
            hotel_container = soup.find("div", class_="gta-modal-preview__hotel-name")
            if hotel_container:
                bui_text = hotel_container.find("div", class_="bui-text")
                if bui_text:
                    hotel_name = bui_text.text.strip()

    booking = {
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
        "total_price": total_price,
        "free_cancel_until": free_cancel_until,
    }

    logger.debug(f"booking: {booking}")

    return booking
