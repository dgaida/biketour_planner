import re
from bs4 import BeautifulSoup
from pathlib import Path

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


def extract_booking_info(html_path: Path):
    """Extrahiert Buchungsinformationen aus einer Booking.com HTML-Bestätigung.

    Args:
        html_path: Pfad zur HTML-Datei

    Returns:
        Dictionary mit Buchungsinformationen (hotel_name, arrival_date, etc.)
    """
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    text = soup.get_text(" ", strip=True)

    # Versuche zuerst Daten aus utag_data JavaScript zu extrahieren
    hotel_name = ""
    arrival_date = None
    departure_date = None

    script_tag = soup.find("script", string=re.compile(r"window\.utag_data"))
    if script_tag:
        script_text = script_tag.string

        # Extrahiere hotel_name
        hotel_match = re.search(r"hotel_name:\s*'([^']*)'", script_text)
        if hotel_match:
            hotel_name = hotel_match.group(1)

        # Extrahiere date_in (Anreise)
        date_in_match = re.search(r"date_in:\s*'([^']*)'", script_text)
        if date_in_match:
            arrival_date = date_in_match.group(1)

        # Extrahiere date_out (Abreise)
        date_out_match = re.search(r"date_out:\s*'([^']*)'", script_text)
        if date_out_match:
            departure_date = date_out_match.group(1)

    # Fallback: Versuche Daten aus HTML zu extrahieren falls JavaScript-Extraktion fehlschlägt
    if not arrival_date:
        arrival_elem = soup.find("h3", string="Anreise")
        if arrival_elem:
            arrival_date = parse_date(arrival_elem.find_next("div").text)

    if not departure_date:
        departure_elem = soup.find("h3", string="Abreise")
        if departure_elem:
            departure_date = parse_date(departure_elem.find_next("div").text)

    # früheste Check-in-Zeit
    checkin_raw = soup.find("h3", string="Anreise").find_next("div").find_next("div").text
    checkin_time = checkin_raw.split("-")[0].strip()

    # Adresse
    address_label = soup.find("div", string="Adresse")
    address = address_label.find_next("div").text.strip()

    # Ausstattung
    amenities_text = soup.find("h5", string="Ausstattung").find_parent("th").find_next("td").get_text(" ")
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

    return {
        "hotel_name": hotel_name,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "checkin_time": checkin_time,
        "address": address,
        "has_kitchen": has_kitchen,
        "has_washing_machine": has_washing_machine,
        "total_price": total_price,
        "free_cancel_until": free_cancel_until,
    }
