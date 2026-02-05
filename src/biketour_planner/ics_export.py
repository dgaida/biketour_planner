"""ICS-Export-Modul für Reiseplanung.

Dieses Modul erstellt ICS-Kalenderdateien mit:
- Übernachtungsereignissen (mit vollständigen Buchungsdetails)
- Stornierungserinnerungen (48h vor Stornierungsfrist)
"""

from datetime import datetime, timedelta
from pathlib import Path

from .constants import ICS_MAX_LINE_LENGTH
from .logger import get_logger

# Initialisiere Logger
logger = get_logger()


def create_ics_event(
    summary: str,
    start_date: datetime,
    end_date: datetime,
    description: str = "",
    location: str = "",
) -> str:
    """Erstellt einen einzelnen ICS-Event-Block.

    Args:
        summary: Titel des Events.
        start_date: Startdatum und -zeit des Events.
        end_date: Enddatum und -zeit des Events.
        description: Optionale Beschreibung des Events.
        location: Optionaler Ort des Events.

    Returns:
        ICS-formatierter Event-String im VCALENDAR-Format.

    Note:
        - Verwendet VALUE=DATE für Ganztagesevents
        - Escapet Sonderzeichen gemäß ICS-Spezifikation
        - Bricht lange Zeilen bei 75 Zeichen um
    """
    # Generiere eindeutige UID basierend auf Zeitstempel und Summary
    uid = f"{start_date.strftime('%Y%m%d%H%M%S')}-{hash(summary)}@biketour-planner"

    # Erstelle Zeitstempel für CREATED und DTSTAMP
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Für Ganztagesevents (keine Uhrzeit)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    # Escape Sonderzeichen in Text (ICS-Spec: Kommas, Semikolons, Backslashes)
    def escape_text(text: str) -> str:
        """Escapet Sonderzeichen für ICS-Format."""
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    event = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{start_str}",
        f"DTEND;VALUE=DATE:{end_str}",
        f"SUMMARY:{escape_text(summary)}",
    ]

    if description:
        # Breche lange Zeilen nach ICS-Spec (max 75 Zeichen pro Zeile)
        desc_escaped = escape_text(description)
        desc_line = f"DESCRIPTION:{desc_escaped}"

        # Umbrechen bei > ICS_MAX_LINE_LENGTH Zeichen (mit Continuation auf neuer Zeile)
        if len(desc_line) > ICS_MAX_LINE_LENGTH:
            lines = []
            current_line = desc_line[:ICS_MAX_LINE_LENGTH]
            remaining = desc_line[ICS_MAX_LINE_LENGTH:]
            lines.append(current_line)

            while remaining:
                lines.append(" " + remaining[: ICS_MAX_LINE_LENGTH - 1])  # Space-Prefix für Continuation
                remaining = remaining[ICS_MAX_LINE_LENGTH - 1 :]

            event.extend(lines)
        else:
            event.append(desc_line)

    if location:
        event.append(f"LOCATION:{escape_text(location)}")

    event.append("END:VEVENT")

    return "\n".join(event)


def create_accommodation_description(booking: dict) -> str:
    """Erstellt eine Beschreibung für Übernachtungsereignisse.

    Extrahiert alle relevanten Informationen aus dem Buchungs-Dictionary
    und formatiert sie für die Kalenderbeschreibung.

    Args:
        booking: Buchungs-Dictionary mit Informationen zur Unterkunft.
                Verwendet werden:
                - hotel_name: Name der Unterkunft
                - address: Vollständige Adresse
                - phone: Telefonnummer
                - checkin_time: Früheste Check-in-Zeit
                - has_kitchen: Boolean für Küchenausstattung
                - has_washing_machine: Boolean für Waschmaschine
                - has_breakfast: Boolean für Frühstück
                - total_price: Gesamtpreis der Buchung
                - free_cancel_until: Datum der kostenlosen Stornierungsfrist
                - latitude, longitude: GPS-Koordinaten

    Returns:
        Formatierter mehrzeiliger Beschreibungstext.
    """
    lines = []

    # Unterkunftsname
    if booking.get("hotel_name"):
        lines.append(f"Unterkunft: {booking['hotel_name']}")

    # Adresse
    if booking.get("address"):
        lines.append(f"Adresse: {booking['address']}")

    # Telefon
    if booking.get("phone"):
        lines.append(f"Telefon: {booking['phone']}")

    # Check-in Zeit
    if booking.get("checkin_time"):
        lines.append(f"Check-in ab: {booking['checkin_time']}")

    # Ausstattung
    amenities = []
    if booking.get("has_kitchen"):
        amenities.append("Küche")
    if booking.get("has_washing_machine"):
        amenities.append("Waschmaschine")
    if booking.get("has_breakfast"):
        amenities.append("Frühstück")

    if amenities:
        lines.append(f"Ausstattung: {', '.join(amenities)}")

    # Preis
    if booking.get("total_price"):
        lines.append(f"Preis: {booking['total_price']:.2f} €")

    # Stornierungsfrist
    if booking.get("free_cancel_until"):
        lines.append(f"Kostenlose Stornierung bis: {booking['free_cancel_until']}")

    # GPS-Koordinaten (als Google Maps Link)
    if booking.get("latitude") and booking.get("longitude"):
        lat = booking["latitude"]
        lon = booking["longitude"]
        lines.append(f"Google Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}")

    return "\n".join(lines)


