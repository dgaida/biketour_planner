"""Unit-Tests für elevation_profiles.py.

Testet die Höhenprofil-Generierung inklusive:
- Extraktion von Distanz und Höhendaten aus GPX-Dateien
- Berechnung von Steigungen
- Farbcodierung basierend auf Steigung
- Erstellung von Höhenprofil-Plots
- Hinzufügen von Profilen zu PDF-Stories
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from reportlab.lib.styles import ParagraphStyle

from biketour_planner.elevation_profiles import (
    add_elevation_profiles_to_story,
    calculate_gradient,
    create_elevation_profile_plot,
    extract_elevation_profile,
    get_color_for_gradient,
    get_merged_gpx_files_from_bookings,
)

# ============================================================================
# Test-Fixtures
# ============================================================================


@pytest.fixture
def simple_gpx_file(tmp_path):
    """Erstellt eine einfache Test-GPX-Datei mit Höhenprofil."""
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.01" lon="11.01"><ele>520</ele></trkpt>
      <trkpt lat="48.02" lon="11.02"><ele>510</ele></trkpt>
      <trkpt lat="48.03" lon="11.03"><ele>540</ele></trkpt>
      <trkpt lat="48.04" lon="11.04"><ele>550</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

    gpx_file = tmp_path / "test_profile.gpx"
    gpx_file.write_text(gpx_content, encoding="utf-8")
    return gpx_file


@pytest.fixture
def gpx_without_elevation(tmp_path):
    """Erstellt GPX-Datei ohne Höheninformationen."""
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
      <trkpt lat="48.01" lon="11.01"/>
      <trkpt lat="48.02" lon="11.02"/>
    </trkseg>
  </trk>
</gpx>"""

    gpx_file = tmp_path / "no_elevation.gpx"
    gpx_file.write_text(gpx_content, encoding="utf-8")
    return gpx_file


@pytest.fixture
def booking_with_stats():
    """Erstellt Booking-Dictionary mit Statistiken."""
    return {
        "arrival_date": "2026-05-15",
        "hotel_name": "Test Hotel",
        "total_ascent_m": 250,
        "total_descent_m": 100,
    }


# ============================================================================
# Test extract_elevation_profile
# ============================================================================


class TestExtractElevationProfile:
    """Tests für die extract_elevation_profile Funktion."""

    def test_extract_profile_basic(self, simple_gpx_file):
        """Testet grundlegende Profil-Extraktion."""
        distances, elevations = extract_elevation_profile(simple_gpx_file)

        assert len(distances) == len(elevations)
        assert len(elevations) == 5
        assert distances[0] == 0.0
        assert distances[-1] > 0
        assert elevations[0] == 500
        assert elevations[-1] == 550

    def test_extract_profile_cumulative_distance(self, simple_gpx_file):
        """Testet dass Distanz kumulativ ist."""
        distances, elevations = extract_elevation_profile(simple_gpx_file)

        # Distanzen sollten monoton steigend sein
        for i in range(1, len(distances)):
            assert distances[i] > distances[i - 1]

    def test_extract_profile_converts_to_km(self, simple_gpx_file):
        """Testet dass Distanz in Kilometern ist."""
        distances, elevations = extract_elevation_profile(simple_gpx_file)

        # Distanz zwischen Punkten ca. 1.5km pro 0.01 Grad
        # 4 Segmente * ~1.5km = ~6km
        assert distances[-1] > 5
        assert distances[-1] < 10

    def test_extract_profile_no_elevation_data(self, gpx_without_elevation):
        """Testet Verhalten ohne Höhendaten."""
        with pytest.raises(ValueError, match="Keine Höhendaten"):
            extract_elevation_profile(gpx_without_elevation)

    def test_extract_profile_invalid_file(self, tmp_path):
        """Testet Verhalten bei ungültiger GPX-Datei."""
        invalid_file = tmp_path / "invalid.gpx"
        invalid_file.write_text("nicht gpx", encoding="utf-8")

        with pytest.raises(ValueError):
            extract_elevation_profile(invalid_file)

    def test_extract_profile_empty_track(self, tmp_path):
        """Testet Verhalten bei leerem Track."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "empty.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        with pytest.raises(ValueError, match="Keine Höhendaten"):
            extract_elevation_profile(gpx_file)

    def test_extract_profile_returns_numpy_arrays(self, simple_gpx_file):
        """Testet dass NumPy-Arrays zurückgegeben werden."""
        distances, elevations = extract_elevation_profile(simple_gpx_file)

        assert isinstance(distances, np.ndarray)
        assert isinstance(elevations, np.ndarray)

    def test_extract_profile_filters_none_elevations(self, tmp_path):
        """Testet dass None-Höhenwerte gefiltert werden."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.01" lon="11.01"/>
      <trkpt lat="48.02" lon="11.02"><ele>520</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "partial_elevation.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        distances, elevations = extract_elevation_profile(gpx_file)

        # Sollte nur Punkte mit Elevation enthalten
        assert len(elevations) == 2
        assert 500 in elevations
        assert 520 in elevations


