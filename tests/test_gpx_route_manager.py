"""Unit-Tests für gpx_route_manager.py.

Testet die GPXRouteManager-Klasse inklusive:
- Initialisierung und GPX-Index-Erstellung
- Start- und Zielpositions-Bestimmung
- Track-Verkettung und Richtungserkennung
- Statistik-Berechnung (Distanz, Höhenmeter)
- GPX-Merging
- Mehrtägige Touren (previous_last_file)
"""

import pytest

# from pathlib import Path
from unittest.mock import patch
import gpxpy
from biketour_planner.gpx_route_manager import GPXRouteManager


# ============================================================================
# Test-Fixtures
# ============================================================================


@pytest.fixture
def gpx_dir(tmp_path):
    """Erstellt temporäres GPX-Verzeichnis."""
    gpx_path = tmp_path / "gpx"
    gpx_path.mkdir()
    return gpx_path


@pytest.fixture
def output_dir(tmp_path):
    """Erstellt temporäres Output-Verzeichnis."""
    output_path = tmp_path / "output"
    output_path.mkdir()
    return output_path


@pytest.fixture
def simple_gpx_file(gpx_dir):
    """Erstellt eine einfache Test-GPX-Datei."""
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0">
        <ele>500</ele>
      </trkpt>
      <trkpt lat="48.1" lon="11.1">
        <ele>520</ele>
      </trkpt>
      <trkpt lat="48.2" lon="11.2">
        <ele>540</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

    gpx_file = gpx_dir / "test_route.gpx"
    gpx_file.write_text(gpx_content, encoding="utf-8")
    return gpx_file


@pytest.fixture
def multiple_gpx_files(gpx_dir):
    """Erstellt mehrere GPX-Dateien für Verkettungs-Tests."""
    # Route 1: München Nord
    gpx1 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.2" lon="11.6"><ele>520</ele></trkpt>
      <trkpt lat="48.1" lon="11.5"><ele>515</ele></trkpt>
      <trkpt lat="48.0" lon="11.4"><ele>510</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    # Route 2: München Süd (verbindet mit Route 1)
    gpx2 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.4"><ele>510</ele></trkpt>
      <trkpt lat="47.9" lon="11.3"><ele>505</ele></trkpt>
      <trkpt lat="47.8" lon="11.2"><ele>500</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    # Route 3: Garmisch (verbindet mit Route 2)
    gpx3 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="47.8" lon="11.2"><ele>500</ele></trkpt>
      <trkpt lat="47.6" lon="11.1"><ele>600</ele></trkpt>
      <trkpt lat="47.5" lon="11.0"><ele>700</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    (gpx_dir / "route_north.gpx").write_text(gpx1, encoding="utf-8")
    (gpx_dir / "route_south.gpx").write_text(gpx2, encoding="utf-8")
    (gpx_dir / "route_garmisch.gpx").write_text(gpx3, encoding="utf-8")

    return gpx_dir


# ============================================================================
# Test GPXRouteManager Initialisierung
# ============================================================================


class TestGPXRouteManagerInit:
    """Tests für die Initialisierung des GPXRouteManager."""

    def test_init_creates_gpx_index(self, simple_gpx_file, output_dir):
        """Testet dass GPX-Index bei Initialisierung erstellt wird."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir, max_connection_distance_m=1000)

        assert manager.gpx_index is not None
        assert len(manager.gpx_index) == 1
        assert "test_route.gpx" in manager.gpx_index

    def test_init_stores_parameters(self, gpx_dir, output_dir):
        """Testet dass Initialisierungs-Parameter gespeichert werden."""
        manager = GPXRouteManager(gpx_dir, output_dir, max_connection_distance_m=2000, max_chain_length=15)

        assert manager.gpx_dir == gpx_dir
        assert manager.output_path == output_dir
        assert manager.max_connection_distance_m == 2000
        assert manager.max_chain_length == 15

    def test_init_with_empty_directory(self, gpx_dir, output_dir):
        """Testet Initialisierung mit leerem Verzeichnis."""
        manager = GPXRouteManager(gpx_dir, output_dir)

        assert manager.gpx_index == {}

    def test_init_skips_invalid_gpx_files(self, gpx_dir, output_dir):
        """Testet dass ungültige GPX-Dateien übersprungen werden."""
        # Erstelle ungültige GPX-Datei
        invalid_gpx = gpx_dir / "invalid.gpx"
        invalid_gpx.write_text("nicht-gpx-inhalt", encoding="utf-8")

        # Erstelle gültige GPX-Datei
        valid_gpx = gpx_dir / "valid.gpx"
        valid_gpx.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
    </trkseg>
  </trk>
</gpx>""",
            encoding="utf-8",
        )

        manager = GPXRouteManager(gpx_dir, output_dir)

        # Nur die gültige Datei sollte im Index sein
        assert len(manager.gpx_index) == 1
        assert "valid.gpx" in manager.gpx_index
        assert "invalid.gpx" not in manager.gpx_index


