"""Unit-Tests für parse_booking.py.

Testet das Parsing von Booking.com HTML-Bestätigungen inklusive:
- Datumskonvertierung
- GPS-Koordinaten-Parsing
- Extraktion von Buchungsinformationen aus verschiedenen HTML-Formaten
"""

import pytest

from biketour_planner.parse_booking import (
    MONTHS_DE,
    extract_booking_info,
    parse_date,
    parse_gps_coordinates,
)


class TestParseDate:
    """Tests für die parse_date Funktion."""

    def test_parse_date_standard_format(self):
        """Testet Parsing eines Standard-Datums."""
        result = parse_date("So., 8. März 2026")
        assert result == "2026-03-08"

    def test_parse_date_single_digit_day(self):
        """Testet Parsing mit einstelligem Tag."""
        result = parse_date("Mo., 1. Januar 2026")
        assert result == "2026-01-01"

    def test_parse_date_double_digit_day(self):
        """Testet Parsing mit zweistelligem Tag."""
        result = parse_date("Fr., 15. Dezember 2025")
        assert result == "2025-12-15"

    def test_parse_date_all_months(self):
        """Testet Parsing für alle Monate."""
        for month_name, month_num in MONTHS_DE.items():
            result = parse_date(f"Mo., 1. {month_name} 2026")
            assert result == f"2026-{month_num}-01"

    def test_parse_date_invalid_format(self):
        """Testet Verhalten bei ungültigem Format."""
        result = parse_date("ungültiges Datum")
        assert result is None

    def test_parse_date_empty_string(self):
        """Testet Verhalten bei leerem String."""
        result = parse_date("")
        assert result is None

    def test_parse_date_without_weekday(self):
        """Testet Parsing ohne Wochentag."""
        result = parse_date("8. März 2026")
        assert result == "2026-03-08"


class TestParseGPSCoordinates:
    """Tests für die parse_gps_coordinates Funktion."""

    def test_parse_gps_standard_format(self):
        """Testet Standard GPS-Format mit N/E."""
        lat, lon = parse_gps_coordinates("N 043° 56.181, E 15° 26.645")
        assert lat == pytest.approx(43.936, abs=0.01)
        assert lon == pytest.approx(15.444, abs=0.01)

    def test_parse_gps_with_html_entity(self):
        """Testet GPS-Format mit &deg; HTML-Entity."""
        lat, lon = parse_gps_coordinates("N 043&deg; 56.181, E 15&deg; 26.645")
        assert lat == pytest.approx(43.936, abs=0.01)
        assert lon == pytest.approx(15.444, abs=0.01)

    def test_parse_gps_south_west(self):
        """Testet GPS-Koordinaten in südlicher/westlicher Hemisphäre."""
        lat, lon = parse_gps_coordinates("S 033° 52.000, W 151° 12.500")
        assert lat == pytest.approx(-33.867, abs=0.01)
        assert lon == pytest.approx(-151.208, abs=0.01)

    def test_parse_gps_exact_degrees(self):
        """Testet GPS-Koordinaten ohne Minuten-Dezimalstellen."""
        lat, lon = parse_gps_coordinates("N 045° 30, E 012° 15")
        assert lat == pytest.approx(45.5, abs=0.01)
        assert lon == pytest.approx(12.25, abs=0.01)

    def test_parse_gps_zero_minutes(self):
        """Testet GPS-Koordinaten mit null Minuten."""
        lat, lon = parse_gps_coordinates("N 050° 0.0, E 010° 0.0")
        assert lat == pytest.approx(50.0, abs=0.01)
        assert lon == pytest.approx(10.0, abs=0.01)

    def test_parse_gps_invalid_format(self):
        """Testet Verhalten bei ungültigem Format."""
        lat, lon = parse_gps_coordinates("ungültige Koordinaten")
        assert lat is None
        assert lon is None

    def test_parse_gps_empty_string(self):
        """Testet Verhalten bei leerem String."""
        lat, lon = parse_gps_coordinates("")
        assert lat is None
        assert lon is None

    def test_parse_gps_none_input(self):
        """Testet Verhalten bei None-Input."""
        lat, lon = parse_gps_coordinates(None)
        assert lat is None
        assert lon is None

    def test_parse_gps_missing_longitude(self):
        """Testet Verhalten wenn Längengrad fehlt."""
        lat, lon = parse_gps_coordinates("N 043° 56.181")
        assert lat is None
        assert lon is None

    def test_parse_gps_spaces_variations(self):
        """Testet verschiedene Whitespace-Variationen."""
        lat, lon = parse_gps_coordinates("N043°56.181,E15°26.645")
        assert lat == pytest.approx(43.936, abs=0.01)
        assert lon == pytest.approx(15.444, abs=0.01)


