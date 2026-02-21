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

        # Header + 3 Zeilen
        assert len(table_data) == 4

        # Zeile 1: Anreisetag (index 1)
        assert "Arrival Info" in table_data[1][8].text

        # Zeile 2: Zwischentag (index 2)
        assert "Intermediate Info" in table_data[2][8].text

        # Zeile 3: Checkout-Tag (index 3)
        assert "Checkout Info" in table_data[3][8].text

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
        # Wait, booking 1 departure is 16th. Booking 2 arrival is 18th.
        # Intermediate day is 16th (if departure and next arrival are different).
        # In current logic:
        # Day 1: 15th (Arrival Hotel 1)
        # previous_departure_date = 16th
        # next booking arrival = 18th
        # days_between = 18 - 16 = 2
        # offset 0: 16th
        # offset 1: 17th
        # Then Day 4: 18th (Arrival Hotel 2)
        # Then Checkout: 19th

        mock_read_excel.return_value = {"2026-05-16": ["Gap Day 16"], "2026-05-17": ["Gap Day 17"]}

        mock_get_gpx.return_value = []

        export_bookings_to_pdf(json_path, output_path, excel_info_path=excel_path)

        table_data = mock_table.call_args[0][0]

        # Zeilen:
        # 0: Header
        # 1: 15th
        # 2: 16th (Gap)
        # 3: 17th (Gap)
        # 4: 18th
        # 5: 19th (Checkout)

        assert "Gap Day 16" in table_data[2][8].text
        assert "Gap Day 17" in table_data[3][8].text