class TestGPXIndexPreprocessing:
    """Tests für die GPX-Index-Vorverarbeitung."""

    def test_index_contains_metadata(self, simple_gpx_file, output_dir):
        """Testet dass Index alle wichtigen Metadaten enthält."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        assert "file" in meta
        assert "start_lat" in meta
        assert "start_lon" in meta
        assert "end_lat" in meta
        assert "end_lon" in meta
        assert "total_distance_m" in meta
        assert "total_ascent_m" in meta
        assert "max_elevation_m" in meta
        assert "points" in meta

    def test_index_calculates_distance(self, simple_gpx_file, output_dir):
        """Testet dass Distanz korrekt berechnet wird."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        # Distanz sollte > 0 sein
        assert meta["total_distance_m"] > 0
        # Ca. 2x 15km = 30km für die Test-Route
        assert 25000 < meta["total_distance_m"] < 35000

    def test_index_calculates_ascent(self, simple_gpx_file, output_dir):
        """Testet dass Höhenmeter korrekt berechnet werden."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        # Anstieg: 500 -> 520 -> 540 = 40m
        assert meta["total_ascent_m"] == pytest.approx(40, abs=1)

    def test_index_finds_max_elevation(self, simple_gpx_file, output_dir):
        """Testet dass maximale Höhe gefunden wird."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        assert meta["max_elevation_m"] == 540

    def test_index_stores_all_points(self, simple_gpx_file, output_dir):
        """Testet dass alle Punkte mit Index gespeichert werden."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]
        points = meta["points"]

        assert len(points) == 3
        assert points[0]["lat"] == 48.0
        assert points[0]["lon"] == 11.0
        assert points[0]["elevation"] == 500
        assert points[0]["index"] == 0

        assert points[2]["lat"] == 48.2
        assert points[2]["index"] == 2


# ============================================================================
# Test Positions-Bestimmung
# ============================================================================


class TestFindStartPos:
    """Tests für die _find_start_pos Methode."""

    def test_find_start_pos_without_previous(self, simple_gpx_file, output_dir):
        """Testet Start-Suche ohne vorherige Route."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        # Suche Start nahe erstem Punkt
        start_file, start_index, force_direction = manager._find_start_pos(
            start_lat=48.05, start_lon=11.05, target_lat=48.2, target_lon=11.2, previous_last_file=None
        )

        assert start_file == "test_route.gpx"
        assert start_index is not None
        assert force_direction is None

    def test_find_start_pos_with_previous_forward(self, simple_gpx_file, output_dir):
        """Testet Start-Suche mit vorheriger Route (vorwärts)."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        previous_last_file = {"file": "test_route.gpx", "end_index": 1, "reversed": False}

        start_file, start_index, force_direction = manager._find_start_pos(
            start_lat=48.05, start_lon=11.05, target_lat=48.2, target_lon=11.2, previous_last_file=previous_last_file
        )

        assert start_file == "test_route.gpx"
        assert start_index == 1
        assert force_direction == "forward"

    def test_find_start_pos_with_previous_backward(self, simple_gpx_file, output_dir):
        """Testet Start-Suche mit vorheriger Route (rückwärts)."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        previous_last_file = {"file": "test_route.gpx", "end_index": 1, "reversed": True}

        start_file, start_index, force_direction = manager._find_start_pos(
            start_lat=48.05, start_lon=11.05, target_lat=48.2, target_lon=11.2, previous_last_file=previous_last_file
        )

        assert start_file == "test_route.gpx"
        assert force_direction == "backward"