# ============================================================================
# Test calculate_gradient
# ============================================================================


class TestCalculateGradient:
    """Tests für die calculate_gradient Funktion."""

    def test_calculate_gradient_flat(self):
        """Testet Steigungsberechnung auf flacher Strecke."""
        distances = np.array([0, 1, 2, 3])
        elevations = np.array([100, 100, 100, 100])

        gradients = calculate_gradient(distances, elevations)

        assert len(gradients) == len(elevations)
        assert all(g == 0 for g in gradients)

    def test_calculate_gradient_constant_ascent(self):
        """Testet Steigungsberechnung bei konstantem Anstieg."""
        distances = np.array([0, 1, 2, 3])  # km
        elevations = np.array([0, 100, 200, 300])  # m

        gradients = calculate_gradient(distances, elevations)

        # 100m auf 1000m = 10% Steigung
        for i in range(1, len(gradients)):
            assert gradients[i] == pytest.approx(10.0, abs=0.1)

    def test_calculate_gradient_constant_descent(self):
        """Testet Steigungsberechnung bei konstantem Abstieg."""
        distances = np.array([0, 1, 2, 3])
        elevations = np.array([300, 200, 100, 0])

        gradients = calculate_gradient(distances, elevations)

        # -100m auf 1000m = -10%
        for i in range(1, len(gradients)):
            assert gradients[i] == pytest.approx(-10.0, abs=0.1)

    def test_calculate_gradient_mixed(self):
        """Testet Steigungsberechnung bei Wechsel von Anstieg/Abstieg."""
        distances = np.array([0, 1, 2, 3])
        elevations = np.array([0, 100, 50, 150])

        gradients = calculate_gradient(distances, elevations)

        assert gradients[1] > 0  # Anstieg
        assert gradients[2] < 0  # Abstieg
        assert gradients[3] > 0  # Anstieg

    def test_calculate_gradient_first_element_zero(self):
        """Testet dass erstes Element Null ist."""
        distances = np.array([0, 1, 2])
        elevations = np.array([0, 100, 200])

        gradients = calculate_gradient(distances, elevations)

        assert gradients[0] == 0

    def test_calculate_gradient_zero_distance_segment(self):
        """Testet Verhalten bei null Distanz zwischen Punkten."""
        distances = np.array([0, 1, 1, 2])  # Gleiche Distanz für Index 1 und 2
        elevations = np.array([0, 100, 150, 200])

        gradients = calculate_gradient(distances, elevations)

        # Bei null Distanz sollte Steigung 0 sein
        assert gradients[2] == 0

    def test_calculate_gradient_steep_climb(self):
        """Testet sehr steile Steigungen (>20%)."""
        distances = np.array([0, 1])
        elevations = np.array([0, 300])

        gradients = calculate_gradient(distances, elevations)

        assert gradients[1] == pytest.approx(30.0, abs=0.1)

    def test_calculate_gradient_returns_same_length(self):
        """Testet dass Output gleiche Länge wie Input hat."""
        distances = np.array([0, 1, 2, 3, 4, 5])
        elevations = np.array([0, 10, 20, 30, 40, 50])

        gradients = calculate_gradient(distances, elevations)

        assert len(gradients) == len(distances)


# ============================================================================
# Test get_color_for_gradient
# ============================================================================


