import json
import shutil
import unittest
from datetime import datetime
from pathlib import Path

import openpyxl

from biketour_planner.excel_export import (
    create_accommodation_text,
    export_bookings_to_excel,
    extract_city_name,
)


class TestExcelExport(unittest.TestCase):
    def test_extract_city_name(self):
        self.assertEqual(extract_city_name("Straße 1, 21000 Split, Kroatien"), "Split")
        self.assertEqual(extract_city_name("Some Street 123, 10115 Berlin, Germany"), "Berlin")
        self.assertEqual(extract_city_name("Just a city name"), "Just a city name")
        self.assertEqual(extract_city_name("12345 City"), "City")
        self.assertEqual(extract_city_name(""), "")

    def test_create_accommodation_text(self):
        booking_full = {
            "hotel_name": "Grand Hotel",
            "address": "Main Street 1",
            "has_washing_machine": True,
            "has_kitchen": True,
        }
        expected_text_full = "Grand Hotel\nMain Street 1\nWasch, Küche"
        self.assertEqual(create_accommodation_text(booking_full), expected_text_full)

        booking_no_amenities = {
            "hotel_name": "Budget Inn",
            "address": "Side Alley 5",
        }
        expected_text_no_amenities = "Budget Inn\nSide Alley 5"
        self.assertEqual(create_accommodation_text(booking_no_amenities), expected_text_no_amenities)

        booking_only_name = {"hotel_name": "Just a Name"}
        self.assertEqual(create_accommodation_text(booking_only_name), "Just a Name")

        booking_empty = {}
        self.assertEqual(create_accommodation_text(booking_empty), "")

    def test_export_bookings_to_excel(self):
        # Create a temporary directory for test files
        test_dir = Path("test_excel_export_temp")
        test_dir.mkdir(exist_ok=True)

        # Create a dummy JSON file
        bookings_data = [
            {
                "arrival_date": "2026-08-01",
                "departure_date": "2026-08-03",
                "address": "Street 1, 12345 CityA, Country",
                "total_distance_km": 50,
                "hotel_name": "Hotel A",
                "has_washing_machine": True,
                "has_kitchen": False,
                "total_ascent_m": 500,
                "max_elevation_m": 600,
                "tourist_sights": {
                    "features": [
                        {"properties": {"name": "Sight 1", "lat": 43.5, "lon": 16.4}},
                        {"properties": {"name": "Sight 2", "lat": 43.6, "lon": 16.5}},
                    ]
                },
                "total_price": 100,
                "free_cancel_until": "2026-07-15",
            },
            {
                "arrival_date": "2026-08-05",
                "departure_date": "2026-08-07",
                "address": "Avenue 2, 54321 CityB, Country",
                "total_distance_km": 75,
                "hotel_name": "Hotel B",
                "has_washing_machine": False,
                "has_kitchen": True,
                "total_ascent_m": 300,
                "max_elevation_m": 400,
                "tourist_sights": [],
                "total_price": 150,
                "free_cancel_until": "2026-07-20",
            },
        ]
        json_path = test_dir / "bookings.json"
        with open(json_path, "w") as f:
            json.dump(bookings_data, f)

        # Create a dummy Excel template
        template_path = test_dir / "template.xlsx"
        wb_template = openpyxl.Workbook()
        ws_template = wb_template.active
        ws_template["A1"] = "Day"
        ws_template["B1"] = "Date"
        # Add headers to match expected structure if needed
        wb_template.save(template_path)

        # Define output path
        output_path = test_dir / "output.xlsx"

        # Run the function
        export_bookings_to_excel(json_path, template_path, output_path, start_row=2)

        # --- Verification ---
        self.assertTrue(output_path.exists())

        # Load the generated Excel and verify content
        wb_out = openpyxl.load_workbook(output_path)
        ws_out = wb_out.active

        # Check Row 2 (Booking 1)
        self.assertEqual(ws_out["A2"].value, 1)
        # Handle datetime object comparison for date
        self.assertIsInstance(ws_out["B2"].value, datetime)
        self.assertEqual(ws_out["B2"].value.strftime("%Y-%m-%d"), "2026-08-01")
        self.assertEqual(ws_out["C2"].value, None)  # No previous city
        self.assertEqual(ws_out["D2"].value, "CityA")
        self.assertEqual(ws_out["E2"].value, 50)
        self.assertEqual(ws_out["F2"].value, "Hotel A\nStreet 1, 12345 CityA, Country\nWasch")
        self.assertEqual(ws_out["G2"].value, "500 / 600")
        # Column I now contains a HYPERLINK formula
        self.assertIn("HYPERLINK", ws_out["I2"].value)
        self.assertIn("Sight 1", ws_out["I2"].value)
        self.assertEqual(ws_out["J2"].value, 100)
        self.assertEqual(ws_out["K2"].value, "Stornierung bis: 2026-07-15")

        # Check Row 3 (Empty day between bookings)
        self.assertEqual(ws_out["A3"].value, 2)
        self.assertIsInstance(ws_out["B3"].value, datetime)
        self.assertEqual(ws_out["B3"].value.strftime("%Y-%m-%d"), "2026-08-03")
        self.assertEqual(ws_out["C3"].value, "CityA")  # Start is previous city
        self.assertEqual(ws_out["D3"].value, None)  # Destination is empty

        # Check Row 4 (Booking 2)
        self.assertEqual(ws_out["A5"].value, 4)
        self.assertIsInstance(ws_out["B5"].value, datetime)
        self.assertEqual(ws_out["B5"].value.strftime("%Y-%m-%d"), "2026-08-05")
        self.assertEqual(ws_out["C5"].value, "CityA")  # Start is previous city
        self.assertEqual(ws_out["D5"].value, "CityB")
        self.assertEqual(ws_out["E5"].value, 75)
        self.assertEqual(ws_out["F5"].value, "Hotel B\nAvenue 2, 54321 CityB, Country\nKüche")
        self.assertEqual(ws_out["G5"].value, "300 / 400")
        self.assertEqual(ws_out["J5"].value, 150)
        self.assertEqual(ws_out["K5"].value, "Stornierung bis: 2026-07-20")

        # Clean up the temporary directory
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    unittest.main()