class TestExtractBookingInfo:
    """Tests für die extract_booking_info Funktion."""

    def test_extract_airbnb_booking(self, tmp_path):
        """Testet Extraktion von Airbnb-Buchungen."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <script>
            var data = {"metadata":{"title":"Cozy Airbnb","check_in_date":"2026-06-01","check_out_date":"2026-06-05"},"lat":44.123,"lng":15.456};
        </script>
        <script>
            {"id":"header_action.direction", "subtitle": "Beach Road 1, Zadar"}
        </script>
        <script>
            {"id":"payment_summary", "content": "Gesamtkosten: 450,00 €"}
        </script>
        <script>
            {"id":"checkin_checkout_arrival_guide", "leading_kicker": "Check-in", "leading_subtitle": "15:00 - 22:00"}
        </script>
        <div class="rz78adb">
            <p class="_yz1jt7x">Beach Road 1, Zadar, Croatia</p>
        </div>
        </html>
        """
        # Note: Airbnb parser looks for script with re.compile(r'"metadata".*"title".*"check_in_date"')
        # My dummy content has it.

        html_file = tmp_path / "airbnb.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["hotel_name"] == "Cozy Airbnb"
        assert result["arrival_date"] == "2026-06-01"
        assert result["departure_date"] == "2026-06-05"
        assert result["latitude"] == 44.123
        assert result["longitude"] == 15.456
        assert result["city_name"] == "Zadar"
        assert result["total_price"] == 450.0

    def test_extract_booking_info_complete_new_format(self, tmp_path):
        """Testet Extraktion mit vollständigem neuen HTML-Format."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script>
                window.utag_data = {
                    hotel_name: 'Test Hotel',
                    city_name: 'Split',
                    country_name: 'Kroatien',
                    date_in: '2026-05-15',
                    date_out: '2026-05-16'
                };
            </script>
        </head>
        <body>
            <div class="hotel-details__address">
                <h2>Test Hotel</h2>
                <strong>Adresse:</strong> Teststraße 1, 21000 Split, Kroatien
                <strong>Telefon:</strong> <span class="u-phone">+385 21 123456</span>
                <strong>GPS-Koordinaten:</strong> N 043° 30.500, E 016° 26.400
            </div>
            <div class="row dates">
                <div class="col-6 dates__item">
                    <div class="summary__big-num">15</div>
                    <div class="dates__month">Mai</div>
                    <div class="dates__time">14:00 - 20:00</div>
                </div>
                <div class="col-6 dates__item">
                    <div class="summary__big-num">16</div>
                    <div class="dates__month">Mai</div>
                </div>
            </div>
            <h5>Ausstattung</h5>
            <th><td>Küche, Waschmaschine, WLAN</td></th>
            <div data-total-price="150.50"></div>
            <p>Kostenlose Stornierung bis 10. Mai 2026</p>
        </body>
        </html>
        """

        html_file = tmp_path / "test_booking.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["hotel_name"] == "Test Hotel"
        assert result["city_name"] == "Split"
        assert result["country_name"] == "Kroatien"
        assert result["arrival_date"] == "2026-05-15"
        assert result["departure_date"] == "2026-05-16"
        assert result["checkin_time"] == "14:00"
        assert "Split" in result["address"]
        assert result["phone"] == "+385 21 123456"
        assert result["latitude"] == pytest.approx(43.508, abs=0.01)
        assert result["longitude"] == pytest.approx(16.440, abs=0.01)
        assert result["has_kitchen"] is True
        assert result["has_washing_machine"] is True
        assert result["total_price"] == 150.50
        assert result["free_cancel_until"] == "2026-05-10"

    def test_extract_booking_info_old_format(self, tmp_path):
        """Testet Extraktion mit altem HTML-Format (Fallback)."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h3>Anreise</h3>
            <div>So., 8. März 2026</div>
            <div>14:00 - 18:00</div>

            <h3>Abreise</h3>
            <div>Mo., 9. März 2026</div>

            <div>Adresse</div>
            <div>Alte Straße 5, 80331 München, Deutschland</div>

            <div class="gta-modal-preview__hotel-name">
                <div class="bui-text">Altes Hotel</div>
            </div>
        </body>
        </html>
        """

        html_file = tmp_path / "test_old_booking.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["hotel_name"] == "Altes Hotel"
        assert result["arrival_date"] == "2026-03-08"
        assert result["departure_date"] == "2026-03-09"
        assert result["checkin_time"] == "14:00"
        assert "München" in result["address"]

    def test_extract_booking_info_minimal_data(self, tmp_path):
        """Testet Extraktion mit minimalen Daten."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h2>Minimal Hotel</h2>
        </body>
        </html>
        """

        html_file = tmp_path / "test_minimal.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        # Alle Felder sollten vorhanden sein, aber leer/None/False
        assert "hotel_name" in result
        assert "arrival_date" in result
        assert "has_kitchen" in result
        assert result["has_kitchen"] is False
        assert result["has_washing_machine"] is False

    def test_extract_booking_info_missing_amenities(self, tmp_path):
        """Testet Extraktion ohne Ausstattungs-Informationen."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="hotel-details__address">
                <h2>Hotel Ohne Küche</h2>
            </div>
        </body>
        </html>
        """

        html_file = tmp_path / "test_no_amenities.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["has_kitchen"] is False
        assert result["has_washing_machine"] is False

    def test_extract_booking_info_partial_amenities(self, tmp_path):
        """Testet Extraktion mit nur einer Ausstattung."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h5>Ausstattung</h5>
            <th><td>Nur Küche verfügbar</td></th>
        </body>
        </html>
        """

        html_file = tmp_path / "test_partial.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["has_kitchen"] is True
        assert result["has_washing_machine"] is False

    def test_extract_booking_info_invalid_price(self, tmp_path):
        """Testet Extraktion mit ungültigem Preis."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <div data-total-price="ungültig"></div>
        </body>
        </html>
        """

        html_file = tmp_path / "test_invalid_price.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["total_price"] is None

    def test_extract_booking_info_utf8_encoding(self, tmp_path):
        """Testet korrekte UTF-8 Behandlung."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="hotel-details__address">
                <h2>Hotel Müller-Thürgau</h2>
                <strong>Adresse:</strong> Äußere Straße 5, München
            </div>
        </body>
        </html>
        """

        html_file = tmp_path / "test_utf8.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert "Müller" in result["hotel_name"]
        assert "Äußere" in result["address"]

    def test_extract_booking_info_no_cancellation(self, tmp_path):
        """Testet Extraktion ohne Stornierungsinformation."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h2>Test Hotel</h2>
        </body>
        </html>
        """

        html_file = tmp_path / "test_no_cancel.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["free_cancel_until"] is None

    def test_extract_booking_info_missing_gps(self, tmp_path):
        """Testet Extraktion ohne GPS-Koordinaten."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="hotel-details__address">
                <h2>Hotel ohne GPS</h2>
                <strong>Adresse:</strong> Irgendwo 1, Stadt
            </div>
        </body>
        </html>
        """

        html_file = tmp_path / "test_no_gps.html"
        html_file.write_text(html_content, encoding="utf-8")

        result = extract_booking_info(html_file)

        assert result["latitude"] is None
        assert result["longitude"] is None

    def test_create_all_bookings(self, tmp_path):
        """Testet create_all_bookings Funktion."""
        html_content = """
        <html>
        <div class="hotel-details__address">
            <h2>Test Hotel</h2>
            <strong>GPS-Koordinaten:</strong> N 45° 0.0, E 15° 0.0
        </div>
        </html>
        """
        (tmp_path / "booking1.html").write_text(html_content)

        from unittest.mock import patch

        from biketour_planner.parse_booking import create_all_bookings

        with patch("biketour_planner.parse_booking.find_top_tourist_sights") as mock_sights:
            mock_sights.return_value = ["Sight 1"]
            bookings = create_all_bookings(tmp_path, 5000, 2)

            assert len(bookings) == 1
            assert bookings[0]["hotel_name"] == "Test Hotel"
            assert bookings[0]["tourist_sights"] == ["Sight 1"]

    def test_extract_booking_info_more_fallbacks(self, tmp_path):
        """Testet weitere Fallbacks in extract_booking_info."""
        html_content = """
        <html>
        <h5>Ausstattung</h5>
        <tr><td>Küche</td></tr>
        <h5>Mahlzeiten</h5>
        <tr><td>Frühstück</td></tr>
        <div class="gta-modal-preview__hotel-name">
            <div class="bui-text">Fallback Hotel Name</div>
        </div>
        </html>
        """
        html_file = tmp_path / "fallback.html"
        html_file.write_text(html_content, encoding="utf-8")
        result = extract_booking_info(html_file)
        assert result["hotel_name"] == "Fallback Hotel Name"
        assert result["has_kitchen"] is True
        assert result["has_breakfast"] is True

    def test_extract_booking_info_towels(self, tmp_path):
        """Testet Extraktion von Handtüchern."""
        html_content = """
        <html>
        <body>
            <h5>Ausstattung</h5>
            <th><td>Handtücher, Küche</td></th>
        </body>
        </html>
        """
        html_file = tmp_path / "towels.html"
        html_file.write_text(html_content, encoding="utf-8")
        result = extract_booking_info(html_file)
        assert result["has_towels"] is True

    def test_extract_booking_info_toiletries(self, tmp_path):
        """Testet Extraktion von kostenlosen Pflegeprodukten."""
        html_content = """
        <html>
        <body>
            <h5>Ausstattung</h5>
            <th><td>Kostenlose Pflegeprodukte, Küche</td></th>
        </body>
        </html>
        """
        html_file = tmp_path / "toiletries.html"
        html_file.write_text(html_content, encoding="utf-8")
        result = extract_booking_info(html_file)
        assert result["has_toiletries"] is True
        assert result["has_kitchen"] is True

    def test_extract_airbnb_booking_toiletries(self, tmp_path):
        """Testet Extraktion von Pflegeprodukten aus Airbnb."""
        html_content = """
        <html>
        <script>
            var data = {"metadata":{"title":"Airbnb Toiletries","check_in_date":"2026-06-01","check_out_date":"2026-06-05"},"lat":44.123,"lng":15.456};
        </script>
        <body>Kostenlose Pflegeprodukte, Küche</body>
        </html>
        """
        html_file = tmp_path / "airbnb_toiletries.html"
        html_file.write_text(html_content, encoding="utf-8")
        result = extract_booking_info(html_file)
        assert result["has_toiletries"] is True
        assert result["has_kitchen"] is True

    def test_extract_airbnb_booking_towels(self, tmp_path):
        """Testet Extraktion von Handtüchern/Grundausstattung aus Airbnb."""
        html_content = """
        <html>
        <script>
            var data = {"metadata":{"title":"Airbnb Towels","check_in_date":"2026-06-01","check_out_date":"2026-06-05"},"lat":44.123,"lng":15.456};
        </script>
        <body>Grundausstattung</body>
        </html>
        """
        html_file = tmp_path / "airbnb_towels.html"
        html_file.write_text(html_content, encoding="utf-8")
        result = extract_booking_info(html_file)
        assert result["has_towels"] is True


class TestMonthsDE:
    """Tests für das MONTHS_DE Dictionary."""

    def test_months_de_completeness(self):
        """Testet ob alle 12 Monate vorhanden sind."""
        assert len(MONTHS_DE) == 12

    def test_months_de_valid_values(self):
        """Testet ob alle Werte gültige Monatsnummern sind."""
        for month_num in MONTHS_DE.values():
            assert month_num in [f"{i:02d}" for i in range(1, 13)]

    def test_months_de_unique_values(self):
        """Testet ob alle Monatsnummern eindeutig sind."""
        values = list(MONTHS_DE.values())
        assert len(values) == len(set(values))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
