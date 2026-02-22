from datetime import datetime

from biketour_planner.ics_export import create_accommodation_description, create_ics_event, export_bookings_to_ics


def test_create_ics_event_basic():
    summary = "Test Event"
    start_date = datetime(2026, 5, 15)
    end_date = datetime(2026, 5, 17)

    event_str = create_ics_event(summary, start_date, end_date)

    assert "BEGIN:VEVENT" in event_str
    assert "SUMMARY:Test Event" in event_str
    assert "DTSTART;VALUE=DATE:20260515" in event_str
    assert "DTEND;VALUE=DATE:20260517" in event_str
    assert "END:VEVENT" in event_str


def test_create_ics_event_with_description_and_location():
    summary = "Test Event"
    start_date = datetime(2026, 5, 15)
    end_date = datetime(2026, 5, 17)
    description = "A long description that might need wrapping if it was long enough but this one is short."
    location = "Test Location, 12345 City"

    event_str = create_ics_event(summary, start_date, end_date, description, location)

    assert "DESCRIPTION:A long description" in event_str
    assert "LOCATION:Test Location\\, 12345 City" in event_str


def test_create_ics_event_wrapping():
    summary = "Test Event"
    start_date = datetime(2026, 5, 15)
    end_date = datetime(2026, 5, 17)
    # Long description to trigger wrapping (> 75 chars)
    description = "This is a very long description that definitely exceeds seventy-five characters and should therefore be wrapped according to the ICS specification. It needs to be long enough to test the while loop in the wrapping logic."

    event_str = create_ics_event(summary, start_date, end_date, description)

    assert "DESCRIPTION:" in event_str
    # Check for continuation lines (lines starting with a space)
    assert "\n " in event_str


def test_create_accommodation_description_complete():
    booking = {
        "hotel_name": "Hotel Test",
        "address": "Test Street 1",
        "phone": "+49 123 456",
        "checkin_time": "15:00",
        "has_kitchen": True,
        "has_washing_machine": True,
        "has_breakfast": True,
        "total_price": 123.45,
        "free_cancel_until": "2026-05-10",
        "latitude": 45.123,
        "longitude": 15.456,
    }

    desc = create_accommodation_description(booking)

    assert "Unterkunft: Hotel Test" in desc
    assert "Adresse: Test Street 1" in desc
    assert "Telefon: +49 123 456" in desc
    assert "Check-in ab: 15:00" in desc
    assert "Ausstattung: Küche, Waschmaschine, Frühstück" in desc
    assert "Preis: 123.45 €" in desc
    assert "Kostenlose Stornierung bis: 2026-05-10" in desc
    assert "Google Maps: https://www.google.com/maps/search/?api=1&query=45.123,15.456" in desc


def test_export_bookings_to_ics(tmp_path):
    output_file = tmp_path / "test.ics"
    bookings = [
        {
            "hotel_name": "Hotel A",
            "city_name": "City A",
            "arrival_date": "2026-05-15",
            "departure_date": "2026-05-16",
            "address": "Street A",
            "free_cancel_until": "2026-05-10",
        }
    ]

    export_bookings_to_ics(bookings, output_file)

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "🏨 Hotel A (City A)" in content
    assert "⚠️ Stornierungsfrist: Hotel A" in content
    assert "END:VCALENDAR" in content


def test_export_bookings_to_ics_invalid_date(tmp_path, caplog):
    output_file = tmp_path / "test_invalid.ics"
    bookings = [{"hotel_name": "Bad Date Hotel", "arrival_date": "invalid-date", "departure_date": "2026-05-16"}]

    export_bookings_to_ics(bookings, output_file)
    assert "Ungültiges Datum" in caplog.text


def test_export_bookings_to_ics_invalid_cancel_date(tmp_path, caplog):
    output_file = tmp_path / "test_invalid_cancel.ics"
    bookings = [
        {
            "hotel_name": "Bad Cancel Hotel",
            "arrival_date": "2026-05-15",
            "departure_date": "2026-05-16",
            "free_cancel_until": "invalid-date",
        }
    ]

    export_bookings_to_ics(bookings, output_file)
    assert "Ungültiges Stornierungsdatum" in caplog.text