class TestGetColorForGradient:
    """Tests für die get_color_for_gradient Funktion."""

    def test_color_flat_terrain(self):
        """Testet Farbe für flaches Gelände."""
        color = get_color_for_gradient(0)
        assert color in ["#ffcccc", "#ccffcc"]  # Hellrot oder Hellgrün

    def test_color_gentle_ascent(self):
        """Testet Farbe für sanften Anstieg (0-3%)."""
        color = get_color_for_gradient(2)
        assert color == "#ffcccc"  # Hellrot

    def test_color_moderate_ascent(self):
        """Testet Farbe für moderaten Anstieg (3-6%)."""
        color = get_color_for_gradient(5)
        assert color == "#ff6666"  # Mittelrot

    def test_color_steep_ascent(self):
        """Testet Farbe für steilen Anstieg (6-10%)."""
        color = get_color_for_gradient(8)
        assert color == "#ff0000"  # Rot

    def test_color_very_steep_ascent(self):
        """Testet Farbe für sehr steilen Anstieg (>10%)."""
        color = get_color_for_gradient(15)
        assert color == "#cc0000"  # Dunkelrot

    def test_color_gentle_descent(self):
        """Testet Farbe für sanften Abstieg (0 bis -3%)."""
        color = get_color_for_gradient(-2)
        assert color == "#ccffcc"  # Hellgrün

    def test_color_moderate_descent(self):
        """Testet Farbe für moderaten Abstieg (-3 bis -6%)."""
        color = get_color_for_gradient(-5)
        assert color == "#66ff66"  # Mittelgrün

    def test_color_steep_descent(self):
        """Testet Farbe für steilen Abstieg (-6 bis -10%)."""
        color = get_color_for_gradient(-8)
        assert color == "#00ff00"  # Grün

    def test_color_very_steep_descent(self):
        """Testet Farbe für sehr steilen Abstieg (< -10%)."""
        color = get_color_for_gradient(-15)
        assert color == "#00cc00"  # Dunkelgrün

    def test_color_boundary_values(self):
        """Testet Grenzwerte zwischen Farbkategorien."""
        assert get_color_for_gradient(3.0) == "#ff6666"  # Genau 3%
        assert get_color_for_gradient(6.0) == "#ff0000"  # Genau 6%
        assert get_color_for_gradient(10.0) == "#cc0000"  # Genau 10%

    def test_color_returns_hex_string(self):
        """Testet dass Hex-String zurückgegeben wird."""
        color = get_color_for_gradient(5)
        assert color.startswith("#")
        assert len(color) == 7


# ============================================================================
# Test create_elevation_profile_plot
# ============================================================================


