import re
import json
from bs4 import BeautifulSoup
from pathlib import Path

MONTHS_DE = {
    "Januar": "01", "Februar": "02", "März": "03", "April": "04",
    "Mai": "05", "Juni": "06", "Juli": "07", "August": "08",
    "September": "09", "Oktober": "10", "November": "11", "Dezember": "12"
}


def parse_date(text):
    # z.B. "So., 8. März 2026"
    m = re.search(r"(\d{1,2})\. ([A-Za-zäöüÄÖÜ]+) (\d{4})", text)
    if not m:
        return None
    day, month, year = m.groups()
    return f"{year}-{MONTHS_DE[month]}-{int(day):02d}"


def extract_booking_info(html_path: Path):
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    text = soup.get_text(" ", strip=True)

    # An- / Abreise
    arrival_date = parse_date(
        soup.find("h3", string="Anreise").find_next("div").text
    )
    departure_date = parse_date(
        soup.find("h3", string="Abreise").find_next("div").text
    )

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

    # kostenlose Stornierung
    cancel_match = re.search(r"bis (\d{1,2}\. [A-Za-zäöüÄÖÜ]+ \d{4})", text)
    free_cancel_until = parse_date(cancel_match.group(1)) if cancel_match else None

    hotel_name = soup.select_one(".gta-modal-preview__hotel-name .bui-text").text.strip()

    return {
        "hotel_name": hotel_name,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "checkin_time": checkin_time,
        "address": address,
        "has_kitchen": has_kitchen,
        "has_washing_machine": has_washing_machine,
        "free_cancel_until": free_cancel_until,
    }
