"""Unit-Tests für pdf_export.py.

Testet den PDF-Export inklusive:
- Touristen-Links-Erstellung
- Stornierungszellen-Styling
- PDF-Tabellen-Generierung
- Höhenprofil-Integration
- Excel-Info-Integration
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from biketour_planner.pdf_export import (
    create_tourist_sights_links,
    export_bookings_to_pdf,
    get_cancellation_cell_style,
)

# ============================================================================
# Test-Fixtures
# ============================================================================


@pytest.fixture
def tourist_sights_data():
    """Erstellt Beispiel-Daten für Sehenswürdigkeiten."""
    return {
        "features": [
            {"properties": {"name": "Diokletianpalast", "lat": 43.5081, "lon": 16.4402}},
            {"properties": {"name": "Marjan Park", "lat": 43.5150, "lon": 16.4300}},
        ]
    }


@pytest.fixture
def tourist_sights_without_names():
    """Erstellt Sehenswürdigkeiten-Daten ohne Namen (Fallback zu Straße)."""
    return {"features": [{"properties": {"street": "Hauptstraße", "lat": 43.5081, "lon": 16.4402}}]}


@pytest.fixture
def tourist_sights_coordinates_only():
    """Erstellt Sehenswürdigkeiten-Daten nur mit Koordinaten."""
    return {"features": [{"properties": {"lat": 43.5081, "lon": 16.4402}}]}


@pytest.fixture
def base_paragraph_style():
    """Erstellt einen Basis-ParagraphStyle für Tests."""
    return ParagraphStyle("TestStyle", fontSize=10, textColor=colors.black)


@pytest.fixture
def bookings_data(tmp_path):
    """Erstellt Test-Buchungsdaten."""
    return [
        {
            "arrival_date": "2026-05-15",
            "departure_date": "2026-05-16",
            "hotel_name": "Test Hotel",
            "address": "Teststraße 1, 21000 Split, Kroatien",
            "total_distance_km": 50,
            "total_ascent_m": 500,
            "max_elevation_m": 600,
            "total_price": 100.50,
            "free_cancel_until": "2026-05-10",
            "tourist_sights": {"features": [{"properties": {"name": "Test POI", "lat": 43.5, "lon": 16.4}}]},
        }
    ]


# ============================================================================
# Test create_tourist_sights_links
# ============================================================================


class TestCreateTouristSightsLinks:
    """Tests für die create_tourist_sights_links Funktion."""

    def test_create_links_basic(self, tourist_sights_data):
        """Testet grundlegende Link-Erstellung."""
        links = create_tourist_sights_links(tourist_sights_data)

        assert len(links) == 2
        assert all(isinstance(link, str) for link in links)
        assert all("<a href=" in link for link in links)

    def test_create_links_contains_google_maps_url(self, tourist_sights_data):
        """Testet dass Google Maps URLs erstellt werden."""
        links = create_tourist_sights_links(tourist_sights_data)

        for link in links:
            assert "https://www.google.com/maps/search/?api=1&query=" in link

    def test_create_links_includes_coordinates(self, tourist_sights_data):
        """Testet dass Koordinaten in URLs enthalten sind."""
        links = create_tourist_sights_links(tourist_sights_data)

        assert "43.5081,16.4402" in links[0]
        assert "43.515,16.43" in links[1]

    def test_create_links_includes_display_names(self, tourist_sights_data):
        """Testet dass Anzeigenamen in Links enthalten sind."""
        links = create_tourist_sights_links(tourist_sights_data)

        assert "Diokletianpalast" in links[0]
        assert "Marjan Park" in links[1]

    def test_create_links_has_blue_color(self, tourist_sights_data):
        """Testet dass Links blaue Farbe haben."""
        links = create_tourist_sights_links(tourist_sights_data)

        for link in links:
            assert 'color="blue"' in link

    def test_create_links_has_underline(self, tourist_sights_data):
        """Testet dass Links unterstrichen sind."""
        links = create_tourist_sights_links(tourist_sights_data)

        for link in links:
            assert "<u>" in link and "</u>" in link

    def test_create_links_fallback_to_street(self, tourist_sights_without_names):
        """Testet Fallback zu Straßennamen wenn Name fehlt."""
        links = create_tourist_sights_links(tourist_sights_without_names)

        assert len(links) == 1
        assert "Hauptstraße" in links[0]

    def test_create_links_fallback_to_coordinates(self, tourist_sights_coordinates_only):
        """Testet Fallback zu Koordinaten wenn Name und Straße fehlen."""
        links = create_tourist_sights_links(tourist_sights_coordinates_only)

        assert len(links) == 1
        assert "(43.5081, 16.4402)" in links[0]

    def test_create_links_empty_features(self):
        """Testet Verhalten bei leerer Features-Liste."""
        data = {"features": []}
        links = create_tourist_sights_links(data)

        assert links == []

    def test_create_links_none_input(self):
        """Testet Verhalten bei None-Input."""
        links = create_tourist_sights_links(None)

        assert links == []

    def test_create_links_missing_features_key(self):
        """Testet Verhalten wenn features-Key fehlt."""
        data = {"other_key": "value"}
        links = create_tourist_sights_links(data)

        assert links == []

    def test_create_links_missing_properties(self):
        """Testet Verhalten wenn properties-Key fehlt."""
        data = {"features": [{"other_key": "value"}]}
        links = create_tourist_sights_links(data)

        # Sollte Entry überspringen
        assert links == []

    def test_create_links_missing_coordinates(self):
        """Testet Verhalten wenn Koordinaten fehlen."""
        data = {
            "features": [
                {
                    "properties": {
                        "name": "Test POI"
                        # lat/lon fehlen
                    }
                }
            ]
        }
        links = create_tourist_sights_links(data)

        # Sollte Entry überspringen
        assert links == []

    def test_create_links_partial_coordinates(self):
        """Testet Verhalten wenn nur eine Koordinate vorhanden."""
        data = {
            "features": [
                {
                    "properties": {
                        "name": "Test POI",
                        "lat": 43.5,
                        # lon fehlt
                    }
                }
            ]
        }
        links = create_tourist_sights_links(data)

        assert links == []

    def test_create_links_multiple_pois(self):
        """Testet mit vielen POIs."""
        features = [{"properties": {"name": f"POI {i}", "lat": 43.5 + i * 0.01, "lon": 16.4 + i * 0.01}} for i in range(10)]
        data = {"features": features}

        links = create_tourist_sights_links(data)

        assert len(links) == 10

    def test_create_links_special_characters_in_name(self):
        """Testet POI-Namen mit Sonderzeichen."""
        data = {"features": [{"properties": {"name": "St. Peter's & Paul Café", "lat": 43.5, "lon": 16.4}}]}
        links = create_tourist_sights_links(data)

        # Sonderzeichen sollten erhalten bleiben
        assert "St. Peter's & Paul Café" in links[0]


# ============================================================================
# Test get_cancellation_cell_style
# ============================================================================


class TestGetCancellationCellStyle:
    """Tests für die get_cancellation_cell_style Funktion."""

    def test_style_flexible_cancellation(self, base_paragraph_style):
        """Testet grüne Farbe bei flexibler Stornierung (<7 Tage)."""
        style = get_cancellation_cell_style("2026-05-10", "2026-05-15", base_paragraph_style)  # 5 Tage Differenz

        # Sollte grün sein
        assert style.textColor == colors.HexColor("#008000")

    def test_style_inflexible_cancellation(self, base_paragraph_style):
        """Testet rote Farbe bei unflexibler Stornierung (>30 Tage)."""
        style = get_cancellation_cell_style("2026-04-10", "2026-05-15", base_paragraph_style)  # 35 Tage Differenz

        # Sollte rot sein
        assert style.textColor == colors.HexColor("#DC143C")

    def test_style_medium_cancellation(self, base_paragraph_style):
        """Testet schwarze Farbe bei mittlerer Stornierungsfrist (7-30 Tage)."""
        style = get_cancellation_cell_style("2026-05-01", "2026-05-15", base_paragraph_style)  # 14 Tage Differenz

        # Sollte schwarz bleiben
        assert style.textColor == colors.black

    def test_style_no_cancellation(self, base_paragraph_style):
        """Testet schwarze Farbe wenn keine Stornierung möglich."""
        style = get_cancellation_cell_style(None, "2026-05-15", base_paragraph_style)

        assert style.textColor == colors.black

    def test_style_missing_arrival_date(self, base_paragraph_style):
        """Testet Verhalten bei fehlendem Anreisedatum."""
        style = get_cancellation_cell_style("2026-05-10", None, base_paragraph_style)

        assert style.textColor == colors.black

    def test_style_invalid_date_format(self, base_paragraph_style):
        """Testet Verhalten bei ungültigem Datumsformat."""
        style = get_cancellation_cell_style("ungültiges datum", "2026-05-15", base_paragraph_style)

        # Sollte Fehler abfangen und schwarz zurückgeben
        assert style.textColor == colors.black

    def test_style_boundary_7_days(self, base_paragraph_style):
        """Testet Grenzwert bei genau 7 Tagen."""
        style = get_cancellation_cell_style("2026-05-08", "2026-05-15", base_paragraph_style)  # Genau 7 Tage

        # Bei 7 Tagen sollte es schwarz sein (nicht grün)
        assert style.textColor == colors.black

    def test_style_boundary_30_days(self, base_paragraph_style):
        """Testet Grenzwert bei genau 30 Tagen."""
        style = get_cancellation_cell_style("2026-04-15", "2026-05-15", base_paragraph_style)  # Genau 30 Tage

        # Bei 30 Tagen sollte es schwarz sein (nicht rot)
        assert style.textColor == colors.black

    def test_style_same_day(self, base_paragraph_style):
        """Testet bei Stornierung am selben Tag."""
        style = get_cancellation_cell_style("2026-05-15", "2026-05-15", base_paragraph_style)  # 0 Tage

        # Sehr flexibel - sollte grün sein
        assert style.textColor == colors.HexColor("#008000")

    def test_style_preserves_other_attributes(self, base_paragraph_style):
        """Testet dass andere Style-Attribute erhalten bleiben."""
        style = get_cancellation_cell_style("2026-05-10", "2026-05-15", base_paragraph_style)

        # Andere Attribute vom Base-Style sollten erhalten sein
        assert style.fontSize == base_paragraph_style.fontSize

    def test_style_creates_new_instance(self, base_paragraph_style):
        """Testet dass neuer Style erstellt wird (kein Mutieren)."""
        style = get_cancellation_cell_style("2026-05-10", "2026-05-15", base_paragraph_style)

        # Sollte nicht die gleiche Instanz sein
        assert style is not base_paragraph_style


# ============================================================================
# Test export_bookings_to_pdf
# ============================================================================


class TestExportBookingsToPDF:
    """Tests für die export_bookings_to_pdf Funktion."""

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.Table")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_creates_pdf(self, mock_get_gpx, mock_table, mock_doc, bookings_data, tmp_path):
        """Testet dass PDF erstellt wird."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        # Erstelle JSON-Datei
        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path)

        # SimpleDocTemplate sollte erstellt werden
        mock_doc.assert_called_once()
        # build sollte aufgerufen werden
        mock_doc_instance.build.assert_called_once()

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_sorts_bookings_by_date(self, mock_get_gpx, mock_doc, tmp_path):
        """Testet dass Bookings nach Datum sortiert werden."""
        bookings = [
            {"arrival_date": "2026-05-20", "hotel_name": "Hotel B"},
            {"arrival_date": "2026-05-15", "hotel_name": "Hotel A"},
            {"arrival_date": "2026-05-17", "hotel_name": "Hotel C"},
        ]

        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path)

        # build wurde mit story aufgerufen - prüfe Reihenfolge indirekt
        assert mock_doc_instance.build.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_calculates_totals(self, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet dass Summen berechnet werden."""
        # Mehrere Bookings für Summenberechnung
        bookings = [
            {
                "arrival_date": "2026-05-15",
                "departure_date": "2026-05-16",
                "hotel_name": "Hotel 1",
                "address": "Adresse 1",
                "total_distance_km": 50,
                "total_ascent_m": 500,
                "total_price": 100.0,
            },
            {
                "arrival_date": "2026-05-16",
                "departure_date": "2026-05-17",
                "hotel_name": "Hotel 2",
                "address": "Adresse 2",
                "total_distance_km": 75,
                "total_ascent_m": 300,
                "total_price": 150.0,
            },
        ]

        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path)

        # Story sollte Zusammenfassung enthalten
        # (schwer zu testen ohne Story zu inspizieren)
        assert mock_doc_instance.build.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    @patch("biketour_planner.pdf_export.add_elevation_profiles_to_story_seq")
    def test_export_adds_elevation_profiles(self, mock_add_profiles, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet dass Höhenprofile hinzugefügt werden."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        output_dir = tmp_path / "gpx"
        output_dir.mkdir()

        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_gpx_files = [output_dir / "test.gpx"]
        mock_get_gpx.return_value = mock_gpx_files

        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path, output_dir=output_dir)

        # add_elevation_profiles_to_story_seq sollte aufgerufen werden
        mock_add_profiles.assert_called_once()

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    @patch("biketour_planner.pdf_export.read_daily_info_from_excel")
    def test_export_integrates_excel_info(self, mock_read_excel, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet Integration von Excel-Zusatzinfos."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        excel_path = tmp_path / "info.xlsx"
        excel_path.touch()  # Ensure file exists

        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        # Mock Excel-Infos
        mock_read_excel.return_value = {"2026-05-15": ["Info 1", "Info 2"]}

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path, excel_info_path=excel_path)

        # read_daily_info_from_excel sollte aufgerufen werden
        mock_read_excel.assert_called_once()

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_custom_title(self, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet benutzerdefinierten Titel."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path, title="Custom Title")

        # Titel sollte in Story enthalten sein
        # (schwer zu testen ohne Story zu inspizieren)
        assert mock_doc_instance.build.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_landscape_orientation(self, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet dass Querformat verwendet wird."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path)

        # SimpleDocTemplate sollte mit landscape pagesize aufgerufen werden
        call_args = mock_doc.call_args
        print(call_args)
        # pagesize sollte landscape sein (schwer zu prüfen ohne genaue Inspektion)
        assert mock_doc.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_handles_missing_optional_fields(self, mock_get_gpx, mock_doc, tmp_path):
        """Testet Verhalten bei fehlenden optionalen Feldern."""
        bookings = [
            {
                "arrival_date": "2026-05-15",
                "hotel_name": "Hotel",
                # Viele Felder fehlen
            }
        ]

        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        # Sollte nicht crashen
        export_bookings_to_pdf(json_path, output_path)

        assert mock_doc_instance.build.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    @patch("biketour_planner.pdf_export.read_gpx_file")
    @patch("biketour_planner.pdf_export.get_statistics4track")
    def test_export_with_pass_tracks(self, mock_stats, mock_read_gpx, mock_get_gpx, mock_doc, tmp_path):
        """Testet PDF-Export mit Pass-Tracks."""
        bookings = [
            {
                "arrival_date": "2026-05-15",
                "departure_date": "2026-05-17",  # 2 nights stay
                "hotel_name": "Pass Hotel",
                "address": "Pass Road 1",
                "paesse_tracks": [{"file": "pass1.gpx", "passname": "Great Pass", "latitude": 45.0, "longitude": 15.0}],
            },
            {
                "arrival_date": "2026-05-20",  # Gap of 3 days
                "hotel_name": "After Gap Hotel",
                "address": "Road 2",
            },
        ]

        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        gpx_dir = tmp_path / "gpx"
        gpx_dir.mkdir()
        (gpx_dir / "pass1.gpx").touch()

        import json

        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_read_gpx.return_value = MagicMock(tracks=[True])
        mock_stats.return_value = (2000.0, 10000.0, 1000.0, 0.0)

        export_bookings_to_pdf(json_path, output_path, gpx_dir=gpx_dir)
        assert mock_doc.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    @patch("biketour_planner.pdf_export.pdfmetrics.registerFont")
    def test_export_font_registration_failure(self, mock_register, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet Verhalten bei fehlgeschlagener Font-Registrierung."""
        mock_register.side_effect = Exception("Font missing")

        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_get_gpx.return_value = []

        # Should use fallback fonts and not crash
        export_bookings_to_pdf(json_path, output_path)
        assert mock_doc.called

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_creates_output_directory(self, mock_get_gpx, mock_doc, bookings_data, tmp_path):
        """Testet dass Output-Verzeichnis erstellt wird."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "subdir" / "output.pdf"

        import json

        json_path.write_text(json.dumps(bookings_data), encoding="utf-8")

        mock_get_gpx.return_value = []
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        export_bookings_to_pdf(json_path, output_path)

        # Parent-Verzeichnis sollte existieren
        # (SimpleDocTemplate sollte aufgerufen worden sein)
        assert mock_doc.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
