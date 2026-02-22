import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from biketour_planner.pass_finder import (
    load_json,
    get_gpx_endpoints,
    find_nearest_hotel,
    find_pass_track,
    process_passes
)

def test_load_json(tmp_path):
    data = {"test": "value"}
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data))

    loaded = load_json(json_file)
    assert loaded == data

def test_load_json_error(tmp_path):
    json_file = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        load_json(json_file)

@patch("biketour_planner.pass_finder.read_gpx_file")
def test_get_gpx_endpoints(mock_read_gpx):
    mock_gpx = MagicMock()
    mock_track = MagicMock()
    mock_segment = MagicMock()
    mock_p1 = MagicMock(latitude=1.0, longitude=2.0)
    mock_p2 = MagicMock(latitude=3.0, longitude=4.0)

    mock_segment.points = [mock_p1, mock_p2]
    mock_track.segments = [mock_segment]
    mock_gpx.tracks = [mock_track]
    mock_read_gpx.return_value = mock_gpx

    endpoints = get_gpx_endpoints(Path("test.gpx"))
    assert endpoints == (1.0, 2.0, 3.0, 4.0)

def test_find_nearest_hotel():
    bookings = [
        {"hotel_name": "Far", "latitude": 10.0, "longitude": 10.0},
        {"hotel_name": "Near", "latitude": 1.1, "longitude": 1.1},
        {"hotel_name": "No GPS"}
    ]

    nearest = find_nearest_hotel(1.0, 1.0, bookings)
    assert nearest["hotel_name"] == "Near"

@patch("biketour_planner.pass_finder.get_gpx_endpoints")
@patch("biketour_planner.pass_finder.get_config")
def test_find_pass_track(mock_get_config, mock_get_endpoints, tmp_path):
    # Setup config
    mock_config = MagicMock()
    mock_config.passes.hotel_radius_km = 1.0
    mock_config.passes.pass_radius_km = 1.0
    mock_get_config.return_value = mock_config

    # Create dummy GPX files
    gpx_dir = tmp_path / "gpx"
    gpx_dir.mkdir()
    gpx_file = gpx_dir / "test_pass.gpx"
    gpx_file.write_text("dummy")

    # Mock endpoints: Start at (0,0), End at (10,10)
    # Hotel is at (0,0), Pass is at (10,10)
    mock_get_endpoints.return_value = (0.0, 0.0, 10.0, 10.0)

    track = find_pass_track(0.0, 0.0, 10.0, 10.0, gpx_dir)
    assert track == gpx_file

@patch("biketour_planner.pass_finder.get_gpx_endpoints")
@patch("biketour_planner.pass_finder.get_config")
def test_find_pass_track_reversed(mock_get_config, mock_get_endpoints, tmp_path):
    mock_config = MagicMock()
    mock_config.passes.hotel_radius_km = 1.0
    mock_config.passes.pass_radius_km = 1.0
    mock_get_config.return_value = mock_config

    gpx_dir = tmp_path / "gpx"
    gpx_dir.mkdir()
    gpx_file = gpx_dir / "test_pass_rev.gpx"
    gpx_file.write_text("dummy")

    # Mock endpoints: End at (0,0), Start at (10,10)
    # Hotel is at (0,0), Pass is at (10,10)
    mock_get_endpoints.return_value = (10.0, 10.0, 0.0, 0.0)

    track = find_pass_track(0.0, 0.0, 10.0, 10.0, gpx_dir)
    assert track == gpx_file

