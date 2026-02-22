import pytest
from unittest.mock import MagicMock, patch
from biketour_planner.geocode import (
    clean_address,
    extract_city_country,
    geocode_with_nominatim,
    geocode_with_photon,
    geocode_address,
    GeocodingError
)

def test_clean_address():
    assert clean_address("Main St 1, Prizemlje") == "Main St 1,"
    assert clean_address("High St 2, 1. kat") == "High St 2,"
    assert clean_address("Road - 123") == "Road"
    assert clean_address("Place br. 45") == "Place"

def test_extract_city_country():
    assert extract_city_country("Street, City, Country") == "City, Country"
    assert extract_city_country("City, Country") == "City, Country"
    assert extract_city_country("OnlyCity") == "OnlyCity"

@patch("biketour_planner.geocode.geolocator_nominatim")
def test_geocode_with_nominatim_success(mock_nominatim):
    mock_loc = MagicMock()
    mock_loc.latitude = 1.0
    mock_loc.longitude = 2.0
    mock_nominatim.geocode.return_value = mock_loc

    lat, lon = geocode_with_nominatim("Test Address")
    assert lat == 1.0
    assert lon == 2.0

@patch("biketour_planner.geocode.geolocator_nominatim")
def test_geocode_with_nominatim_fail(mock_nominatim):
    mock_nominatim.geocode.return_value = None
    with pytest.raises(GeocodingError):
        geocode_with_nominatim("Nonexistent Address")

@patch("biketour_planner.geocode.geolocator_photon")
def test_geocode_with_photon_success(mock_photon):
    mock_loc = MagicMock()
    mock_loc.latitude = 3.0
    mock_loc.longitude = 4.0
    mock_photon.geocode.return_value = mock_loc

    # Ensure PHOTON_AVAILABLE is mocked or handled
    with patch("biketour_planner.geocode.geolocator_photon", mock_photon):
        lat, lon = geocode_with_photon("Test Address")
        assert lat == 3.0
        assert lon == 4.0

@patch("biketour_planner.geocode._cached_geocode")
def test_geocode_address_success(mock_cached):
    mock_cached.return_value = (5.0, 6.0)
    lat, lon = geocode_address("Any Address")
    assert lat == 5.0
    assert lon == 6.0

@patch("biketour_planner.geocode._cached_geocode")
def test_geocode_address_fail(mock_cached):
    mock_cached.return_value = None
    with pytest.raises(GeocodingError):
        geocode_address("Failing Address")

@patch("biketour_planner.geocode.geolocator_nominatim")
@patch("biketour_planner.geocode.geolocator_photon")
def test_cached_geocode_flow(mock_photon, mock_nominatim):
    # Test fallback flow in _cached_geocode
    # 1. Nominatim fails
    # 2. Photon fails
    # 3. Nominatim with city_country succeeds

    mock_nominatim.geocode.side_effect = [None, MagicMock(latitude=7.0, longitude=8.0)]
    mock_photon.geocode.return_value = None

    # We need to clear the cache or mock it to ensure it actually runs the logic
    with patch("biketour_planner.geocode._geocode_cache", {}):
        from biketour_planner.geocode import _cached_geocode
        result = _cached_geocode("Street, City, Country")
        assert result == (7.0, 8.0)

@patch("biketour_planner.geocode.geolocator_nominatim")
def test_geocode_with_nominatim_retries(mock_nominatim):
    from geopy.exc import GeocoderTimedOut
    mock_nominatim.geocode.side_effect = [GeocoderTimedOut("Timeout"), MagicMock(latitude=1.0, longitude=2.0)]

    with patch("biketour_planner.geocode.sleep"): # Skip sleep
        lat, lon = geocode_with_nominatim("Test Retries")
        assert lat == 1.0
        assert lon == 2.0
        assert mock_nominatim.geocode.call_count == 2

@patch("biketour_planner.geocode.geolocator_nominatim")
def test_geocode_with_nominatim_all_fail(mock_nominatim):
    from geopy.exc import GeocoderTimedOut
    mock_nominatim.geocode.side_effect = GeocoderTimedOut("Timeout")

    with patch("biketour_planner.geocode.sleep"): # Skip sleep
        with pytest.raises(GeocodingError):
            geocode_with_nominatim("Test All Fail")

@patch("biketour_planner.geocode.geolocator_photon")
def test_geocode_with_photon_none(mock_photon):
    with patch("biketour_planner.geocode.geolocator_photon", None):
        with pytest.raises(GeocodingError, match="Photon not available"):
            geocode_with_photon("Any")

@patch("biketour_planner.geocode.geolocator_photon")
def test_geocode_with_photon_exception(mock_photon):
    mock_photon.geocode.side_effect = Exception("General error")
    with pytest.raises(GeocodingError, match="General error"):
        geocode_with_photon("Any")

def test_cached_geocode_all_fail():
    with patch("biketour_planner.geocode.geocode_with_nominatim") as mock_nom:
        with patch("biketour_planner.geocode.geocode_with_photon") as mock_pho:
            mock_nom.side_effect = GeocodingError("addr", "nom fail")
            mock_pho.side_effect = GeocodingError("addr", "pho fail")

            with patch("biketour_planner.geocode._geocode_cache", {}):
                from biketour_planner.geocode import _cached_geocode
                assert _cached_geocode("Failing Address") is None
