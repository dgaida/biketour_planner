"""Unit-Tests für geoapify.py.

Testet die Geoapify API Integration inklusive:
- POI-Suche (find_top_tourist_sights)
- Namen-Extraktion (get_names_as_comma_separated_string)
- Error-Handling bei Timeout und Request-Fehlern
- Umgang mit fehlenden/ungültigen API-Keys
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from biketour_planner.geoapify import (
    find_top_tourist_sights,
    get_names_as_comma_separated_string,
)


class TestFindTopTouristSights:
    """Tests für die find_top_tourist_sights Funktion."""

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key_12345")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_success(self, mock_get):
        """Testet erfolgreiche POI-Suche."""
        # Mock Response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {"properties": {"name": "Diokletianpalast", "lat": 43.5081, "lon": 16.4402}},
                {"properties": {"name": "Marjan Park", "lat": 43.515, "lon": 16.43}},
            ]
        }
        mock_get.return_value = mock_response

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is not None
        assert "features" in result
        assert len(result["features"]) == 2
        assert result["features"][0]["properties"]["name"] == "Diokletianpalast"

        # Prüfe API-Call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.geoapify.com/v2/places"
        assert call_args[1]["params"]["categories"] == "tourism.sights"
        assert call_args[1]["params"]["apiKey"] == "test_key_12345"

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_custom_radius(self, mock_get):
        """Testet POI-Suche mit benutzerdefiniertem Radius."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        find_top_tourist_sights(43.5081, 16.4402, radius=10000)

        call_args = mock_get.call_args
        assert "circle:16.4402,43.5081,10000" in call_args[1]["params"]["filter"]

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_custom_limit(self, mock_get):
        """Testet POI-Suche mit benutzerdefiniertem Limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        find_top_tourist_sights(43.5081, 16.4402, limit=5)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 5

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", None)
    def test_find_sights_missing_api_key(self):
        """Testet Verhalten bei fehlendem API-Key."""
        result = find_top_tourist_sights(43.5081, 16.4402)

        # Sollte leeres Dict zurückgeben, nicht None
        assert result == {"features": []}

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_timeout(self, mock_get):
        """Testet Timeout-Handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is None

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_http_error(self, mock_get):
        """Testet Handling von HTTP-Fehlern."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is None

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_connection_error(self, mock_get):
        """Testet Handling von Verbindungsfehlern."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is None

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_empty_response(self, mock_get):
        """Testet Verhalten bei leerer Response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is not None
        assert result["features"] == []

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_malformed_json(self, mock_get):
        """Testet Verhalten bei fehlerhaftem JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is None

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_unexpected_error(self, mock_get):
        """Testet Handling unerwarteter Fehler."""
        mock_get.side_effect = Exception("Unexpected error")

        result = find_top_tourist_sights(43.5081, 16.4402)

        assert result is None

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_coordinate_format(self, mock_get):
        """Testet korrekte Koordinaten-Formatierung im API-Call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        find_top_tourist_sights(43.508134, 16.440235, radius=5000)

        call_args = mock_get.call_args
        filter_param = call_args[1]["params"]["filter"]

        # Prüfe dass Koordinaten im richtigen Format sind (lon,lat,radius)
        # Coordinates are now rounded to 4 decimal places in find_top_tourist_sights
        assert "circle:16.4402,43.5081,5000" == filter_param

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_find_sights_negative_coordinates(self, mock_get):
        """Testet POI-Suche mit negativen Koordinaten."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        find_top_tourist_sights(-33.8688, 151.2093)  # Sydney

        call_args = mock_get.call_args
        filter_param = call_args[1]["params"]["filter"]
        assert "151.2093" in filter_param
        assert "-33.8688" in filter_param


