import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def booking_html():
    return """
    <html>
    <head>
        <script>
            window.utag_data = {
                hotel_name: 'Test Hotel E2E',
                city_name: 'Split',
                date_in: '2026-05-15',
                date_out: '2026-05-16'
            };
        </script>
    </head>
    <body>
        <div class="hotel-details__address">
            <strong>GPS-Koordinaten:</strong> N 043° 30.488, E 016° 26.412
        </div>
    </body>
    </html>
    """


@pytest.fixture
def complete_tour_setup(tmp_path, booking_html):
    """Set up complete tour data for E2E testing."""
    # Create booking HTML
    booking_dir = tmp_path / "booking"
    booking_dir.mkdir()
    (booking_dir / "booking1.html").write_text(booking_html, encoding="utf-8")

    # Create GPX tracks
    gpx_dir = tmp_path / "gpx"
    gpx_dir.mkdir()

    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="43.5081" lon="16.4402"><ele>10</ele></trkpt>
      <trkpt lat="43.5100" lon="16.4420"><ele>15</ele></trkpt>
      <trkpt lat="43.5120" lon="16.4440"><ele>20</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
    (gpx_dir / "track1.gpx").write_text(gpx_content, encoding="utf-8")

    # Create pass database
    passes = [{"passname": "Test Pass", "latitude": 43.51, "longitude": 16.44}]
    (gpx_dir / "Paesse.json").write_text(json.dumps(passes))

    return {"booking_dir": booking_dir, "gpx_dir": gpx_dir, "output_dir": tmp_path / "output"}


@pytest.mark.integration
@patch("biketour_planner.brouter.requests.get")
@patch("biketour_planner.geoapify.requests.get")
def test_complete_planning_workflow(mock_geoapify, mock_brouter, complete_tour_setup, booking_html):
    """Test complete workflow: parse -> route -> merge."""
    from biketour_planner.gpx_route_manager import GPXRouteManager
    from biketour_planner.parse_booking import create_all_bookings

    # Mock external services
    mock_brouter.return_value = MagicMock(
        status_code=200,
        text="""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BRouter-1.6.3">
 <trk>
  <trkseg>
   <trkpt lat="43.5120" lon="16.4440"><ele>20</ele></trkpt>
   <trkpt lat="43.5081" lon="16.4402"><ele>10</ele></trkpt>
  </trkseg>
 </trk>
</gpx>""",
    )
    mock_geoapify.return_value = MagicMock(status_code=200, json=lambda: {"features": []})

    setup = complete_tour_setup

    # Add another booking so we have a route between them
    booking2_html = (
        booking_html.replace("2026-05-15", "2026-05-16")
        .replace("2026-05-16", "2026-05-17")
        .replace("Test Hotel E2E", "Hotel 2")
    )
    (setup["booking_dir"] / "booking2.html").write_text(booking2_html, encoding="utf-8")

    # 1. Parse bookings
    bookings = create_all_bookings(setup["booking_dir"], search_radius_m=5000, max_pois=2)
    assert len(bookings) == 2

    # 2. Process routes
    manager = GPXRouteManager(setup["gpx_dir"], setup["output_dir"])

    processed_bookings = manager.process_all_bookings(bookings, setup["output_dir"])

    assert len(processed_bookings) == 2
    assert "gpx_track_final" in processed_bookings[1]

    final_gpx = setup["output_dir"] / processed_bookings[1]["gpx_track_final"]
    assert final_gpx.exists()
