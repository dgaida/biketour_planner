"""Unit-Tests für brouter.py.

Testet die BRouter API Integration inklusive:
- Routing zwischen zwei Koordinaten (route_to_address)
- Extraktion von GPX-Trackpunkten (get_route2address_as_points)
- Error-Handling bei Server-Fehlern
- Validierung der GPX-Ausgabe
"""

import pytest
from unittest.mock import patch, Mock
import requests
import gpxpy
from biketour_planner.brouter import (
    route_to_address,
    get_route2address_as_points,
)


class TestRouteToAddress:
    """Tests für die route_to_address Funktion."""

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_success(self, mock_get, mock_check):
        """Testet erfolgreiche Routenberechnung."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        # Mock GPX-Response
        gpx_response = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BRouter">
  <trk>
    <trkseg>
      <trkpt lat="48.1351" lon="11.5820">
        <ele>520</ele>
      </trkpt>
      <trkpt lat="48.1400" lon="11.5900">
        <ele>525</ele>
      </trkpt>
      <trkpt lat="47.4917" lon="11.0953">
        <ele>705</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = gpx_response
        mock_get.return_value = mock_response

        result = route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        assert result == gpx_response
        assert "<?xml version" in result
        assert "<gpx" in result
        assert "<trk>" in result

        # Prüfe API-Call Parameter
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://localhost:17777/brouter"
        assert call_args[1]["params"]["lonlats"] == "11.582,48.1351|11.0953,47.4917"
        assert call_args[1]["params"]["profile"] == "trekking"
        assert call_args[1]["params"]["format"] == "gpx"

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_coordinate_order(self, mock_get, mock_check):
        """Testet korrekte Koordinatenreihenfolge (lon,lat)."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx></gpx>"
        mock_get.return_value = mock_response

        route_to_address(52.5200, 13.4050, 52.3906, 13.0645)

        call_args = mock_get.call_args
        lonlats = call_args[1]["params"]["lonlats"]

        # Koordinatenreihenfolge: lon,lat|lon,lat
        assert lonlats == "13.405,52.52|13.0645,52.3906"

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_negative_coordinates(self, mock_get, mock_check):
        """Testet Routing mit negativen Koordinaten."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx></gpx>"
        mock_get.return_value = mock_response

        route_to_address(-33.8688, 151.2093, -34.0000, 151.0000)

        call_args = mock_get.call_args
        lonlats = call_args[1]["params"]["lonlats"]

        assert "151.2093,-33.8688" in lonlats
        assert "151,-34" in lonlats

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_http_error_404(self, mock_get, mock_check):
        """Testet Verhalten bei HTTP 404 (Server nicht erreichbar)."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_http_error_400(self, mock_get, mock_check):
        """Testet Verhalten bei HTTP 400 (fehlende Routing-Daten)."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request - No data available")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_connection_error(self, mock_get, mock_check):
        """Testet Verhalten bei Verbindungsfehler."""
        # Mock BRouter als verfügbar (aber dann schlägt die Verbindung fehl)
        mock_check.return_value = True

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused - BRouter Server nicht erreichbar")

        with pytest.raises(requests.exceptions.ConnectionError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_timeout(self, mock_get, mock_check):
        """Testet Verhalten bei Timeout."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_get.side_effect = requests.exceptions.Timeout("Request timeout - Routenberechnung dauert zu lange")

        with pytest.raises(requests.exceptions.Timeout):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_empty_response(self, mock_get, mock_check):
        """Testet Verhalten bei leerer Response."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_get.return_value = mock_response

        result = route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        assert result == ""

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_uses_trekking_profile(self, mock_get, mock_check):
        """Testet dass das 'trekking' Profil verwendet wird."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx></gpx>"
        mock_get.return_value = mock_response

        route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["profile"] == "trekking"

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_gpx_format(self, mock_get, mock_check):
        """Testet dass GPX-Format angefordert wird."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx></gpx>"
        mock_get.return_value = mock_response

        route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["format"] == "gpx"

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_same_start_end(self, mock_get, mock_check):
        """Testet Routing mit identischen Start- und Endkoordinaten."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx><trk><trkseg><trkpt lat='48.1351' lon='11.5820'/></trkseg></trk></gpx>"
        mock_get.return_value = mock_response

        result = route_to_address(48.1351, 11.5820, 48.1351, 11.5820)

        assert "<gpx>" in result

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_high_precision_coordinates(self, mock_get, mock_check):
        """Testet Routing mit hochpräzisen Koordinaten."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_response = Mock()
        mock_response.text = "<gpx></gpx>"
        mock_get.return_value = mock_response

        route_to_address(48.135123456, 11.582045678, 47.491789012, 11.095334567)

        call_args = mock_get.call_args
        lonlats = call_args[1]["params"]["lonlats"]

        # Prüfe dass volle Präzision übergeben wird
        assert "11.582045678,48.135123456" in lonlats


class TestGetRoute2AddressAsPoints:
    """Tests für die get_route2address_as_points Funktion."""

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_success(self, mock_route):
        """Testet erfolgreiche Punkt-Extraktion."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050">
        <ele>35</ele>
      </trkpt>
      <trkpt lat="52.5100" lon="13.4000">
        <ele>40</ele>
      </trkpt>
      <trkpt lat="52.3906" lon="13.0645">
        <ele>50</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 3
        assert points[0].latitude == 52.5200
        assert points[0].longitude == 13.4050
        assert points[0].elevation == 35
        assert points[-1].latitude == 52.3906
        assert points[-1].longitude == 13.0645

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_empty_response(self, mock_route):
        """Testet Verhalten bei leerer Response."""
        mock_route.return_value = ""

        with pytest.raises(ValueError, match="leere Antwort"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_whitespace_only(self, mock_route):
        """Testet Verhalten bei Whitespace-only Response."""
        mock_route.return_value = "   \n\t  "

        with pytest.raises(ValueError, match="leere Antwort"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_no_tracks(self, mock_route):
        """Testet Verhalten wenn GPX keine Tracks enthält."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
</gpx>"""
        mock_route.return_value = gpx_string

        with pytest.raises(ValueError, match="keine Tracks/Segmente"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_no_segments(self, mock_route):
        """Testet Verhalten wenn Track keine Segmente enthält."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        with pytest.raises(ValueError, match="keine Tracks/Segmente"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_no_points(self, mock_route):
        """Testet Verhalten wenn Segment keine Punkte enthält."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        with pytest.raises(ValueError, match="keine Punkte"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_single_point(self, mock_route):
        """Testet Route mit nur einem Punkt."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050">
        <ele>35</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 1
        assert points[0].latitude == 52.5200

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_without_elevation(self, mock_route):
        """Testet Punkte ohne Höheninformation."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050"/>
      <trkpt lat="52.3906" lon="13.0645"/>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 2
        assert points[0].elevation is None
        assert points[1].elevation is None

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_with_time(self, mock_route):
        """Testet Punkte mit Zeitstempel."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050">
        <ele>35</ele>
        <time>2026-05-15T10:00:00Z</time>
      </trkpt>
      <trkpt lat="52.3906" lon="13.0645">
        <ele>50</ele>
        <time>2026-05-15T12:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 2
        assert points[0].time is not None
        assert points[1].time is not None

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_multiple_segments(self, mock_route):
        """Testet dass nur das erste Segment verwendet wird."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050"/>
      <trkpt lat="52.5100" lon="13.4000"/>
    </trkseg>
    <trkseg>
      <trkpt lat="52.4000" lon="13.3000"/>
      <trkpt lat="52.3906" lon="13.0645"/>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        # Nur Punkte aus dem ersten Segment
        assert len(points) == 2
        assert points[0].latitude == 52.5200
        assert points[1].latitude == 52.5100

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_http_errors(self, mock_route):
        """Testet dass HTTP-Fehler weitergegeben werden."""
        mock_route.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_connection_errors(self, mock_route):
        """Testet dass Verbindungsfehler weitergegeben werden."""
        mock_route.side_effect = requests.exceptions.ConnectionError("BRouter nicht erreichbar")

        with pytest.raises(requests.exceptions.ConnectionError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_timeout(self, mock_route):
        """Testet dass Timeouts weitergegeben werden."""
        mock_route.side_effect = requests.exceptions.Timeout("Timeout")

        with pytest.raises(requests.exceptions.Timeout):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_invalid_xml(self, mock_route):
        """Testet Verhalten bei ungültigem XML."""
        mock_route.return_value = "ungültiges XML <gpx"

        with pytest.raises(Exception):  # gpxpy wirft verschiedene Exceptions
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_large_route(self, mock_route):
        """Testet Verhalten bei sehr großer Route (viele Punkte)."""
        # Erstelle GPX mit 1000 Punkten
        points_xml = "\n".join(
            [f'<trkpt lat="{52.5200 - i*0.001}" lon="{13.4050 - i*0.001}"><ele>{35+i}</ele></trkpt>' for i in range(1000)]
        )

        gpx_string = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      {points_xml}
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 1000
        assert points[0].latitude == 52.5200
        assert points[-1].latitude == pytest.approx(52.5200 - 999 * 0.001, abs=0.0001)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_returns_gpxtrackpoint_objects(self, mock_route):
        """Testet dass GPXTrackPoint-Objekte zurückgegeben werden."""
        gpx_string = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050">
        <ele>35</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        mock_route.return_value = gpx_string

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert isinstance(points[0], gpxpy.gpx.GPXTrackPoint)
        assert hasattr(points[0], "latitude")
        assert hasattr(points[0], "longitude")
        assert hasattr(points[0], "elevation")
        assert hasattr(points[0], "time")


class TestBRouterIntegration:
    """Integrationstests für die BRouter-Module."""

    @patch("biketour_planner.brouter.requests.get")
    def test_full_workflow(self, mock_get):
        """Testet kompletten Workflow: Route anfordern + Punkte extrahieren."""
        gpx_response = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.1351" lon="11.5820"><ele>520</ele></trkpt>
      <trkpt lat="48.0000" lon="11.3000"><ele>600</ele></trkpt>
      <trkpt lat="47.4917" lon="11.0953"><ele>705</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = gpx_response
        mock_get.return_value = mock_response

        # 1. Route anfordern
        gpx_string = route_to_address(48.1351, 11.5820, 47.4917, 11.0953)
        assert gpx_string is not None
        assert "<gpx" in gpx_string

        # 2. Punkte extrahieren (nutzt intern route_to_address nochmal)
        points = get_route2address_as_points(48.1351, 11.5820, 47.4917, 11.0953)
        assert len(points) == 3
        assert points[0].latitude == 48.1351
        assert points[-1].latitude == 47.4917

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_workflow_server_down(self, mock_get, mock_check):
        """Testet Workflow wenn BRouter-Server nicht erreichbar ist."""
        # Mock BRouter als verfügbar (damit check_brouter_availability() nicht abbricht)
        mock_check.return_value = True

        # Dann schlägt der requests.get() Aufruf fehl
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # route_to_address sollte Exception werfen
        with pytest.raises(requests.exceptions.ConnectionError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        # get_route2address_as_points sollte Exception propagieren
        with pytest.raises(requests.exceptions.ConnectionError):
            get_route2address_as_points(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_workflow_coordinates_validation(self, mock_get, mock_check):
        """Testet dass Koordinaten korrekt durch beide Funktionen gehen."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        gpx_response = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050"/>
    </trkseg>
  </trk>
</gpx>"""

        mock_response = Mock()
        mock_response.text = gpx_response
        mock_get.return_value = mock_response

        # Teste verschiedene Koordinatenformate
        test_cases = [
            (48.1351, 11.5820, 47.4917, 11.0953),  # München -> Garmisch
            (52.5200, 13.4050, 52.3906, 13.0645),  # Berlin -> Potsdam
            (-33.8688, 151.2093, -34.0000, 151.0000),  # Negative Koordinaten
            (0.0, 0.0, 0.0, 0.0),  # Null-Insel
        ]

        for lat1, lon1, lat2, lon2 in test_cases:
            get_route2address_as_points(lat1, lon1, lat2, lon2)

            call_args = mock_get.call_args
            lonlats = call_args[1]["params"]["lonlats"]

            # Prüfe dass Koordinaten im richtigen Format übergeben werden
            assert f"{lon1},{lat1}" in lonlats
            assert f"{lon2},{lat2}" in lonlats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