class TestFindTargetPos:
    """Tests für die _find_target_pos Methode."""

    def test_find_target_pos_basic(self, simple_gpx_file, output_dir):
        """Testet Ziel-Suche grundlegend."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        target_file, target_index, target_side_lat, target_side_lon = manager._find_target_pos(48.0, 11.0, 48.2, 11.2)

        assert target_file == "test_route.gpx"
        assert target_index is not None
        assert target_side_lat is not None
        assert target_side_lon is not None

    def test_find_target_pos_determines_correct_side(self, simple_gpx_file, output_dir):
        """Testet dass richtige Ziel-Seite bestimmt wird."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        # Start im Norden (näher am Ende des Tracks)
        _, _, target_side_lat, target_side_lon = manager._find_target_pos(48.3, 11.3, 48.2, 11.2)  # Start  # Ziel

        # Ziel-Seite sollte das Ende des Tracks sein (48.2, 11.2)
        assert target_side_lat == pytest.approx(48.2, abs=0.01)
        assert target_side_lon == pytest.approx(11.2, abs=0.01)


# ============================================================================
# Test Track-Statistiken
# ============================================================================


class TestGetStatistics4Track:
    """Tests für die _get_statistics4track Methode."""

    def test_statistics_forward_direction(self, simple_gpx_file, output_dir):
        """Testet Statistik-Berechnung vorwärts."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        max_elev, total_dist, total_asc, total_desc = manager._get_statistics4track(
            meta=meta,
            current_index=0,
            end_index=2,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
            reversed_direction=False,
        )

        assert max_elev == 540
        assert total_dist > 0
        assert total_asc == pytest.approx(40, abs=1)
        assert total_desc == pytest.approx(0, abs=1)

    def test_statistics_backward_direction(self, simple_gpx_file, output_dir):
        """Testet Statistik-Berechnung rückwärts."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        max_elev, total_dist, total_asc, total_desc = manager._get_statistics4track(
            meta=meta,
            current_index=2,
            end_index=0,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
            reversed_direction=True,
        )

        assert max_elev == 540
        assert total_dist > 0
        # Rückwärts: keine Anstiege (540 -> 520 -> 500)
        assert total_asc == pytest.approx(0, abs=1)
        assert total_desc == pytest.approx(40, abs=1)

    def test_statistics_partial_track(self, simple_gpx_file, output_dir):
        """Testet Statistik-Berechnung für Teilstrecke."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        meta = manager.gpx_index["test_route.gpx"]

        # Nur Index 0 bis 1
        max_elev, total_dist, total_asc, total_desc = manager._get_statistics4track(
            meta=meta,
            current_index=0,
            end_index=1,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
            reversed_direction=False,
        )

        assert max_elev == 520
        assert total_asc == pytest.approx(20, abs=1)
        assert total_desc == pytest.approx(0, abs=1)


# ============================================================================
# Test GPX-Merging
# ============================================================================


class TestMergeGPXFiles:
    """Tests für die merge_gpx_files Methode."""

    def test_merge_single_file(self, simple_gpx_file, output_dir):
        """Testet Merging einer einzelnen Datei."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        route_files = [{"file": "test_route.gpx", "start_index": 0, "end_index": 2, "reversed": False}]

        booking = {"arrival_date": "2026-05-15", "hotel_name": "Test Hotel"}

        output_path = manager.merge_gpx_files(route_files, output_dir, booking)

        assert output_path is not None
        assert output_path.exists()
        assert "2026-05-15" in output_path.name
        assert "Test_Hotel" in output_path.name

    def test_merge_multiple_files(self, multiple_gpx_files, output_dir):
        """Testet Merging mehrerer Dateien."""
        manager = GPXRouteManager(multiple_gpx_files, output_dir)

        route_files = [
            {"file": "route_north.gpx", "start_index": 0, "end_index": 2, "reversed": False},
            {"file": "route_south.gpx", "start_index": 0, "end_index": 2, "reversed": False},
        ]

        booking = {"arrival_date": "2026-05-15", "hotel_name": "Test Hotel"}

        output_path = manager.merge_gpx_files(route_files, output_dir, booking)

        assert output_path is not None

        # Prüfe dass GPX-Datei gültig ist
        gpx = gpxpy.parse(output_path.read_text(encoding="utf-8"))
        assert len(gpx.tracks) == 1
        assert len(gpx.tracks[0].segments) == 1
        # Sollte 6 Punkte haben (3 + 3)
        assert len(gpx.tracks[0].segments[0].points) == 6

    def test_merge_with_reversed_track(self, simple_gpx_file, output_dir):
        """Testet Merging mit rückwärts durchlaufenem Track."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        route_files = [{"file": "test_route.gpx", "start_index": 2, "end_index": 0, "reversed": True}]

        booking = {"arrival_date": "2026-05-15", "hotel_name": "Test Hotel"}

        output_path = manager.merge_gpx_files(route_files, output_dir, booking)

        gpx = gpxpy.parse(output_path.read_text(encoding="utf-8"))
        points = gpx.tracks[0].segments[0].points

        # Punkte sollten in umgekehrter Reihenfolge sein
        assert points[0].latitude == 48.2
        assert points[-1].latitude == 48.0

    def test_merge_returns_none_on_empty_input(self, gpx_dir, output_dir):
        """Testet dass None zurückgegeben wird bei leerer Input-Liste."""
        manager = GPXRouteManager(gpx_dir, output_dir)

        result = manager.merge_gpx_files([], output_dir, {})

        assert result is None

    def test_merge_sanitizes_hotel_name(self, simple_gpx_file, output_dir):
        """Testet dass Hotelname bereinigt wird."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        route_files = [{"file": "test_route.gpx", "start_index": 0, "end_index": 1, "reversed": False}]

        booking = {"arrival_date": "2026-05-15", "hotel_name": "Test/Hotel & Co. (Special)"}

        output_path = manager.merge_gpx_files(route_files, output_dir, booking)

        # Sonderzeichen sollten entfernt sein
        assert "/" not in output_path.name
        assert "&" not in output_path.name
        assert "(" not in output_path.name