class TestGetNamesAsCommaSeparatedString:
    """Tests für die get_names_as_comma_separated_string Funktion."""

    def test_get_names_standard_format(self):
        """Testet Extraktion von Standard-POI-Namen."""
        data = {
            "features": [
                {"properties": {"name": "Diokletianpalast"}},
                {"properties": {"name": "Marjan Park"}},
                {"properties": {"name": "Riva Promenade"}},
            ]
        }

        result = get_names_as_comma_separated_string(data)

        assert result == "Diokletianpalast, Marjan Park, Riva Promenade"

    def test_get_names_single_poi(self):
        """Testet Extraktion mit nur einem POI."""
        data = {"features": [{"properties": {"name": "Einzelner POI"}}]}

        result = get_names_as_comma_separated_string(data)

        assert result == "Einzelner POI"

    def test_get_names_empty_features(self):
        """Testet Verhalten bei leerer Features-Liste."""
        data = {"features": []}

        result = get_names_as_comma_separated_string(data)

        assert result == ""

    def test_get_names_none_input(self):
        """Testet Verhalten bei None-Input."""
        result = get_names_as_comma_separated_string(None)

        assert result == ""

    def test_get_names_fallback_to_street(self):
        """Testet Fallback zu Straßennamen wenn Name fehlt."""
        data = {
            "features": [
                {"properties": {"name": "POI mit Name"}},
                {"properties": {"street": "Hauptstraße"}},
                {"properties": {"name": "Weiterer POI"}},
            ]
        }

        result = get_names_as_comma_separated_string(data)

        assert "POI mit Name" in result
        assert "Hauptstraße" in result
        assert "Weiterer POI" in result

    def test_get_names_fallback_to_coordinates(self):
        """Testet Fallback zu Koordinaten wenn Name und Straße fehlen."""
        data = {"features": [{"properties": {"lat": 43.5081, "lon": 16.4402}}, {"properties": {"name": "Bekannter POI"}}]}

        result = get_names_as_comma_separated_string(data)

        assert "Bekannter POI" in result
        assert "(43.5081, 16.4402)" in result

    def test_get_names_missing_properties_key(self):
        """Testet Verhalten wenn properties-Key fehlt."""
        data = {"features": [{"other_key": "value"}]}

        # Sollte KeyError nicht werfen, sondern graceful handhaben
        try:
            get_names_as_comma_separated_string(data)
            # Falls kein Error, ist das Verhalten akzeptabel
            assert True
        except KeyError:
            pytest.fail("Sollte KeyError graceful handhaben")

    def test_get_names_mixed_valid_invalid(self):
        """Testet gemischte Liste aus validen und invaliden Einträgen."""
        data = {
            "features": [
                {"properties": {"name": "Gültiger POI"}},
                {},  # Ungültiger Eintrag
                {"properties": {"street": "Straße"}},
            ]
        }

        # Sollte nicht crashen und valide POIs extrahieren
        try:
            result = get_names_as_comma_separated_string(data)
            assert "Gültiger POI" in result
        except Exception as e:
            pytest.fail(f"Sollte gemischte Einträge handhaben: {e}")

    def test_get_names_unicode_characters(self):
        """Testet Umgang mit Unicode-Zeichen in Namen."""
        data = {
            "features": [
                {"properties": {"name": "Müller-Denkmal"}},
                {"properties": {"name": "Café Côte d'Azur"}},
                {"properties": {"name": "北京故宫"}},  # Chinesisch
            ]
        }

        result = get_names_as_comma_separated_string(data)

        assert "Müller-Denkmal" in result
        assert "Café Côte d'Azur" in result
        assert "北京故宫" in result

    def test_get_names_very_long_names(self):
        """Testet Verhalten mit sehr langen POI-Namen."""
        data = {"features": [{"properties": {"name": "A" * 200}}, {"properties": {"name": "Normal POI"}}]}  # Sehr langer Name

        result = get_names_as_comma_separated_string(data)

        assert "A" * 200 in result
        assert "Normal POI" in result

    def test_get_names_special_characters(self):
        """Testet Umgang mit Sonderzeichen."""
        data = {
            "features": [
                {"properties": {"name": "POI & Co."}},
                {"properties": {"name": "Museum (Alt)"}},
                {"properties": {"name": "St. Peter's Church"}},
            ]
        }

        result = get_names_as_comma_separated_string(data)

        assert "POI & Co." in result
        assert "Museum (Alt)" in result
        assert "St. Peter's Church" in result

    def test_get_names_empty_string_names(self):
        """Testet Verhalten mit leeren String-Namen."""
        data = {
            "features": [
                {"properties": {"name": ""}},
                {"properties": {"name": "Valider POI"}},
                {"properties": {"name": "   "}},  # Nur Whitespace
            ]
        }

        result = get_names_as_comma_separated_string(data)

        # Sollte leere Namen überspringen oder handhaben
        assert "Valider POI" in result


class TestGeoapifyIntegration:
    """Integrationstests für die Geoapify-Module."""

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_full_workflow(self, mock_get):
        """Testet kompletten Workflow: Suche + Namen-Extraktion."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {"properties": {"name": "Sehenswürdigkeit 1", "lat": 43.51, "lon": 16.44}},
                {"properties": {"name": "Sehenswürdigkeit 2", "lat": 43.52, "lon": 16.45}},
            ]
        }
        mock_get.return_value = mock_response

        # 1. POIs finden
        data = find_top_tourist_sights(43.5081, 16.4402)
        assert data is not None

        # 2. Namen extrahieren
        names = get_names_as_comma_separated_string(data)
        assert "Sehenswürdigkeit 1" in names
        assert "Sehenswürdigkeit 2" in names

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", None)
    def test_workflow_missing_api_key(self):
        """Testet Workflow bei fehlendem API-Key."""
        # 1. Suche schlägt fehl (gibt leeres Dict zurück)
        data = find_top_tourist_sights(43.5081, 16.4402)
        assert data == {"features": []}

        # 2. Namen-Extraktion mit leerem Dict sollte leeren String geben
        names = get_names_as_comma_separated_string(data)
        assert names == ""

    @patch("biketour_planner.geoapify.GEOAPIFY_CACHE_FILE", Path("non_existent.json"))
    @patch("biketour_planner.geoapify._geoapify_cache", {})  # Cache leeren
    @patch("biketour_planner.geoapify.geoapify_api_key", "test_key")
    @patch("biketour_planner.geoapify.requests.get")
    def test_workflow_no_results(self, mock_get):
        """Testet Workflow wenn keine POIs gefunden werden."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        # 1. Suche gibt leere Liste
        data = find_top_tourist_sights(43.5081, 16.4402)
        assert data is not None
        assert data["features"] == []

        # 2. Namen-Extraktion gibt leeren String
        names = get_names_as_comma_separated_string(data)
        assert names == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
