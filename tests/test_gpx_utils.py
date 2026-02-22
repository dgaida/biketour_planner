import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from biketour_planner.gpx_utils import get_gps_tracks4day_4alldays

@patch("biketour_planner.gpx_utils.GPXRouteManager")
def test_get_gps_tracks4day_4alldays(mock_manager_class):
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.process_all_bookings.return_value = [{"enriched": True}]

    gpx_dir = Path("gpx")
    bookings = [{"hotel": "A"}]
    output_path = Path("out")

    result = get_gps_tracks4day_4alldays(gpx_dir, bookings, output_path)

    assert result == [{"enriched": True}]
    mock_manager_class.assert_called_once_with(gpx_dir, output_path)
    mock_manager.process_all_bookings.assert_called_once_with(bookings, output_path)
