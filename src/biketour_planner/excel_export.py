import json
import re
from pathlib import Path
from typing import Dict
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from datetime import datetime, timedelta
from .geoapify import get_names_as_comma_separated_string


def extract_city_name(address: str) -> str:
    """Extrahiert nur den Ortsnamen aus einer vollständigen Adresse.

    Args:
        address: Vollständige Adresse, z.B. "Straße 1, 21000 Split, Kroatien"

    Returns:
        Nur der Ortsname, z.B. "Split"
    """
    # Format: "Straße, PLZ Stadt, Land"
    # Wir wollen nur "Stadt"

    # Entferne Land am Ende (nach letztem Komma)
    parts = address.split(",")
    if len(parts) >= 2:
        # Nimm den vorletzten Teil (sollte "PLZ Stadt" sein)
        city_part = parts[-2].strip()

        # Entferne PLZ (führende Zahlen und Leerzeichen)
        city_match = re.search(r"^\d+\s+(.+)$", city_part)
        if city_match:
            return city_match.group(1).strip()

        # Falls kein PLZ-Muster, gib den ganzen Teil zurück
        return city_part

    return address


def create_accommodation_text(booking: Dict) -> str:
    """Erstellt den Unterkunftstext mit Name, Adresse und Ausstattung.

    Args:
        booking: Buchungsinformationen-Dictionary

    Returns:
        Formatierter Text für die Excel-Zelle
    """
    text_parts = []

    # Hotelname
    if booking.get("hotel_name"):
        text_parts.append(booking["hotel_name"])

    # Adresse
    if booking.get("address"):
        text_parts.append(booking["address"])

    # Ausstattung
    amenities = []
    if booking.get("has_washing_machine"):
        amenities.append("Wasch")
    if booking.get("has_kitchen"):
        amenities.append("Küche")

    if amenities:
        text_parts.append(", ".join(amenities))

    return "\n".join(text_parts)


def export_bookings_to_excel(json_path: Path, template_path: Path, output_path: Path, start_row: int = 4) -> None:
    """Exportiert Buchungsinformationen in eine Excel-Datei basierend auf Template.

    Fügt automatisch Leerzeilen für Tage ohne Buchung ein (zwischen departure_date
    einer Buchung und arrival_date der nächsten Buchung).

    Args:
        json_path: Pfad zur JSON-Datei mit Buchungen
        template_path: Pfad zur Excel-Template-Datei
        output_path: Pfad für die Ausgabe-Excel-Datei
        start_row: Zeile ab der die Daten eingefügt werden (1-basiert)
    """
    # JSON laden
    with open(json_path, "r", encoding="utf-8") as f:
        bookings = json.load(f)

    # Nach Anreisedatum sortieren
    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    # Template laden
    wb = load_workbook(template_path)
    ws = wb.active

    # Vorherige Stadt für Start-Ziel-Bestimmung
    previous_city = None
    previous_departure_date = None

    # Aktueller Tageszähler
    day_counter = 1

    # Aktuelle Excel-Zeile
    current_row = start_row

    # Daten einfügen
    for booking in bookings_sorted:
        # Prüfe ob Leerzeilen für Zwischentage eingefügt werden müssen
        if previous_departure_date and booking.get("arrival_date"):
            try:
                prev_departure = datetime.fromisoformat(previous_departure_date)
                current_arrival = datetime.fromisoformat(booking["arrival_date"])

                # Berechne Differenz in Tagen
                days_between = (current_arrival - prev_departure).days

                # Füge Leerzeilen ein (eine Zeile pro Tag dazwischen)
                if days_between > 0:
                    for day_offset in range(days_between):
                        # Spalte A: Tageszähler
                        ws[f"A{current_row}"] = day_counter

                        # Spalte B: Datum des Zwischentags
                        intermediate_date = prev_departure + timedelta(days=day_offset)
                        ws[f"B{current_row}"] = intermediate_date
                        ws[f"B{current_row}"].number_format = "DDD, DD.MM.YYYY"

                        # Spalte C: Startort (vorherige Stadt)
                        if previous_city:
                            ws[f"C{current_row}"] = previous_city

                        # Restliche Spalten bleiben leer

                        day_counter += 1
                        current_row += 1

            except ValueError:
                # Falls Datumskonvertierung fehlschlägt, überspringe die Lückenprüfung
                pass

        # Normale Buchungszeile einfügen
        row = current_row

        # Spalte A: Tageszähler
        ws[f"A{row}"] = day_counter

        # Spalte B: Datum
        arrival_date = booking.get("arrival_date", "")
        if arrival_date:
            try:
                # Konvertiere ISO-Datum zu datetime für bessere Formatierung
                date_obj = datetime.fromisoformat(arrival_date)
                ws[f"B{row}"] = date_obj
                ws[f"B{row}"].number_format = "DDD, DD.MM.YYYY"
            except ValueError:
                ws[f"B{row}"] = arrival_date

        # Spalte C: Startort (vorherige Stadt)
        if previous_city:
            ws[f"C{row}"] = previous_city

        # Spalte D: Zielort (aktuelle Stadt)
        current_city = extract_city_name(booking.get("address", ""))
        ws[f"D{row}"] = current_city

        # Spalte E: km
        ws[f"E{row}"] = booking.get("total_distance_km", "")

        # Spalte F: Unterkunft mit Name, Adresse und Ausstattung
        accommodation_text = create_accommodation_text(booking)
        ws[f"F{row}"] = accommodation_text
        ws[f"F{row}"].alignment = Alignment(wrap_text=True, vertical="top")

        ws[f"G{row}"] = f"{booking.get('total_ascent_m', '')} / {booking.get('max_elevation_m', '')}"

        cs_string_names = get_names_as_comma_separated_string(booking.get("tourist_sights", None))

        ws[f"I{row}"] = cs_string_names

        # Spalte J: Preis
        ws[f"J{row}"] = booking.get("total_price", "")

        ws[f"K{row}"] = f"Stornierung bis: {booking.get('free_cancel_until', '')}"

        # Aktualisiere Variablen für nächste Iteration
        previous_city = current_city
        previous_departure_date = booking.get("departure_date")
        day_counter += 1
        current_row += 1

    # Ausgabe speichern
    wb.save(output_path)
    print(f"Excel-Datei erstellt: {output_path}")


if __name__ == "__main__":
    # Beispielaufruf
    export_bookings_to_excel(
        json_path=Path("output/bookings.json"),
        template_path=Path("Reiseplanung_Fahrrad template.xlsx"),
        output_path=Path("output/Reiseplanung_Kroatien_2026.xlsx"),
        start_row=4,  # Passe an, ab welcher Zeile die Daten stehen sollen
    )
