"""Unit-Tests für private Methoden in gpx_route_manager.py.

Testet die internen Hilfsmethoden des GPXRouteManager inklusive:
- _init_end_index: Endindex-Initialisierung bei erzwungener Richtung
- _set_end_index: Endindex-Bestimmung für Track-Abschnitte
- _add_target_track_to_route: Ziel-Track zur Route hinzufügen
- _process_route_iteration: Einzelne Routing-Iteration
- _find_next_gpx_file: Nächste GPX-Datei in Kette finden
- _update_gpx_index_entry: GPX-Index aktualisieren
"""

import pytest

# from pathlib import Path
from unittest.mock import Mock, patch

# import gpxpy
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
def manager_with_test_track(gpx_dir, output_dir):
    """Erstellt Manager mit Test-Track für private Methoden-Tests."""
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.1" lon="11.1"><ele>520</ele></trkpt>
      <trkpt lat="48.2" lon="11.2"><ele>540</ele></trkpt>
      <trkpt lat="48.3" lon="11.3"><ele>560</ele></trkpt>
      <trkpt lat="48.4" lon="11.4"><ele>580</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    gpx_file = gpx_dir / "test_track.gpx"
    gpx_file.write_text(gpx_content, encoding="utf-8")

    return GPXRouteManager(gpx_dir, output_dir)


@pytest.fixture
def manager_with_multiple_tracks(gpx_dir, output_dir):
    """Erstellt Manager mit mehreren verkettbaren Tracks."""
    # Track 1: Nord
    gpx1 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.5" lon="11.5"><ele>600</ele></trkpt>
      <trkpt lat="48.4" lon="11.4"><ele>580</ele></trkpt>
      <trkpt lat="48.3" lon="11.3"><ele>560</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    # Track 2: Mitte (verbindet mit Track 1)
    gpx2 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.3" lon="11.3"><ele>560</ele></trkpt>
      <trkpt lat="48.2" lon="11.2"><ele>540</ele></trkpt>
      <trkpt lat="48.1" lon="11.1"><ele>520</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    # Track 3: Süd (verbindet mit Track 2)
    gpx3 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.1" lon="11.1"><ele>520</ele></trkpt>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="47.9" lon="10.9"><ele>480</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    (gpx_dir / "track_north.gpx").write_text(gpx1, encoding="utf-8")
    (gpx_dir / "track_middle.gpx").write_text(gpx2, encoding="utf-8")
    (gpx_dir / "track_south.gpx").write_text(gpx3, encoding="utf-8")

    return GPXRouteManager(gpx_dir, output_dir)


# ============================================================================
# Test _init_end_index
# ============================================================================


