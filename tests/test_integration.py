"""Integration Tests für den kompletten Workflow.

Testet das Zusammenspiel aller Komponenten von Booking-Parsing bis PDF-Export.
"""

import json
from unittest.mock import patch

import pytest


class TestEndToEndWorkflow:
    """End-to-End Tests für den kompletten Planungs-Workflow."""

    @pytest.fixture
    def test_data_dir(self, tmp_path):
        """Erstellt temporäre Test-Daten-Struktur."""
        booking_dir = tmp_path / "booking"
        gpx_dir = tmp_path / "gpx"
        output_dir = tmp_path / "output"

        booking_dir.mkdir()
        gpx_dir.mkdir()
        output_dir.mkdir()

        # Erstelle minimales Booking HTML
        booking_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script>
                window.utag_data = {
                    hotel_name: 'Test Hotel',
                    city_name: 'Test City',
                    date_in: '2026-05-15',
                    date_out: '2026-05-16'
                };
            </script>
        </head>
        <body>
            <div class="hotel-details__address">
                <h2>Test Hotel</h2>
                <strong>GPS-Koordinaten:</strong> N 048° 08.106, E 011° 34.920
            </div>
        </body>
        </html>
        """
        (booking_dir / "test_booking.html").write_text(booking_html, encoding="utf-8")

        # Erstelle minimale GPX-Datei
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.1" lon="11.5"><ele>520</ele></trkpt>
      <trkpt lat="48.135, lon="11.582"><ele>540</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
        (gpx_dir / "test_route.gpx").write_text(gpx_content, encoding="utf-8")

        return {"booking_dir": booking_dir, "gpx_dir": gpx_dir, "output_dir": output_dir}

    @patch("biketour_planner.geoapify.find_top_tourist_sights")
    @patch("biketour_planner.brouter.check_brouter_availability")
    def test_complete_workflow_without_brouter(self, mock_brouter_check, mock_geoapify, test_data_dir):
        """Testet kompletten Workflow ohne BRouter (nur GPX-Merging)."""
        from biketour_planner.gpx_route_manager import GPXRouteManager
        from biketour_planner.parse_booking import extract_booking_info

        # Mock BRouter als verfügbar
        mock_brouter_check.return_value = False  # Kein BRouter für Test

        # Mock Geoapify
        mock_geoapify.return_value = {"features": []}

        # 1. Parse Booking
        booking_file = list(test_data_dir["booking_dir"].glob("*.html"))[0]
        booking = extract_booking_info(booking_file)

        assert booking["hotel_name"] == "Test Hotel"
        assert booking["arrival_date"] == "2026-05-15"

        # 2. GPX Processing (ohne BRouter - nur Merging)
        manager = GPXRouteManager(test_data_dir["gpx_dir"], test_data_dir["output_dir"])

        assert len(manager.gpx_index) == 1
        assert "test_route.gpx" in manager.gpx_index

        # 3. Merge GPX
        route_files = [{"file": "test_route.gpx", "start_index": 0, "end_index": 2, "reversed": False}]

        merged = manager.merge_gpx_files(route_files, test_data_dir["output_dir"], booking)

        assert merged is not None
        assert merged.exists()
        assert "merged.gpx" in merged.name

    def test_workflow_validates_input_directories(self, tmp_path):
        """Testet dass fehlende Verzeichnisse erkannt werden."""
        from biketour_planner.gpx_route_manager import GPXRouteManager

        non_existent = tmp_path / "does_not_exist"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Sollte nicht crashen, aber leeren Index haben
        manager = GPXRouteManager(non_existent, output_dir)
        assert len(manager.gpx_index) == 0

    @patch("biketour_planner.geoapify.geoapify_api_key", None)
    def test_workflow_gracefully_handles_missing_api_key(self, test_data_dir):
        """Testet dass fehlender Geoapify-Key nicht zum Crash führt."""
        from biketour_planner.geoapify import find_top_tourist_sights

        result = find_top_tourist_sights(48.0, 11.0)

        # Sollte leeres Result zurückgeben, nicht None
        assert result == {"features": []}


class TestDataPersistence:
    """Tests für Daten-Speicherung und -Laden."""

    def test_bookings_json_round_trip(self, tmp_path):
        """Testet dass bookings.json korrekt gespeichert und geladen wird."""
        from biketour_planner.pass_finder import load_json

        # Erstelle Test-Daten
        test_bookings = [
            {
                "hotel_name": "Test Hotel",
                "arrival_date": "2026-05-15",
                "latitude": 48.135,
                "longitude": 11.582,
                "gpx_files": [{"file": "test.gpx", "start_index": 0, "end_index": 10}],
            }
        ]

        # Speichere
        json_path = tmp_path / "test_bookings.json"
        json_path.write_text(json.dumps(test_bookings, indent=2, ensure_ascii=False), encoding="utf-8")

        # Lade wieder
        loaded = load_json(json_path)

        assert loaded == test_bookings
        assert loaded[0]["hotel_name"] == "Test Hotel"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