@patch("biketour_planner.pass_finder.load_json")
@patch("biketour_planner.pass_finder.geocode_address")
@patch("biketour_planner.pass_finder.find_pass_track")
@patch("biketour_planner.pass_finder.read_gpx_file")
@patch("biketour_planner.pass_finder.get_statistics4track")
@patch("biketour_planner.pass_finder.get_config")
def test_process_passes(
    mock_get_config,
    mock_get_stats,
    mock_read_gpx,
    mock_find_track,
    mock_geocode,
    mock_load_json,
    tmp_path
):
    # Setup config
    mock_config = MagicMock()
    mock_config.passes.hotel_radius_km = 1.0
    mock_config.passes.pass_radius_km = 1.0
    mock_get_config.return_value = mock_config

    passes_json = tmp_path / "passes.json"
    passes_json.write_text("[]")

    mock_load_json.return_value = [{"passname": "Alpe d'Huez"}]
    mock_geocode.return_value = (45.0, 6.0)

    gpx_file = tmp_path / "alpe.gpx"
    mock_find_track.return_value = gpx_file

    mock_read_gpx.return_value = MagicMock(tracks=[True])
    mock_get_stats.return_value = (1800.0, 14000.0, 1100.0, 0.0)

    bookings = [{"hotel_name": "Hotel Huez", "latitude": 45.01, "longitude": 6.01}]

    result = process_passes(passes_json, tmp_path, bookings)

    assert "paesse_tracks" in result[0]
    assert len(result[0]["paesse_tracks"]) == 1
    assert result[0]["paesse_tracks"][0]["passname"] == "Alpe d'Huez"
    assert result[0]["paesse_tracks"][0]["total_ascent_m"] == 1100

def test_process_passes_no_file(caplog):
    bookings = [{"hotel_name": "Test"}]
    result = process_passes(Path("nonexistent.json"), Path("."), bookings)
    assert result == bookings
    assert "Keine Pässe-Datei gefunden" in caplog.text

@patch("biketour_planner.pass_finder.load_json")
def test_process_passes_empty_list(mock_load_json, tmp_path, caplog):
    mock_load_json.return_value = []
    passes_json = tmp_path / "passes.json"
    passes_json.write_text("[]")
    bookings = [{"hotel_name": "Test"}]
    result = process_passes(passes_json, Path("."), bookings)
    assert result == bookings
    assert "Keine Pässe in der JSON-Datei" in caplog.text

@patch("biketour_planner.pass_finder.load_json")
def test_process_passes_invalid_pass(mock_load_json, tmp_path, caplog):
    mock_load_json.return_value = [{"something": "else"}]
    passes_json = tmp_path / "passes.json"
    passes_json.write_text("[]")
    bookings = [{"hotel_name": "Test"}]
    process_passes(passes_json, Path("."), bookings)
    assert "Pass ohne Namen gefunden" in caplog.text

@patch("biketour_planner.pass_finder.load_json")
@patch("biketour_planner.pass_finder.geocode_address")
def test_process_passes_geocode_error(mock_geocode, mock_load_json, tmp_path, caplog):
    mock_load_json.return_value = [{"passname": "Fail"}]
    mock_geocode.side_effect = ValueError("Geocode fail")
    passes_json = tmp_path / "passes.json"
    passes_json.write_text("[]")
    bookings = [{"hotel_name": "Test"}]
    process_passes(passes_json, Path("."), bookings)
    assert "Geocoding fehlgeschlagen" in caplog.text

@patch("biketour_planner.pass_finder.load_json")
@patch("biketour_planner.pass_finder.geocode_address")
def test_process_passes_no_hotel(mock_geocode, mock_load_json, tmp_path, caplog):
    mock_load_json.return_value = [{"passname": "Remote Pass"}]
    mock_geocode.return_value = (0.0, 0.0)
    passes_json = tmp_path / "passes.json"
    passes_json.write_text("[]")
    bookings = [] # No hotels
    process_passes(passes_json, Path("."), bookings)
    assert "Kein Hotel gefunden" in caplog.text

def test_get_gpx_endpoints_empty():
    with patch("biketour_planner.pass_finder.read_gpx_file") as mock_read:
        mock_read.return_value = None
        assert get_gpx_endpoints(Path("test.gpx")) is None

        mock_gpx = MagicMock(tracks=[])
        mock_read.return_value = mock_gpx
        assert get_gpx_endpoints(Path("test.gpx")) is None

def test_find_pass_track_no_tracks(tmp_path, mock_get_config):
    gpx_dir = tmp_path / "empty"
    gpx_dir.mkdir()
    assert find_pass_track(0, 0, 1, 1, gpx_dir) is None

@pytest.fixture
def mock_get_config():
    with patch("biketour_planner.pass_finder.get_config") as m:
        mock_config = MagicMock()
        mock_config.passes.hotel_radius_km = 1.0
        mock_config.passes.pass_radius_km = 1.0
        m.return_value = mock_config
        yield m
