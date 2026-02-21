import json
from unittest.mock import patch

from biketour_planner.pdf_export import export_bookings_to_pdf


class TestPDFExportExcelInfo:
    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.Table")
    @patch("biketour_planner.pdf_export.read_daily_info_from_excel")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_integrates_excel_info_for_all_days(self, mock_get_gpx, mock_read_excel, mock_table, mock_doc, tmp_path):
        """Testet dass Excel-Infos für Anreise, Zwischentage und Abreise übernommen werden."""
        # Setup
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        excel_path = tmp_path / "info.xlsx"
        excel_path.touch()

        # Buchung für 2 Nächte -> 3 Tage im PDF (Anreise, Zwischentag, Checkout)
        bookings = [
            {
                "arrival_date": "2026-05-15",
                "departure_date": "2026-05-17",
                "hotel_name": "Test Hotel",
                "address": "Split, Croatia",
            }
        ]
        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        # Mock Excel-Infos für alle 3 Tage
        mock_read_excel.return_value = {
            "2026-05-15": ["Arrival Info"],
            "2026-05-16": ["Intermediate Info"],
            "2026-05-17": ["Checkout Info"],
        }

        mock_get_gpx.return_value = []

        export_bookings_to_pdf(json_path, output_path, excel_info_path=excel_path)

        # Prüfe Tabellendaten
        assert mock_table.called
        table_data = mock_table.call_args[0][0]

        # Header + 3 Zeilen (15th Arrival, 16th Stay, 17th Checkout)
        assert len(table_data) == 4

        # Zeile 1: Anreisetag (index 1)
        assert "Arrival Info" in table_data[1][8].text

        # Zeile 2: Zwischentag (index 2) - JETZT IN DER SCHLEIFE
        assert "Intermediate Info" in table_data[2][8].text
        assert "Split" in table_data[2][2].text  # Von (City)
        assert "Test Hotel" in table_data[2][5].text  # Unterkunft

        # Zeile 3: Checkout-Tag (index 3)
        assert "Checkout Info" in table_data[3][8].text
        assert "Checkout" in table_data[3][3].text  # Nach

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.Table")
    @patch("biketour_planner.pdf_export.read_daily_info_from_excel")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_export_integrates_excel_info_for_intermediate_gap(
        self, mock_get_gpx, mock_read_excel, mock_table, mock_doc, tmp_path
    ):
        """Testet Excel-Infos für Lücken zwischen Buchungen."""
        # Setup
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        excel_path = tmp_path / "info.xlsx"
        excel_path.touch()

        # Zwei Buchungen mit Lücke
        bookings = [
            {
                "arrival_date": "2026-05-15",
                "departure_date": "2026-05-16",
                "hotel_name": "Hotel 1",
                "address": "City 1",
            },
            {
                "arrival_date": "2026-05-18",
                "departure_date": "2026-05-19",
                "hotel_name": "Hotel 2",
                "address": "City 2",
            },
        ]
        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        # Info für den Tag in der Lücke (2026-05-16 bis 2026-05-18, also 2026-05-16 und 2026-05-17)
        mock_read_excel.return_value = {"2026-05-16": ["Gap Day 16"], "2026-05-17": ["Gap Day 17"]}

        mock_get_gpx.return_value = []

        export_bookings_to_pdf(json_path, output_path, excel_info_path=excel_path)

        table_data = mock_table.call_args[0][0]

        # Zeilen:
        # 0: Header
        # 1: 15th (B1 Arrival)
        # 2: 16th (Gap/Checkout B1)
        # 3: 17th (Gap)
        # 4: 18th (B2 Arrival)
        # 5: 19th (B2 Checkout)

        assert "Gap Day 16" in table_data[2][8].text
        assert "Gap Day 17" in table_data[3][8].text

    @patch("biketour_planner.pdf_export.SimpleDocTemplate")
    @patch("biketour_planner.pdf_export.Table")
    @patch("biketour_planner.pdf_export.read_daily_info_from_excel")
    @patch("biketour_planner.pdf_export.get_merged_gpx_files_from_bookings")
    def test_multi_night_stays_for_multiple_bookings(self, mock_get_gpx, mock_read_excel, mock_table, mock_doc, tmp_path):
        """Testet mehrere Nächte in verschiedenen Hotels."""
        json_path = tmp_path / "bookings.json"
        output_path = tmp_path / "output.pdf"
        excel_path = tmp_path / "info.xlsx"
        excel_path.touch()

        bookings = [
            {
                "arrival_date": "2026-05-15",
                "departure_date": "2026-05-17",  # 2 nights
                "hotel_name": "Hotel A",
                "address": "City A",
            },
            {
                "arrival_date": "2026-05-17",
                "departure_date": "2026-05-19",  # 2 nights
                "hotel_name": "Hotel B",
                "address": "City B",
            },
        ]
        json_path.write_text(json.dumps(bookings), encoding="utf-8")

        mock_get_gpx.return_value = []
        export_bookings_to_pdf(json_path, output_path, excel_info_path=excel_path)

        table_data = mock_table.call_args[0][0]

        # Zeilen:
        # 0: Header
        # 1: 15th (A Arrival)
        # 2: 16th (A Stay)
        # 3: 17th (B Arrival / A Checkout)
        # 4: 18th (B Stay)
        # 5: 19th (B Checkout)
        assert len(table_data) == 6
        assert "15.05.2026" in table_data[1][1].text
        assert "16.05.2026" in table_data[2][1].text
        assert "17.05.2026" in table_data[3][1].text
        assert "18.05.2026" in table_data[4][1].text
        assert "19.05.2026" in table_data[5][1].text

        # Prüfe Hotelnamen in Stay-Zeilen
        assert "Hotel A" in table_data[2][5].text
        assert "Hotel B" in table_data[4][5].text
