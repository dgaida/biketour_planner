"""Unit-Tests für brouter.py.

Testet die BRouter API Integration inklusive:
- Routing zwischen zwei Koordinaten (route_to_address)
- Extraktion von GPX-Trackpunkten (get_route2address_as_points)
- Error-Handling bei Server-Fehlern
- Validierung der GPX-Ausgabe
"""

import json
from unittest.mock import Mock, patch

import gpxpy
import pytest
import requests

from biketour_planner.brouter import (
    check_brouter_availability,
    get_route2address_as_points,
    get_route2address_with_stats,
    parse_brouter_geojson,
    route_to_address,
)
from biketour_planner.exceptions import RoutingError


class TestCheckBRouterAvailability:
    """Tests für die check_brouter_availability Funktion."""

    @patch("biketour_planner.brouter.requests.get")
    def test_check_availability_success(self, mock_get):
        """Testet Verfügbarkeit bei Status 200."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert check_brouter_availability() is True
        mock_get.assert_called_once()
        assert "timeout" in mock_get.call_args[1]
        assert mock_get.call_args[1]["timeout"] == 5

    @patch("biketour_planner.brouter.requests.get")
    def test_check_availability_400(self, mock_get):
        """Testet Verfügbarkeit bei Status 400 (Bad Request)."""
        # BRouter liefert oft 400 zurück, wenn keine Parameter übergeben werden
        mock_response = Mock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        assert check_brouter_availability() is True

    @patch("biketour_planner.brouter.requests.get")
    def test_check_availability_500(self, mock_get):
        """Testet Nicht-Verfügbarkeit bei Server-Fehler (500)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        assert check_brouter_availability() is False

    @patch("biketour_planner.brouter.requests.get")
    def test_check_availability_connection_error(self, mock_get):
        """Testet Nicht-Verfügbarkeit bei Verbindungsfehler."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        assert check_brouter_availability() is False


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

        with pytest.raises(RoutingError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_http_error_400(self, mock_get, mock_check):
        """Testet Verhalten bei HTTP 400 (fehlende Routing-Daten)."""
        # Mock BRouter als verfügbar
        mock_check.value = True

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request - No data available")
        mock_get.return_value = mock_response

        with pytest.raises(RoutingError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_connection_error(self, mock_get, mock_check):
        """Testet Verhalten bei Verbindungsfehler."""
        # Mock BRouter als verfügbar (aber dann schlägt die Verbindung fehl)
        mock_check.return_value = True

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused - BRouter Server nicht erreichbar")

        with pytest.raises(RoutingError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_route_to_address_timeout(self, mock_get, mock_check):
        """Testet Verhalten bei Timeout."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        mock_get.side_effect = requests.exceptions.Timeout("Request timeout - Routenberechnung dauert zu lange")

        with pytest.raises(RoutingError):
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
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[13.4050, 52.5200, 35], [13.4000, 52.5100, 40], [13.0645, 52.3906, 50]]}
            }]
        }
        mock_route.return_value = json.dumps(geojson_data)

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

        with pytest.raises(RoutingError, match="Empty response"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_whitespace_only(self, mock_route):
        """Testet Verhalten bei Whitespace-only Response."""
        mock_route.return_value = "   \n\t  "

        # BRouter or parser might handle this differently now, but let's assume it fails
        with pytest.raises(RoutingError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_no_features(self, mock_route):
        """Testet Verhalten wenn GeoJSON keine Features enthält."""
        geojson_data = {"features": []}
        mock_route.return_value = json.dumps(geojson_data)

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)
        assert len(points) == 0

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_single_point(self, mock_route):
        """Testet Route mit nur einem Punkt."""
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[13.4050, 52.5200, 35]]}
            }]
        }
        mock_route.return_value = json.dumps(geojson_data)

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 1
        assert points[0].latitude == 52.5200

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_without_elevation(self, mock_route):
        """Testet Punkte ohne Höheninformation."""
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[13.4050, 52.5200], [13.0645, 52.3906]]}
            }]
        }
        mock_route.return_value = json.dumps(geojson_data)

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 2
        assert points[0].elevation is None
        assert points[1].elevation is None

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_http_errors(self, mock_route):
        """Testet dass HTTP-Fehler weitergegeben werden."""
        mock_route.side_effect = RoutingError("404 Not Found")

        with pytest.raises(RoutingError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_connection_errors(self, mock_route):
        """Testet dass Verbindungsfehler weitergegeben werden."""
        mock_route.side_effect = RoutingError("BRouter nicht erreichbar")

        with pytest.raises(RoutingError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_propagates_timeout(self, mock_route):
        """Testet dass Timeouts weitergegeben werden."""
        mock_route.side_effect = RoutingError("Timeout")

        with pytest.raises(RoutingError):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_invalid_geojson(self, mock_route):
        """Testet Verhalten bei ungültigem GeoJSON."""
        mock_route.return_value = "invalid json"

        with pytest.raises(RoutingError, match="Failed to parse GeoJSON"):
            get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_large_route(self, mock_route):
        """Testet Verhalten bei sehr großer Route (viele Punkte)."""
        coords = [[13.4050 - i * 0.001, 52.5200 - i * 0.001, 35 + i] for i in range(1000)]
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": coords}
            }]
        }
        mock_route.return_value = json.dumps(geojson_data)

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert len(points) == 1000
        assert points[0].latitude == 52.5200
        assert points[-1].latitude == pytest.approx(52.5200 - 999 * 0.001, abs=0.0001)

    @patch("biketour_planner.brouter.route_to_address")
    def test_get_points_returns_gpxtrackpoint_objects(self, mock_route):
        """Testet dass GPXTrackPoint-Objekte zurückgegeben werden."""
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[13.4050, 52.5200, 35]]}
            }]
        }
        mock_route.return_value = json.dumps(geojson_data)

        points = get_route2address_as_points(52.5200, 13.4050, 52.3906, 13.0645)

        assert isinstance(points[0], gpxpy.gpx.GPXTrackPoint)
        assert hasattr(points[0], "latitude")
        assert hasattr(points[0], "longitude")
        assert hasattr(points[0], "elevation")
        assert hasattr(points[0], "time")