def export_bookings_to_ics(
    bookings: list[dict],
    output_path: Path,
) -> None:
    """Exportiert Buchungsinformationen in eine ICS-Kalenderdatei.

    Erstellt eine iCalendar-kompatible Datei (.ics) mit zwei Arten von Events:

    1. **Übernachtungsereignisse**: Ganztagesevents von arrival_date bis
       departure_date mit vollständigen Buchungsdetails (Adresse, Ausstattung,
       Preis, etc.)

    2. **Stornierungserinnerungen**: Ganztagesevents 48 Stunden vor der
       kostenlosen Stornierungsfrist (free_cancel_until) als Reminder.

    Die generierten ICS-Dateien können in alle gängigen Kalender-Anwendungen
    importiert werden (Google Calendar, Outlook, Apple Calendar, etc.).

    Args:
        bookings: Liste mit Buchungs-Dictionaries. Erforderliche Keys:
                 - arrival_date: ISO-Datum (YYYY-MM-DD)
                 - departure_date: ISO-Datum (YYYY-MM-DD)
                 - hotel_name: Name der Unterkunft
                 Optional:
                 - address, city_name, phone, checkin_time
                 - has_kitchen, has_washing_machine, has_breakfast
                 - total_price
                 - free_cancel_until: ISO-Datum der Stornierungsfrist
                 - latitude, longitude
        output_path: Pfad für die Ausgabe-ICS-Datei.

    Example:
        >>> bookings = [
        ...     {
        ...         "hotel_name": "Hotel Alpenblick",
        ...         "arrival_date": "2026-05-15",
        ...         "departure_date": "2026-05-17",
        ...         "address": "Hauptstraße 1, Garmisch",
        ...         "has_kitchen": True,
        ...         "total_price": 180.00,
        ...         "free_cancel_until": "2026-05-10"
        ...     }
        ... ]
        >>> export_bookings_to_ics(bookings, Path("reise.ics"))
        ✅ ICS-Datei erstellt: reise.ics
           📅 1 Übernachtungen
           ⚠️  1 Stornierungserinnerungen
    """
    logger.info("Starte ICS-Export...")

    # ICS-Header
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Biketour Planner//ICS Export//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Kroatien Radtour 2026",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]

    # Sortiere Buchungen nach Anreisedatum
    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    accommodation_count = 0
    cancellation_count = 0

    for booking in bookings_sorted:
        # 1. Übernachtungsereignis
        arrival_date = booking.get("arrival_date")
        departure_date = booking.get("departure_date")

        if arrival_date and departure_date:
            try:
                start = datetime.fromisoformat(arrival_date)
                # ICS-Enddatum ist exklusiv, daher +1 Tag für korrekte Anzeige
                end = datetime.fromisoformat(departure_date)

                hotel_name = booking.get("hotel_name", "Unterkunft")
                city_name = booking.get("city_name", "")

                summary = f"🏨 {hotel_name}"
                if city_name:
                    summary += f" ({city_name})"

                location = booking.get("address", "")
                description = create_accommodation_description(booking)

                event = create_ics_event(
                    summary=summary,
                    start_date=start,
                    end_date=end,
                    description=description,
                    location=location,
                )

                ics_content.append(event)
                accommodation_count += 1

                logger.debug(f"Übernachtung hinzugefügt: {hotel_name} ({arrival_date} - {departure_date})")

            except ValueError as e:
                logger.warning(f"Ungültiges Datum bei {booking.get('hotel_name', 'Unbekannt')}: {e}")

        # 2. Stornierungserinnerung (48h vor Stornierungsfrist)
        free_cancel_until = booking.get("free_cancel_until")

        if free_cancel_until:
            try:
                cancel_date = datetime.fromisoformat(free_cancel_until)
                # Erinnerung 48h vorher
                reminder_date = cancel_date - timedelta(hours=48)
                # Enddatum = Startdatum + 1 Tag (Ganztagesevent)
                reminder_end = reminder_date + timedelta(days=1)

                hotel_name = booking.get("hotel_name", "Unterkunft")

                summary = f"⚠️ Stornierungsfrist: {hotel_name}"

                description_lines = [
                    f"ERINNERUNG: Kostenlose Stornierung möglich bis {free_cancel_until}",
                    f"Unterkunft: {hotel_name}",
                ]

                if booking.get("address"):
                    description_lines.append(f"Adresse: {booking['address']}")

                if booking.get("total_price"):
                    description_lines.append(f"Preis: {booking['total_price']:.2f} €")

                description = "\n".join(description_lines)

                event = create_ics_event(
                    summary=summary,
                    start_date=reminder_date,
                    end_date=reminder_end,
                    description=description,
                    location="",
                )

                ics_content.append(event)
                cancellation_count += 1

                logger.debug(f"Stornierungserinnerung hinzugefügt: {hotel_name} (48h vor {free_cancel_until})")

            except ValueError as e:
                logger.warning(f"Ungültiges Stornierungsdatum bei {booking.get('hotel_name', 'Unbekannt')}: {e}")

    # ICS-Footer
    ics_content.append("END:VCALENDAR")

    # Schreibe ICS-Datei
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(ics_content), encoding="utf-8")

    logger.info(f"✅ ICS-Datei erstellt: {output_path}")
    logger.info(f"   📅 {accommodation_count} Übernachtungen")
    logger.info(f"   ⚠️  {cancellation_count} Stornierungserinnerungen")