# ============================================================================
# Test Komplette Workflows
# ============================================================================


class TestCollectRouteBetweenLocations:
    """Tests für die collect_route_between_locations Methode."""

    def test_collect_route_single_file(self, simple_gpx_file, output_dir):
        """Testet Route-Sammlung innerhalb einer Datei."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        booking = {"arrival_date": "2026-05-15", "hotel_name": "Test Hotel"}

        manager.collect_route_between_locations(
            start_lat=48.05, start_lon=11.05, target_lat=48.15, target_lon=11.15, booking=booking
        )

        assert "gpx_files" in booking
        assert len(booking["gpx_files"]) > 0
        assert "total_distance_km" in booking
        assert booking["total_distance_km"] > 0

    def test_collect_route_with_previous_file(self, simple_gpx_file, output_dir):
        """Testet Route-Sammlung mit vorheriger Datei."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        previous_last_file = {"file": "test_route.gpx", "end_index": 1, "reversed": False}

        booking = {}

        manager.collect_route_between_locations(
            start_lat=48.1,
            start_lon=11.1,
            target_lat=48.2,
            target_lon=11.2,
            booking=booking,
            previous_last_file=previous_last_file,
        )

        assert "gpx_files" in booking
        assert "_last_gpx_file" in booking

    def test_collect_route_updates_booking_statistics(self, simple_gpx_file, output_dir):
        """Testet dass Booking-Statistiken aktualisiert werden."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        booking = {}

        manager.collect_route_between_locations(
            start_lat=48.0, start_lon=11.0, target_lat=48.2, target_lon=11.2, booking=booking
        )

        assert "total_distance_km" in booking
        assert "total_ascent_m" in booking
        assert "max_elevation_m" in booking
        assert isinstance(booking["total_distance_km"], (int, float))
        assert isinstance(booking["total_ascent_m"], int)


class TestProcessAllBookings:
    """Tests für die process_all_bookings Methode."""

    def test_process_all_bookings_sorts_by_date(self, simple_gpx_file, output_dir):
        """Testet dass Bookings nach Datum sortiert werden."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        bookings = [
            {"arrival_date": "2026-05-20", "hotel_name": "Hotel B", "latitude": 48.2, "longitude": 11.2},
            {"arrival_date": "2026-05-15", "hotel_name": "Hotel A", "latitude": 48.1, "longitude": 11.1},
        ]

        with patch.object(manager, "collect_route_between_locations"):
            with patch.object(manager, "extend_track2hotel"):
                with patch.object(manager, "merge_gpx_files"):
                    result = manager.process_all_bookings(bookings, output_dir)

        # Sollte nach Datum sortiert sein
        assert result[0]["arrival_date"] == "2026-05-15"
        assert result[1]["arrival_date"] == "2026-05-20"

    def test_process_all_bookings_skips_first(self, simple_gpx_file, output_dir):
        """Testet dass erste Buchung keine Route erhält."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir)

        bookings = [
            {"arrival_date": "2026-05-15", "hotel_name": "Hotel A", "latitude": 48.1, "longitude": 11.1},
            {"arrival_date": "2026-05-16", "hotel_name": "Hotel B", "latitude": 48.2, "longitude": 11.2},
        ]

        with patch.object(manager, "collect_route_between_locations") as mock_collect:
            with patch.object(manager, "extend_track2hotel"):
                with patch.object(manager, "merge_gpx_files"):
                    manager.process_all_bookings(bookings, output_dir)

        # collect_route sollte nur 1x aufgerufen werden (für 2. Booking)
        assert mock_collect.call_count == 1


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests für Grenzfälle und Fehlerbehandlung."""

    def test_handles_missing_gpx_files(self, gpx_dir, output_dir):
        """Testet Verhalten wenn GPX-Dateien nicht existieren."""
        manager = GPXRouteManager(gpx_dir, output_dir)

        booking = {}

        manager.collect_route_between_locations(
            start_lat=48.0, start_lon=11.0, target_lat=48.1, target_lon=11.1, booking=booking
        )

        # Sollte leere Werte setzen wenn keine GPX-Dateien gefunden
        assert booking.get("gpx_files") == []
        assert booking.get("total_distance_km") == 0

    def test_handles_coordinates_far_apart(self, simple_gpx_file, output_dir):
        """Testet Verhalten bei weit entfernten Koordinaten."""
        manager = GPXRouteManager(simple_gpx_file.parent, output_dir, max_connection_distance_m=100)  # Sehr kleine Distanz

        booking = {}

        manager.collect_route_between_locations(
            start_lat=48.0, start_lon=11.0, target_lat=50.0, target_lon=13.0, booking=booking  # Sehr weit entfernt
        )

        # Sollte trotzdem Werte setzen
        assert "gpx_files" in booking
        assert "total_distance_km" in booking

    def test_max_chain_length_limit(self, multiple_gpx_files, output_dir):
        """Testet dass max_chain_length respektiert wird."""
        manager = GPXRouteManager(multiple_gpx_files, output_dir, max_chain_length=2)  # Sehr kleine Grenze

        booking = {}

        manager.collect_route_between_locations(
            start_lat=48.2, start_lon=11.6, target_lat=47.5, target_lon=11.0, booking=booking
        )

        # Sollte maximal 2 Dateien haben
        if "gpx_files" in booking:
            assert len(booking["gpx_files"]) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