class TestBRouterGeoJSON:
    """Tests für GeoJSON-spezifische BRouter-Funktionen."""

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_get_route2address_with_stats_success(self, mock_get, mock_check):
        """Testet erfolgreiche GeoJSON-Routenanforderung."""
        mock_check.return_value = True
        mock_response = Mock()
        mock_response.status_code = 200
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[11.58, 48.13, 500], [11.59, 48.14, 510]]},
                "properties": {
                    "messages": [
                        ["Longitude", "Latitude", "Distance", "surface"],
                        ["11580000", "48130000", "0", "asphalt"],
                        ["11590000", "48140000", "1000", "gravel"]
                    ]
                }
            }]
        }
        mock_response.text = json.dumps(geojson_data)
        mock_get.return_value = mock_response

        points, stats = get_route2address_with_stats(48.13, 11.58, 48.14, 11.59)
        assert len(points) == 2
        assert stats["paved"] == 0.0 # because it starts with 0 distance for asphalt
        # Wait, the way BRouter works: the distance in row N is the distance REACHED after segment N-1.
        # Header is messages[0].
        # Row 1: asphalt, distance 0. (Start point)
        # Row 2: gravel, distance 1000. (Segment 1 to point 2 is gravel, distance 1000)
        # So paved (asphalt) = 0, unpaved (gravel) = 1000. Correct.
        assert stats["unpaved"] == 1000.0

    def test_parse_brouter_geojson_mixed(self):
        """Testet Parsing von gemischten Oberflächen im GeoJSON."""
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[0,0], [1,1], [2,2]]},
                "properties": {
                    "messages": [
                        ["Distance", "surface"],
                        ["0", "asphalt"],
                        ["1000", "asphalt"],
                        ["1500", "gravel"]
                    ]
                }
            }]
        }
        _, stats = parse_brouter_geojson(json.dumps(geojson_data))
        assert stats["paved"] == 1000.0
        assert stats["unpaved"] == 500.0

    def test_parse_brouter_geojson_empty(self):
        """Testet Parsing von leerem Content."""
        points, stats = parse_brouter_geojson("")
        assert points == []
        assert stats["paved"] == 0.0


class TestBRouterIntegration:
    """Integrationstests für die BRouter-Module."""

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_full_workflow(self, mock_get, mock_check):
        """Testet kompletten Workflow: Route anfordern + Punkte extrahieren."""
        mock_check.return_value = True
        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[11.5820, 48.1351, 520], [11.3000, 48.0000, 600], [11.0953, 47.4917, 705]]}
            }]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(geojson_data)
        mock_get.return_value = mock_response

        # 1. Route anfordern (GPX)
        gpx_string = route_to_address(48.1351, 11.5820, 47.4917, 11.0953)
        assert gpx_string is not None
        assert json.loads(gpx_string) == geojson_data # In reality it would be GPX if format=gpx, but we mocked it

        # 2. Punkte extrahieren (nutzt intern route_to_address mit format=geojson)
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
        with pytest.raises(RoutingError):
            route_to_address(48.1351, 11.5820, 47.4917, 11.0953)

        # get_route2address_as_points sollte Exception propagieren
        with pytest.raises(RoutingError):
            get_route2address_as_points(48.1351, 11.5820, 47.4917, 11.0953)

    @patch("biketour_planner.brouter.check_brouter_availability")
    @patch("biketour_planner.brouter.requests.get")
    def test_workflow_coordinates_validation(self, mock_get, mock_check):
        """Testet dass Koordinaten korrekt durch beide Funktionen gehen."""
        # Mock BRouter als verfügbar
        mock_check.return_value = True

        geojson_data = {
            "features": [{
                "geometry": {"coordinates": [[13.4050, 52.5200]]}
            }]
        }

        mock_response = Mock()
        mock_response.text = json.dumps(geojson_data)
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

            # FIX: Verwende :.15g Formatierung wie in route_to_address
            expected_start = f"{lon1:.15g},{lat1:.15g}"
            expected_end = f"{lon2:.15g},{lat2:.15g}"

            # Prüfe dass Koordinaten im richtigen Format übergeben werden
            assert expected_start in lonlats
            assert expected_end in lonlats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