class TestCreateElevationProfilePlot:
    """Tests für die create_elevation_profile_plot Funktion."""

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_basic(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet grundlegende Plot-Erstellung."""
        # Mock figure und axes
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        img_buffer = create_elevation_profile_plot(simple_gpx_file, booking_with_stats)

        assert isinstance(img_buffer, BytesIO)
        mock_plt.subplots.assert_called_once()
        mock_plt.savefig.assert_called_once()
        mock_plt.close.assert_called_once()

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_with_pass_track(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet Plot-Erstellung mit Pass-Track-Statistiken."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        pass_track = {
            "total_ascent_m": 500,
            "total_descent_m": 200,
        }

        img_buffer = create_elevation_profile_plot(simple_gpx_file, booking_with_stats, pass_track=pass_track)

        assert isinstance(img_buffer, BytesIO)

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_custom_title(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet Plot mit benutzerdefiniertem Titel."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats, title="Custom Title")

        # Prüfe dass set_title aufgerufen wurde
        mock_ax.set_title.assert_called_once()
        call_args = mock_ax.set_title.call_args
        assert "Custom Title" in call_args[0][0]

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_custom_figsize(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet Plot mit benutzerdefinierter Größe."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats, figsize=(16, 6))

        call_args = mock_plt.subplots.call_args
        assert call_args[1]["figsize"] == (16, 6)

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_draws_colored_segments(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet dass farbige Segmente gezeichnet werden."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats)

        # fill_between sollte für farbige Segmente aufgerufen werden
        assert mock_ax.fill_between.call_count > 0

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_draws_contour_line(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet dass schwarze Konturlinie gezeichnet wird."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats)

        # plot sollte für Konturlinie aufgerufen werden
        mock_ax.plot.assert_called()

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_sets_labels(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet dass Achsenbeschriftungen gesetzt werden."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats)

        mock_ax.set_xlabel.assert_called_once()
        mock_ax.set_ylabel.assert_called_once()
        mock_ax.set_title.assert_called_once()

    @patch("biketour_planner.elevation_profiles.plt")
    def test_create_plot_adds_statistics_text(self, mock_plt, simple_gpx_file, booking_with_stats):
        """Testet dass Statistik-Text hinzugefügt wird."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        mock_plt.savefig.side_effect = lambda buffer, **kwargs: buffer.write(b"fake data")

        create_elevation_profile_plot(simple_gpx_file, booking_with_stats)

        # text sollte für Statistiken aufgerufen werden
        mock_ax.text.assert_called()

    def test_create_plot_invalid_gpx(self, tmp_path, booking_with_stats):
        """Testet Verhalten bei ungültiger GPX-Datei."""
        invalid_file = tmp_path / "invalid.gpx"
        invalid_file.write_text("nicht gpx", encoding="utf-8")

        with pytest.raises(ValueError, match="Konnte invalid.gpx nicht lesen"):
            create_elevation_profile_plot(invalid_file, booking_with_stats)


# ============================================================================
# Test add_elevation_profiles_to_story
# ============================================================================


class TestAddElevationProfilesToStory:
    """Tests für die add_elevation_profiles_to_story Funktion."""

    @patch("biketour_planner.elevation_profiles.Paragraph")
    @patch("biketour_planner.elevation_profiles.PageBreak")
    @patch("biketour_planner.elevation_profiles.Image")
    @patch("biketour_planner.elevation_profiles.create_elevation_profile_plot")
    def test_add_profiles_basic(self, mock_create_plot, mock_image, mock_pb, mock_para, simple_gpx_file, tmp_path):
        """Testet grundlegendes Hinzufügen von Profilen."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock Plot-Erstellung - return new buffer each time
        mock_create_plot.side_effect = lambda *args, **kwargs: BytesIO(b"fake image data")

        story = []
        gpx_files = [simple_gpx_file]
        bookings = [{"gpx_track_final": simple_gpx_file.name}]

        title_style = ParagraphStyle("Title")

        add_elevation_profiles_to_story(story, gpx_files, bookings, output_dir, title_style)

        # Story sollte Elemente enthalten
        assert len(story) > 0

    @patch("biketour_planner.elevation_profiles.Paragraph")
    @patch("biketour_planner.elevation_profiles.PageBreak")
    @patch("biketour_planner.elevation_profiles.Image")
    @patch("biketour_planner.elevation_profiles.create_elevation_profile_plot")
    def test_add_profiles_multiple_files(self, mock_create_plot, mock_image, mock_pb, mock_para, tmp_path):
        """Testet Hinzufügen mehrerer Profile."""
        # Erstelle mehrere GPX-Dateien
        gpx_files = []
        for i in range(3):
            gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.{i}" lon="11.{i}"><ele>{500 + i * 10}</ele></trkpt>
      <trkpt lat="48.{i + 1}" lon="11.{i + 1}"><ele>{510 + i * 10}</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
            gpx_file = tmp_path / f"route_{i}.gpx"
            gpx_file.write_text(gpx_content, encoding="utf-8")
            gpx_files.append(gpx_file)

        mock_create_plot.side_effect = lambda *args, **kwargs: BytesIO(b"fake image")

        story = []
        bookings = [{"gpx_track_final": f.name} for f in gpx_files]
        title_style = ParagraphStyle("Title")

        add_elevation_profiles_to_story(story, gpx_files, bookings, tmp_path, title_style)

        # Sollte für jede Datei create_elevation_profile_plot aufrufen
        assert mock_create_plot.call_count >= 3

    def test_add_profiles_empty_files_list(self, tmp_path):
        """Testet Verhalten bei leerer Dateiliste."""
        story = []
        title_style = ParagraphStyle("Title")

        add_elevation_profiles_to_story(story, [], [], tmp_path, title_style)

        # Story sollte leer bleiben oder nur PageBreak enthalten
        assert len(story) <= 1

    @patch("biketour_planner.elevation_profiles.Paragraph")
    @patch("biketour_planner.elevation_profiles.PageBreak")
    @patch("biketour_planner.elevation_profiles.Image")
    @patch("biketour_planner.elevation_profiles.create_elevation_profile_plot")
    def test_add_profiles_with_pass_tracks(self, mock_create_plot, mock_image, mock_pb, mock_para, simple_gpx_file, tmp_path):
        """Testet Hinzufügen mit Pass-Tracks."""
        mock_create_plot.side_effect = lambda *args, **kwargs: BytesIO(b"fake image")

        # Booking mit Pass-Tracks
        bookings = [
            {
                "gpx_track_final": simple_gpx_file.name,
                "paesse_tracks": [
                    {
                        "file": "pass.gpx",
                        "passname": "Test Pass",
                        "total_ascent_m": 300,
                        "total_descent_m": 50,
                    }
                ],
            }
        ]

        # Erstelle Pass-Datei
        pass_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.5" lon="11.5"><ele>600</ele></trkpt>
      <trkpt lat="48.6" lon="11.6"><ele>700</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
        pass_file = tmp_path / "pass.gpx"
        pass_file.write_text(pass_content, encoding="utf-8")

        story = []
        title_style = ParagraphStyle("Title")

        add_elevation_profiles_to_story(story, [simple_gpx_file], bookings, tmp_path, title_style)

        # Sollte sowohl Haupt-Track als auch Pass-Track erstellen
        assert mock_create_plot.call_count >= 2

    @patch("biketour_planner.elevation_profiles.Paragraph")
    @patch("biketour_planner.elevation_profiles.PageBreak")
    @patch("biketour_planner.elevation_profiles.create_elevation_profile_plot")
    def test_add_profiles_handles_errors(self, mock_create_plot, mock_pagebreak, mock_paragraph, simple_gpx_file, tmp_path):
        """Testet Fehlerbehandlung bei Plot-Erstellung."""
        # Simuliere Fehler bei Plot-Erstellung
        mock_create_plot.side_effect = Exception("Plot error")

        story = []
        bookings = [{"gpx_track_final": simple_gpx_file.name}]
        title_style = ParagraphStyle("Title")

        # Sollte nicht crashen
        add_elevation_profiles_to_story(story, [simple_gpx_file], bookings, tmp_path, title_style)

        # Story sollte trotzdem Elemente enthalten (z.B. PageBreak, Heading)
        assert len(story) > 0


# ============================================================================
# Test get_merged_gpx_files_from_bookings
# ============================================================================


class TestGetMergedGPXFilesFromBookings:
    """Tests für die get_merged_gpx_files_from_bookings Funktion."""

    def test_get_merged_files_basic(self, tmp_path):
        """Testet grundlegende Extraktion von GPX-Dateien."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Erstelle GPX-Dateien
        for i in range(3):
            gpx_file = output_dir / f"day{i}.gpx"
            gpx_file.write_text("<gpx></gpx>", encoding="utf-8")

        bookings = [
            {"gpx_track_final": "day0.gpx"},
            {"gpx_track_final": "day1.gpx"},
            {"gpx_track_final": "day2.gpx"},
        ]

        files = get_merged_gpx_files_from_bookings(bookings, output_dir)

        assert len(files) == 3
        assert all(isinstance(f, Path) for f in files)
        assert all(f.exists() for f in files)

    def test_get_merged_files_missing_files(self, tmp_path):
        """Testet Verhalten wenn Dateien nicht existieren."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bookings = [
            {"gpx_track_final": "non_existent.gpx"},
        ]

        files = get_merged_gpx_files_from_bookings(bookings, output_dir)

        # Sollte keine nicht-existierenden Dateien zurückgeben
        assert len(files) == 0

    def test_get_merged_files_empty_bookings(self, tmp_path):
        """Testet Verhalten bei leeren Bookings."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        files = get_merged_gpx_files_from_bookings([], output_dir)

        assert len(files) == 0

    def test_get_merged_files_bookings_without_gpx_track(self, tmp_path):
        """Testet Verhalten bei Bookings ohne gpx_track_final."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bookings = [
            {"hotel_name": "Test Hotel"},
            {"arrival_date": "2026-05-15"},
        ]

        files = get_merged_gpx_files_from_bookings(bookings, output_dir)

        assert len(files) == 0

    def test_get_merged_files_mixed_existing_and_missing(self, tmp_path):
        """Testet gemischte existierende und fehlende Dateien."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Nur eine Datei erstellen
        (output_dir / "exists.gpx").write_text("<gpx></gpx>", encoding="utf-8")

        bookings = [
            {"gpx_track_final": "exists.gpx"},
            {"gpx_track_final": "missing.gpx"},
        ]

        files = get_merged_gpx_files_from_bookings(bookings, output_dir)

        assert len(files) == 1
        assert files[0].name == "exists.gpx"

    def test_get_merged_files_preserves_order(self, tmp_path):
        """Testet dass Reihenfolge erhalten bleibt."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Erstelle Dateien in umgekehrter Reihenfolge
        for i in [2, 1, 0]:
            (output_dir / f"day{i}.gpx").write_text("<gpx></gpx>", encoding="utf-8")

        bookings = [
            {"gpx_track_final": "day0.gpx"},
            {"gpx_track_final": "day1.gpx"},
            {"gpx_track_final": "day2.gpx"},
        ]

        files = get_merged_gpx_files_from_bookings(bookings, output_dir)

        assert [f.name for f in files] == ["day0.gpx", "day1.gpx", "day2.gpx"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