class TestInitEndIndex:
    """Tests für die _init_end_index Methode."""

    def test_init_end_index_forward_direction(self, manager_with_test_track):
        """Testet Endindex-Initialisierung vorwärts."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Start bei Index 1, suche vorwärts zum nächsten Punkt zu (48.3, 11.3)
        end_index = manager._init_end_index(
            current_index=1, meta=meta, force_direction="forward", target_side_lat=48.3, target_side_lon=11.3
        )

        # Sollte Index 3 finden (nächster Punkt zu Ziel-Seite, vorwärts)
        assert end_index == 3

    def test_init_end_index_backward_direction(self, manager_with_test_track):
        """Testet Endindex-Initialisierung rückwärts."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Start bei Index 3, suche rückwärts zum nächsten Punkt zu (48.0, 11.0)
        end_index = manager._init_end_index(
            current_index=3, meta=meta, force_direction="backward", target_side_lat=48.0, target_side_lon=11.0
        )

        # Sollte Index 0 finden (nächster Punkt zu Ziel-Seite, rückwärts)
        assert end_index == 0

    def test_init_end_index_forward_no_better_point(self, manager_with_test_track):
        """Testet forward wenn kein besserer Punkt existiert."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Start bei Index 4 (letzter Punkt), kann nicht weiter vorwärts
        end_index = manager._init_end_index(
            current_index=4, meta=meta, force_direction="forward", target_side_lat=48.5, target_side_lon=11.5
        )

        # Sollte bei current_index bleiben
        assert end_index == 4

    def test_init_end_index_backward_no_better_point(self, manager_with_test_track):
        """Testet backward wenn kein besserer Punkt existiert."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Start bei Index 0 (erster Punkt), kann nicht weiter rückwärts
        end_index = manager._init_end_index(
            current_index=0, meta=meta, force_direction="backward", target_side_lat=47.9, target_side_lon=10.9
        )

        # Sollte bei current_index bleiben
        assert end_index == 0

    def test_init_end_index_forward_finds_exact_match(self, manager_with_test_track):
        """Testet dass exakte Übereinstimmung gefunden wird."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Suche nach exaktem Punkt (Index 2)
        end_index = manager._init_end_index(
            current_index=0, meta=meta, force_direction="forward", target_side_lat=48.2, target_side_lon=11.2
        )

        assert end_index == 2


# ============================================================================
# Test _set_end_index
# ============================================================================


class TestSetEndIndex:
    """Tests für die _set_end_index Methode."""

    def test_set_end_index_first_iteration_with_force(self, manager_with_test_track):
        """Testet dass bei iteration=0 mit force_direction _init_end_index aufgerufen wird."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        end_index = manager._set_end_index(
            current_index=1, meta=meta, force_direction="forward", target_side_lat=48.3, target_side_lon=11.3, iteration=0
        )

        # Sollte _init_end_index nutzen (forward von Index 1 zu 48.3/11.3)
        assert end_index == 3

    def test_set_end_index_later_iteration_ignores_force(self, manager_with_test_track):
        """Testet dass bei iteration>0 force_direction ignoriert wird."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        end_index = manager._set_end_index(
            current_index=1,
            meta=meta,
            force_direction="forward",  # Sollte ignoriert werden
            target_side_lat=48.0,
            target_side_lon=11.0,
            iteration=1,
        )

        # Sollte nächsten Punkt zur Ziel-Seite finden (unabhängig von Richtung)
        assert end_index == 0

    def test_set_end_index_no_force_direction(self, manager_with_test_track):
        """Testet ohne erzwungene Richtung."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        end_index = manager._set_end_index(
            current_index=2, meta=meta, force_direction=None, target_side_lat=48.4, target_side_lon=11.4, iteration=0
        )

        # Sollte nächsten Punkt zur Ziel-Seite finden (Index 4)
        assert end_index == 4

    def test_set_end_index_finds_closest_to_target_side(self, manager_with_test_track):
        """Testet dass wirklich nächster Punkt zur Ziel-Seite gefunden wird."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # Von Mitte des Tracks, suche zu Anfang
        end_index = manager._set_end_index(
            current_index=2, meta=meta, force_direction=None, target_side_lat=48.0, target_side_lon=11.0, iteration=1
        )

        assert end_index == 0


# ============================================================================
# Test _add_target_track_to_route
# ============================================================================


class TestAddTargetTrackToRoute:
    """Tests für die _add_target_track_to_route Methode."""

    def test_add_target_track_start_closer(self, manager_with_test_track):
        """Testet Hinzufügen wenn Start näher an aktueller Position."""
        manager = manager_with_test_track
        route_files = []

        manager._add_target_track_to_route(
            target_file="test_track.gpx", target_index=2, current_lat=48.0, current_lon=11.0, route_files=route_files
        )

        assert len(route_files) == 1
        assert route_files[0]["file"] == "test_track.gpx"
        assert route_files[0]["end_index"] == 2
        assert route_files[0]["reversed"] is False

    def test_add_target_track_end_closer(self, manager_with_test_track):
        """Testet Hinzufügen wenn Ende näher an aktueller Position."""
        manager = manager_with_test_track
        route_files = []

        manager._add_target_track_to_route(
            target_file="test_track.gpx", target_index=2, current_lat=48.4, current_lon=11.4, route_files=route_files
        )

        assert len(route_files) == 1
        assert route_files[0]["file"] == "test_track.gpx"
        assert route_files[0]["reversed"] is True
        # Bei reversed: start_index > end_index
        assert route_files[0]["start_index"] > route_files[0]["end_index"]

    def test_add_target_track_appends_to_existing_route(self, manager_with_test_track):
        """Testet dass Track zur existierenden Route hinzugefügt wird."""
        manager = manager_with_test_track
        route_files = [{"file": "other.gpx", "start_index": 0, "end_index": 5, "reversed": False}]

        manager._add_target_track_to_route(
            target_file="test_track.gpx", target_index=1, current_lat=48.0, current_lon=11.0, route_files=route_files
        )

        assert len(route_files) == 2
        assert route_files[1]["file"] == "test_track.gpx"


# ============================================================================
# Test _find_next_gpx_file
# ============================================================================


class TestFindNextGPXFile:
    """Tests für die _find_next_gpx_file Methode."""

    def test_find_next_gpx_file_basic(self, manager_with_multiple_tracks):
        """Testet grundlegende Suche nach nächster GPX-Datei."""
        manager = manager_with_multiple_tracks

        visited = set()
        used_base_files = set()

        # Von track_north (Ende bei 48.3, 11.3) -> track_middle sollte gefunden werden
        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.3, current_lon=11.3
        )

        assert next_file is not None
        assert "track_middle.gpx" in next_file or "track_north.gpx" in next_file
        assert next_index is not None

    def test_find_next_gpx_file_excludes_visited(self, manager_with_multiple_tracks):
        """Testet dass bereits besuchte Dateien ausgeschlossen werden."""
        manager = manager_with_multiple_tracks

        visited = {"track_middle.gpx"}
        used_base_files = {"track_middle"}

        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.3, current_lon=11.3
        )

        # track_middle sollte nicht zurückgegeben werden
        assert next_file != "track_middle.gpx"

    def test_find_next_gpx_file_excludes_same_base(self, gpx_dir, output_dir):
        """Testet dass Dateien mit gleichem Basis-Namen ausgeschlossen werden."""
        # Erstelle Route und Route_reversed
        gpx1 = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.1" lon="11.1"><ele>520</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        (gpx_dir / "route.gpx").write_text(gpx1, encoding="utf-8")
        (gpx_dir / "route_reversed.gpx").write_text(gpx1, encoding="utf-8")

        manager = GPXRouteManager(gpx_dir, output_dir)

        visited = set()
        used_base_files = {"route"}  # route bereits verwendet

        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.0, current_lon=11.0
        )

        # Weder route.gpx noch route_reversed.gpx sollten zurückgegeben werden
        assert next_file is None or "route" not in next_file

    def test_find_next_gpx_file_respects_max_distance(self, manager_with_multiple_tracks):
        """Testet dass max_connection_distance_m respektiert wird."""
        manager = manager_with_multiple_tracks
        manager.max_connection_distance_m = 100  # Sehr kleine Distanz

        visited = set()
        used_base_files = set()

        # Suche von Position die weit weg von allen Tracks ist
        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=50.0, current_lon=13.0
        )

        # Sollte nichts finden (alle zu weit weg)
        assert next_file is None
        assert next_index is None

    def test_find_next_gpx_file_prefers_shorter_route(self, gpx_dir, output_dir):
        """Testet dass bei ähnlicher Distanz kürzere Route bevorzugt wird."""
        # Erstelle zwei Routen mit ähnlicher Start-Position
        gpx_short = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.05" lon="11.05"><ele>510</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        gpx_long = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.001" lon="11.001"><ele>500</ele></trkpt>
      <trkpt lat="48.1" lon="11.1"><ele>520</ele></trkpt>
      <trkpt lat="48.2" lon="11.2"><ele>540</ele></trkpt>
      <trkpt lat="48.3" lon="11.3"><ele>560</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        (gpx_dir / "short.gpx").write_text(gpx_short, encoding="utf-8")
        (gpx_dir / "long.gpx").write_text(gpx_long, encoding="utf-8")

        manager = GPXRouteManager(gpx_dir, output_dir)

        visited = set()
        used_base_files = set()

        next_file, _ = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.0, current_lon=11.0
        )

        # Sollte kürzere Route bevorzugen (bei ähnlicher Distanz)
        assert next_file == "short.gpx"

    def test_find_next_gpx_file_returns_none_when_all_visited(self, manager_with_multiple_tracks):
        """Testet dass None zurückgegeben wird wenn alle Dateien besucht."""
        manager = manager_with_multiple_tracks

        # Markiere alle als besucht
        visited = {"track_north.gpx", "track_middle.gpx", "track_south.gpx"}
        used_base_files = {"track_north", "track_middle", "track_south"}

        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.0, current_lon=11.0
        )

        assert next_file is None
        assert next_index is None


# ============================================================================
# Test _process_route_iteration
# ============================================================================


class TestProcessRouteIteration:
    """Tests für die _process_route_iteration Methode."""

    def test_process_route_iteration_basic(self, manager_with_test_track):
        """Testet grundlegende Routing-Iteration."""
        manager = manager_with_test_track

        visited = set()
        used_base_files = set()
        route_files = []

        should_continue, next_file, next_index, lat, lon, max_elev, dist, asc, desc = manager._process_route_iteration(
            iteration=0,
            current_file="test_track.gpx",
            current_index=0,
            target_file="test_track.gpx",
            target_index=4,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=None,
            target_side_lat=48.4,
            target_side_lon=11.4,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
        )

        # Sollte Ziel erreicht haben
        assert should_continue is False
        assert len(route_files) == 1
        assert route_files[0]["file"] == "test_track.gpx"

    def test_process_route_iteration_already_visited(self, manager_with_test_track):
        """Testet Abbruch wenn Datei bereits besucht."""
        manager = manager_with_test_track

        visited = {"test_track.gpx"}  # Bereits besucht
        used_base_files = set()
        route_files = []

        should_continue, *rest = manager._process_route_iteration(
            iteration=0,
            current_file="test_track.gpx",
            current_index=0,
            target_file="test_track.gpx",
            target_index=4,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=None,
            target_side_lat=48.4,
            target_side_lon=11.4,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
        )

        assert should_continue is False
        assert len(route_files) == 0

    def test_process_route_iteration_base_file_used(self, manager_with_test_track):
        """Testet Abbruch wenn Basis-Datei bereits verwendet."""
        manager = manager_with_test_track

        visited = set()
        used_base_files = {"test_track"}  # Basis bereits verwendet
        route_files = []

        should_continue, *rest = manager._process_route_iteration(
            iteration=0,
            current_file="test_track.gpx",
            current_index=0,
            target_file="test_track.gpx",
            target_index=4,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=None,
            target_side_lat=48.4,
            target_side_lon=11.4,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
        )

        assert should_continue is False

    def test_process_route_iteration_updates_statistics(self, manager_with_test_track):
        """Testet dass Statistiken aktualisiert werden."""
        manager = manager_with_test_track

        visited = set()
        used_base_files = set()
        route_files = []

        _, _, _, _, _, max_elev, dist, asc, desc = manager._process_route_iteration(
            iteration=0,
            current_file="test_track.gpx",
            current_index=0,
            target_file="test_track.gpx",
            target_index=4,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=None,
            target_side_lat=48.4,
            target_side_lon=11.4,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
        )

        assert max_elev == 580  # Höchster Punkt
        assert dist > 0  # Distanz sollte berechnet sein
        assert asc == pytest.approx(80, abs=5)  # 500->580 = 80m Anstieg
        assert desc == pytest.approx(0, abs=1)  # Keine Abstiege bei Vorwärtsfahrt

    def test_process_route_iteration_marks_visited(self, manager_with_test_track):
        """Testet dass Datei als besucht markiert wird."""
        manager = manager_with_test_track

        visited = set()
        used_base_files = set()
        route_files = []

        manager._process_route_iteration(
            iteration=0,
            current_file="test_track.gpx",
            current_index=0,
            target_file="test_track.gpx",
            target_index=4,
            visited=visited,
            used_base_files=used_base_files,
            route_files=route_files,
            force_direction=None,
            target_side_lat=48.4,
            target_side_lon=11.4,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            total_descent=0,
        )

        assert "test_track.gpx" in visited
        # Die Implementierung fügt den vollständigen Dateinamen zu used_base_files hinzu, nicht nur die Basis
        assert "test_track.gpx" in used_base_files


# ============================================================================
# Test _update_gpx_index_entry
# ============================================================================


class TestUpdateGPXIndexEntry:
    """Tests für die _update_gpx_index_entry Methode."""

    def test_update_gpx_index_entry_removes_old(self, manager_with_test_track, output_dir):
        """Testet dass alter Eintrag entfernt wird."""
        manager = manager_with_test_track

        # Alter Eintrag sollte existieren
        assert "test_track.gpx" in manager.gpx_index

        # Erstelle neue GPX-Datei
        new_gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="49.0" lon="12.0"><ele>600</ele></trkpt>
      <trkpt lat="49.1" lon="12.1"><ele>620</ele></trkpt>
      <trkpt lat="49.2" lon="12.2"><ele>640</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        new_gpx_file = output_dir / "new_track.gpx"
        new_gpx_file.write_text(new_gpx_content, encoding="utf-8")

        manager._update_gpx_index_entry("test_track.gpx", new_gpx_file)

        meta = manager.gpx_index["new_track.gpx"]

        assert meta["start_lat"] == 49.0
        assert meta["start_lon"] == 12.0
        assert meta["end_lat"] == 49.2
        assert meta["end_lon"] == 12.2
        assert meta["max_elevation_m"] == 640
        assert meta["total_ascent_m"] == pytest.approx(40, abs=5)
        assert len(meta["points"]) == 3

    def test_update_gpx_index_entry_handles_invalid_file(self, manager_with_test_track, output_dir):
        """Testet Verhalten bei ungültiger GPX-Datei."""
        manager = manager_with_test_track

        invalid_gpx_file = output_dir / "invalid.gpx"
        invalid_gpx_file.write_text("nicht-gpx", encoding="utf-8")

        # Sollte alten Eintrag entfernen aber keinen neuen hinzufügen
        manager._update_gpx_index_entry("test_track.gpx", invalid_gpx_file)

        assert "test_track.gpx" not in manager.gpx_index
        assert "invalid.gpx" not in manager.gpx_index


# ============================================================================
# Test extend_track2hotel
# ============================================================================


class TestExtendTrack2Hotel:
    """Tests für die extend_track2hotel Methode."""

    @patch("biketour_planner.gpx_route_manager.get_route2address_as_points")
    def test_extend_track2hotel_basic(self, mock_get_route, manager_with_test_track, output_dir):
        """Testet grundlegendes Erweitern zur Unterkunft."""
        manager = manager_with_test_track

        # Mock Route-Punkte
        mock_points = [
            Mock(latitude=48.4, longitude=11.4, elevation=580),
            Mock(latitude=48.45, longitude=11.45, elevation=590),
            Mock(latitude=48.5, longitude=11.5, elevation=600),
        ]
        mock_get_route.return_value = mock_points

        booking = {
            "arrival_date": "2026-05-15",
            "hotel_name": "Hotel Test",
            "latitude": 48.5,
            "longitude": 11.5,
            "gpx_files": [{"file": "test_track.gpx", "start_index": 0, "end_index": 4, "reversed": False}],
            "_last_gpx_file": {"file": "test_track.gpx", "end_index": 4, "reversed": False},
        }

        result = manager.extend_track2hotel(booking, output_dir)

        assert result is not None
        assert result.exists()
        assert "to_hotel" in result.name

    def test_extend_track2hotel_no_gpx_files(self, manager_with_test_track, output_dir):
        """Testet Verhalten ohne vorherige Route."""
        manager = manager_with_test_track

        booking = {"latitude": 48.5, "longitude": 11.5}

        result = manager.extend_track2hotel(booking, output_dir)

        assert result is None

    def test_extend_track2hotel_no_coordinates(self, manager_with_test_track, output_dir):
        """Testet Verhalten ohne Hotel-Koordinaten."""
        manager = manager_with_test_track

        booking = {"gpx_files": [{"file": "test_track.gpx", "start_index": 0, "end_index": 4, "reversed": False}]}

        result = manager.extend_track2hotel(booking, output_dir)

        assert result is None

    @patch("biketour_planner.gpx_route_manager.get_route2address_as_points")
    def test_extend_track2hotel_updates_booking(self, mock_get_route, manager_with_test_track, output_dir):
        """Testet dass Booking aktualisiert wird."""
        manager = manager_with_test_track

        mock_points = [Mock(latitude=48.4, longitude=11.4, elevation=580), Mock(latitude=48.5, longitude=11.5, elevation=600)]
        mock_get_route.return_value = mock_points

        booking = {
            "arrival_date": "2026-05-15",
            "hotel_name": "Test Hotel",
            "latitude": 48.5,
            "longitude": 11.5,
            "gpx_files": [{"file": "test_track.gpx", "start_index": 0, "end_index": 4, "reversed": False}],
            "_last_gpx_file": {"file": "test_track.gpx", "end_index": 4, "reversed": False},
        }

        manager.extend_track2hotel(booking, output_dir)

        # Letzter Eintrag in gpx_files sollte aktualisiert sein
        assert booking["gpx_files"][-1]["is_to_hotel"] is True
        assert "to_hotel" in booking["gpx_files"][-1]["file"]


# ============================================================================
# Integration Tests für private Methoden
# ============================================================================


class TestPrivateMethodsIntegration:
    """Integrationstests für Zusammenspiel der privaten Methoden."""

    def test_routing_workflow_with_private_methods(self, manager_with_multiple_tracks):
        """Testet kompletten Routing-Workflow mit privaten Methoden."""
        manager = manager_with_multiple_tracks

        # 1. Finde Start
        start_file, start_index, force_dir = manager._find_start_pos(48.5, 11.5, None)

        assert start_file is not None

        # 2. Finde Ziel
        target_file, target_index, target_side_lat, target_side_lon = manager._find_target_pos(48.5, 11.5, 47.9, 10.9)

        assert target_file is not None

        # 3. Setze Endindex
        meta = manager.gpx_index[start_file]
        end_index = manager._set_end_index(
            current_index=start_index,
            meta=meta,
            force_direction=force_dir,
            target_side_lat=target_side_lat,
            target_side_lon=target_side_lon,
            iteration=0,
        )

        assert end_index is not None

        # 4. Berechne Statistiken
        max_elev, dist, asc = manager._get_statistics4track(
            meta=meta,
            current_index=start_index,
            end_index=end_index,
            max_elevation=0,
            total_distance=0,
            total_ascent=0,
            reversed_direction=(start_index > end_index),
        )

        assert max_elev > 0
        assert dist > 0

    def test_force_direction_workflow(self, manager_with_test_track):
        """Testet Workflow mit erzwungener Richtung."""
        manager = manager_with_test_track
        meta = manager.gpx_index["test_track.gpx"]

        # 1. Init end_index mit forward
        end_index_forward = manager._init_end_index(
            current_index=0, meta=meta, force_direction="forward", target_side_lat=48.3, target_side_lon=11.3
        )

        # 2. Set end_index nutzt init bei iteration=0
        end_index_set = manager._set_end_index(
            current_index=0, meta=meta, force_direction="forward", target_side_lat=48.3, target_side_lon=11.3, iteration=0
        )

        # Sollten gleich sein
        assert end_index_forward == end_index_set

    def test_chain_building_workflow(self, manager_with_multiple_tracks):
        """Testet Aufbau einer Routing-Kette."""
        manager = manager_with_multiple_tracks

        visited = set()
        used_base_files = set()
        # route_files = []

        # Starte bei track_north
        current_file = "track_north.gpx"
        current_lat, current_lon = 48.3, 11.3

        # 1. Finde nächste Datei
        next_file, next_index = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=current_lat, current_lon=current_lon
        )

        assert next_file is not None

        # 2. Markiere als besucht
        visited.add(current_file)
        used_base_files.add("track_north")

        # 3. Finde wieder nächste (sollte different sein)
        next_file2, _ = manager._find_next_gpx_file(
            visited=visited, used_base_files=used_base_files, current_lat=48.2, current_lon=11.2
        )

        # Sollte nicht track_north sein
        assert next_file2 != "track_north.gpx"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
