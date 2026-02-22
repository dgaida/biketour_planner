from unittest.mock import MagicMock

from biketour_planner.excel_hyperlinks import create_tourist_sights_hyperlinks


def test_create_hyperlinks_none():
    ws = {}
    create_tourist_sights_hyperlinks(ws, 5, None)
    assert ws["I5"] == ""


def test_create_hyperlinks_empty():
    ws = {}
    create_tourist_sights_hyperlinks(ws, 5, {"features": []})
    assert ws["I5"] == ""


def test_create_hyperlinks_success():
    ws = MagicMock()
    # Mocking ws[f"{col}{row}"]
    cell_mock = MagicMock()
    ws.__getitem__.return_value = cell_mock

    tourist_sights = {
        "features": [
            {"properties": {"name": "Tower", "lat": 45.0, "lon": 15.0}},
            {"properties": {"name": "Bridge", "lat": 45.1, "lon": 15.1}},
        ]
    }

    create_tourist_sights_hyperlinks(ws, 10, tourist_sights)

    # First sight in Column I
    assert ws.__setitem__.call_args_list[0][0][0] == "I10"
    formula1 = ws.__setitem__.call_args_list[0][0][1]
    assert "Tower" in formula1
    assert "45.0,15.0" in formula1

    # Second sight in Column L
    assert ws.__setitem__.call_args_list[1][0][0] == "L10"
    formula2 = ws.__setitem__.call_args_list[1][0][1]
    assert "Bridge" in formula2
    assert "45.1,15.1" in formula2


def test_create_hyperlinks_fallbacks():
    ws = MagicMock()
    tourist_sights = {
        "features": [
            {"properties": {"street": "Main St", "lat": 1.0, "lon": 2.0}},
            {"properties": {"lat": 3.0, "lon": 4.0}},
            {"something": "else"},
        ]
    }
    create_tourist_sights_hyperlinks(ws, 1, tourist_sights)
    # 1st: Street fallback
    assert "Main St" in ws.__setitem__.call_args_list[0][0][1]
    # 2nd: Coordinates fallback
    assert "(3.0, 4.0)" in ws.__setitem__.call_args_list[1][0][1]
    # 3rd: Skipped (no properties)


def test_create_hyperlinks_missing_coords():
    ws = MagicMock()
    tourist_sights = {"features": [{"properties": {"name": "No Lat", "lon": 2.0}}]}
    create_tourist_sights_hyperlinks(ws, 1, tourist_sights)
    assert not ws.__setitem__.called


def test_create_hyperlinks_too_many_pois():
    ws = MagicMock()
    # Many POIs
    features = [{"properties": {"name": f"POI {i}", "lat": 0, "lon": 0}} for i in range(40)]
    create_tourist_sights_hyperlinks(ws, 1, {"features": features})
    # Should only set up to available columns (1 + 26 = 27)
    assert ws.__setitem__.call_count == 27
