"""Unit-Tests für gpx_route_manager_static.py.

Testet die statischen Hilfsfunktionen für GPX-Verarbeitung inklusive:
- Haversine-Distanzberechnung (haversine)
- GPX-Datei-Lesen mit Encoding-Handling (read_gpx_file)
- Basis-Dateinamen-Extraktion (get_base_filename)
- Nächste-Punkt-Suche (find_closest_point_in_track)
"""

import pytest

# import math
# from pathlib import Path
# import gpxpy
from biketour_planner.gpx_route_manager_static import (
    haversine,
    read_gpx_file,
    get_base_filename,
    find_closest_point_in_track,
)


class TestHaversine:
    """Tests für die haversine Funktion."""

    def test_haversine_same_point(self):
        """Testet Distanz zwischen identischen Punkten."""
        distance = haversine(48.1351, 11.5820, 48.1351, 11.5820)
        assert distance == pytest.approx(0.0, abs=0.1)

    def test_haversine_munich_to_garmisch(self):
        """Testet Distanz München -> Garmisch (~80km Luftlinie)."""
        # München: 48.1351, 11.5820
        # Garmisch: 47.4917, 11.0953
        distance = haversine(48.1351, 11.5820, 47.4917, 11.0953)

        # Erwartete Distanz ca. 80km (Luftlinie)
        assert distance == pytest.approx(80244, rel=0.01)

    def test_haversine_berlin_to_munich(self):
        """Testet Distanz Berlin -> München (~504km)."""
        # Berlin: 52.5200, 13.4050
        # München: 48.1351, 11.5820
        distance = haversine(52.5200, 13.4050, 48.1351, 11.5820)

        # Erwartete Distanz ca. 504km
        assert distance == pytest.approx(504000, rel=0.02)

    def test_haversine_short_distance(self):
        """Testet sehr kurze Distanz (~100m)."""
        # Zwei Punkte in München, ca. 100m auseinander
        distance = haversine(48.1351, 11.5820, 48.1360, 11.5830)

        # Erwartete Distanz ca. 100-120m
        assert 80 < distance < 150

    def test_haversine_negative_coordinates(self):
        """Testet Distanzberechnung mit negativen Koordinaten (Südhalbkugel)."""
        # Sydney: -33.8688, 151.2093
        # Melbourne: -37.8136, 144.9631
        distance = haversine(-33.8688, 151.2093, -37.8136, 144.9631)

        # Erwartete Distanz ca. 714km
        assert distance == pytest.approx(714000, rel=0.05)

    def test_haversine_across_equator(self):
        """Testet Distanzberechnung über den Äquator."""
        # Nördlich: 10.0, 0.0
        # Südlich: -10.0, 0.0
        distance = haversine(10.0, 0.0, -10.0, 0.0)

        # 20 Grad Breitengrad = ca. 2222km
        assert distance == pytest.approx(2222000, rel=0.02)

    def test_haversine_across_dateline(self):
        """Testet Distanzberechnung über die Datumsgrenze."""
        # Punkt westlich: 0.0, 179.0
        # Punkt östlich: 0.0, -179.0
        distance = haversine(0.0, 179.0, 0.0, -179.0)

        # Sollte kürzeren Weg über Datumsgrenze nehmen (~222km)
        assert distance < 300000  # Nicht den langen Weg

    def test_haversine_north_to_south_pole(self):
        """Testet maximale Distanz (Nord- zu Südpol)."""
        distance = haversine(90.0, 0.0, -90.0, 0.0)

        # Halber Erdumfang ca. 20000km
        assert distance == pytest.approx(20000000, rel=0.02)

    def test_haversine_returns_float(self):
        """Testet dass Rückgabewert ein Float ist."""
        distance = haversine(48.0, 11.0, 48.1, 11.1)
        assert isinstance(distance, float)

    def test_haversine_symmetric(self):
        """Testet dass Distanz symmetrisch ist (A->B = B->A)."""
        dist_ab = haversine(48.1351, 11.5820, 47.4917, 11.0953)
        dist_ba = haversine(47.4917, 11.0953, 48.1351, 11.5820)

        assert dist_ab == pytest.approx(dist_ba, abs=0.01)

    def test_haversine_high_precision_coordinates(self):
        """Testet mit hochpräzisen Koordinaten."""
        distance = haversine(48.135123456789, 11.582045678901, 48.135223456789, 11.582145678901)

        # Sehr kurze Distanz, sollte korrekt berechnet werden
        assert distance > 0
        assert distance < 50  # Weniger als 50m

    def test_haversine_extreme_latitude(self):
        """Testet mit extremen Breitengraden nahe den Polen."""
        # Nahe Nordpol
        distance = haversine(89.0, 0.0, 89.0, 180.0)

        # Bei hohen Breitengraden werden Längengrad-Unterschiede kürzer
        assert distance > 0
        assert distance < 300000  # Deutlich kürzer als am Äquator

    def test_haversine_zero_coordinates(self):
        """Testet mit Null-Koordinaten (Null-Insel)."""
        distance = haversine(0.0, 0.0, 1.0, 1.0)

        # Ca. 157km diagonal
        assert distance == pytest.approx(157000, rel=0.05)


class TestReadGPXFile:
    """Tests für die read_gpx_file Funktion."""

    def test_read_gpx_valid_utf8(self, tmp_path):
        """Testet Lesen einer gültigen UTF-8 GPX-Datei."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="48.1351" lon="11.5820">
        <ele>520</ele>
      </trkpt>
      <trkpt lat="48.1400" lon="11.5900">
        <ele>525</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        assert len(gpx.tracks) == 1
        assert gpx.tracks[0].name == "Test Track"
        assert len(gpx.tracks[0].segments[0].points) == 2

    def test_read_gpx_with_bom(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit BOM (Byte Order Mark)."""
        gpx_content = '\ufeff<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1"><trk><trkseg></trkseg></trk></gpx>'

        gpx_file = tmp_path / "test_bom.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8-sig")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        assert len(gpx.tracks) == 1

    def test_read_gpx_with_leading_whitespace(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit führenden Whitespaces."""
        gpx_content = '\n\n  \t<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1"><trk><trkseg></trkseg></trk></gpx>'

        gpx_file = tmp_path / "test_whitespace.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None

    def test_read_gpx_latin1_encoding(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit Latin-1 Encoding."""
        gpx_content = """<?xml version="1.0" encoding="ISO-8859-1"?>
<gpx version="1.1">
  <trk>
    <name>Test mit Umlauten: äöü</name>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_latin1.gpx"
        gpx_file.write_bytes(gpx_content.encode("latin-1"))

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        assert "Umlauten" in gpx.tracks[0].name

    def test_read_gpx_cp1252_encoding(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit CP1252 Encoding."""
        gpx_content = """<?xml version="1.0" encoding="windows-1252"?>
<gpx version="1.1">
  <trk>
    <name>Test</name>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_cp1252.gpx"
        gpx_file.write_bytes(gpx_content.encode("cp1252"))

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None

    def test_read_gpx_invalid_xml(self, tmp_path):
        """Testet Verhalten bei ungültigem XML."""
        gpx_content = '<?xml version="1.0"?>\n<gpx><unclosed_tag>'

        gpx_file = tmp_path / "test_invalid.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is None

    def test_read_gpx_empty_file(self, tmp_path):
        """Testet Verhalten bei leerer Datei."""
        gpx_file = tmp_path / "test_empty.gpx"
        gpx_file.write_text("", encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is None

    def test_read_gpx_non_gpx_content(self, tmp_path):
        """Testet Verhalten bei Nicht-GPX-Inhalt."""
        gpx_file = tmp_path / "test_text.gpx"
        gpx_file.write_text("Dies ist nur Text, kein GPX", encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is None

    def test_read_gpx_multiple_tracks(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit mehreren Tracks."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <name>Track 1</name>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
    </trkseg>
  </trk>
  <trk>
    <name>Track 2</name>
    <trkseg>
      <trkpt lat="49.0" lon="12.0"/>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_multi.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        assert len(gpx.tracks) == 2

    def test_read_gpx_with_metadata(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit Metadaten."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BRouter">
  <metadata>
    <name>Route Metadata</name>
    <desc>Test Route</desc>
  </metadata>
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_metadata.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        assert gpx.name == "Route Metadata"
        assert gpx.description == "Test Route"

    def test_read_gpx_with_elevation_and_time(self, tmp_path):
        """Testet Lesen einer GPX-Datei mit Höhen- und Zeitinformationen."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0">
        <ele>520</ele>
        <time>2026-05-15T10:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_ele_time.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        assert gpx is not None
        point = gpx.tracks[0].segments[0].points[0]
        assert point.elevation == 520
        assert point.time is not None

    def test_read_gpx_mixed_encoding_fallback(self, tmp_path):
        """Testet Fallback bei gemischten/unklaren Encodings."""
        # Erstelle Datei mit problematischen Zeichen
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <name>Test äöü ß</name>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"/>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_mixed.gpx"
        # Schreibe mit UTF-8 aber simuliere encoding-Probleme
        gpx_file.write_text(gpx_content, encoding="utf-8")

        gpx = read_gpx_file(gpx_file)

        # Sollte trotzdem erfolgreich gelesen werden
        assert gpx is not None


class TestGetBaseFilename:
    """Tests für die get_base_filename Funktion."""

    def test_get_base_filename_no_suffix(self):
        """Testet Dateinamen ohne Richtungssuffix."""
        result = get_base_filename("route_munich_garmisch.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_inverted_suffix(self):
        """Testet Entfernung von '_inverted' Suffix."""
        result = get_base_filename("route_munich_garmisch_inverted.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_reversed_suffix(self):
        """Testet Entfernung von '_reversed' Suffix."""
        result = get_base_filename("route_munich_garmisch_reversed.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_rev_suffix(self):
        """Testet Entfernung von '_rev' Suffix."""
        result = get_base_filename("route_munich_garmisch_rev.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_inverse_suffix(self):
        """Testet Entfernung von '_inverse' Suffix."""
        result = get_base_filename("route_munich_garmisch_inverse.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_backward_suffix(self):
        """Testet Entfernung von '_backward' Suffix."""
        result = get_base_filename("route_munich_garmisch_backward.gpx")
        assert result == "route_munich_garmisch.gpx"

    def test_get_base_filename_case_insensitive(self):
        """Testet dass Suffix-Erkennung case-insensitive ist."""
        result = get_base_filename("route_REVERSED.gpx")
        assert result == "route.gpx"

    def test_get_base_filename_mixed_case(self):
        """Testet gemischte Groß-/Kleinschreibung."""
        result = get_base_filename("Route_Munich_ReVeRsEd.gpx")
        assert result == "Route_Munich.gpx"

    def test_get_base_filename_simple(self):
        """Testet einfachen Dateinamen."""
        result = get_base_filename("track.gpx")
        assert result == "track.gpx"

    def test_get_base_filename_with_path(self):
        """Testet dass Funktion nur Dateinamen behandelt (kein Path-Handling)."""
        # Funktion arbeitet nur auf Strings, nicht Paths
        result = get_base_filename("some_track_inverted.gpx")
        assert result == "some_track.gpx"

    def test_get_base_filename_multiple_underscores(self):
        """Testet Dateinamen mit mehreren Unterstrichen."""
        result = get_base_filename("route_munich_to_garmisch_via_mittenwald_reversed.gpx")
        assert result == "route_munich_to_garmisch_via_mittenwald.gpx"

    def test_get_base_filename_suffix_in_middle(self):
        """Testet dass Suffix nur am Ende erkannt wird."""
        result = get_base_filename("reversed_route_normal.gpx")
        assert result == "reversed_route_normal.gpx"

    def test_get_base_filename_no_extension(self):
        """Testet Dateinamen ohne .gpx Extension."""
        result = get_base_filename("route_reversed")
        # Wird nicht als .gpx erkannt, daher keine Änderung
        assert result == "route_reversed"

    def test_get_base_filename_double_suffix(self):
        """Testet Dateinamen mit doppeltem Suffix."""
        # Nur der letzte Suffix sollte entfernt werden
        result = get_base_filename("route_inverted_reversed.gpx")
        assert result == "route_inverted.gpx"


class TestFindClosestPointInTrack:
    """Tests für die find_closest_point_in_track Funktion."""

    def test_find_closest_point_single_point(self):
        """Testet Suche bei nur einem Punkt."""
        points = [{"lat": 48.1351, "lon": 11.5820, "index": 0}]

        idx, dist = find_closest_point_in_track(points, 48.1351, 11.5820)

        assert idx == 0
        assert dist == pytest.approx(0.0, abs=0.1)

    def test_find_closest_point_exact_match(self):
        """Testet Suche bei exakter Übereinstimmung."""
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 48.1351, "lon": 11.5820, "index": 1},
            {"lat": 48.2, "lon": 11.6, "index": 2},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1351, 11.5820)

        assert idx == 1
        assert dist == pytest.approx(0.0, abs=0.1)

    def test_find_closest_point_first_is_closest(self):
        """Testet wenn erster Punkt am nächsten ist."""
        points = [
            {"lat": 48.1351, "lon": 11.5820, "index": 0},
            {"lat": 49.0, "lon": 12.0, "index": 1},
            {"lat": 50.0, "lon": 13.0, "index": 2},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1350, 11.5821)

        assert idx == 0
        assert dist < 100  # Weniger als 100m

    def test_find_closest_point_last_is_closest(self):
        """Testet wenn letzter Punkt am nächsten ist."""
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 49.0, "lon": 12.0, "index": 1},
            {"lat": 48.1351, "lon": 11.5820, "index": 2},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1350, 11.5821)

        assert idx == 2
        assert dist < 100

    def test_find_closest_point_middle_is_closest(self):
        """Testet wenn mittlerer Punkt am nächsten ist."""
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 48.1351, "lon": 11.5820, "index": 1},
            {"lat": 50.0, "lon": 13.0, "index": 2},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1350, 11.5821)

        assert idx == 1

    def test_find_closest_point_many_points(self):
        """Testet Suche bei vielen Punkten."""
        # Erstelle 1000 Punkte entlang einer Linie
        points = [{"lat": 48.0 + i * 0.001, "lon": 11.0 + i * 0.001, "index": i} for i in range(1000)]

        # Suche Punkt nahe Index 500
        idx, dist = find_closest_point_in_track(points, 48.5, 11.5)

        # Sollte Punkt ~500 finden
        assert 490 < idx < 510

    def test_find_closest_point_non_sequential_indices(self):
        """Testet dass tatsächlich index-Wert zurückgegeben wird, nicht Array-Index."""
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 100},
            {"lat": 48.1351, "lon": 11.5820, "index": 200},
            {"lat": 49.0, "lon": 12.0, "index": 300},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1351, 11.5820)

        assert idx == 200  # index-Wert, nicht Array-Index 1

    def test_find_closest_point_equal_distances(self):
        """Testet Verhalten bei gleichen Distanzen."""
        # Zwei Punkte gleich weit entfernt vom Ziel
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 48.0, "lon": 11.2, "index": 1},
        ]

        # Zielpunkt genau in der Mitte
        idx, dist = find_closest_point_in_track(points, 48.0, 11.1)

        # Sollte ersten finden (da in Schleife zuerst geprüft)
        assert idx == 0

    def test_find_closest_point_negative_coordinates(self):
        """Testet Suche mit negativen Koordinaten."""
        points = [
            {"lat": -33.8688, "lon": 151.2093, "index": 0},
            {"lat": -34.0, "lon": 151.0, "index": 1},
            {"lat": -34.5, "lon": 150.5, "index": 2},
        ]

        idx, dist = find_closest_point_in_track(points, -33.9, 151.1)

        # Index 0 sollte am nächsten sein
        assert idx == 0

    def test_find_closest_point_across_dateline(self):
        """Testet Suche über die Datumsgrenze."""
        points = [
            {"lat": 0.0, "lon": 179.0, "index": 0},
            {"lat": 0.0, "lon": -179.0, "index": 1},
        ]

        # Zielpunkt nahe der Datumsgrenze
        idx, dist = find_closest_point_in_track(points, 0.0, 179.5)

        # Index 0 sollte näher sein
        assert idx == 0

    def test_find_closest_point_returns_distance(self):
        """Testet dass korrekte Distanz zurückgegeben wird."""
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 48.1, "lon": 11.1, "index": 1},
        ]

        idx, dist = find_closest_point_in_track(points, 48.1, 11.1)

        assert dist == pytest.approx(0.0, abs=0.1)

    def test_find_closest_point_empty_list(self):
        """Testet Verhalten bei leerer Punkt-Liste."""
        points = []

        idx, dist = find_closest_point_in_track(points, 48.0, 11.0)

        # Sollte None und inf zurückgeben
        assert idx is None
        assert dist == float("inf")


class TestIntegration:
    """Integrationstests für Zusammenspiel der Funktionen."""

    def test_gpx_workflow_read_find_point(self, tmp_path):
        """Testet Workflow: GPX lesen -> nächsten Punkt finden."""
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.0" lon="11.0"><ele>500</ele></trkpt>
      <trkpt lat="48.1351" lon="11.5820"><ele>520</ele></trkpt>
      <trkpt lat="48.2" lon="11.6"><ele>540</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""

        gpx_file = tmp_path / "test_route.gpx"
        gpx_file.write_text(gpx_content, encoding="utf-8")

        # 1. Lese GPX
        gpx = read_gpx_file(gpx_file)
        assert gpx is not None

        # 2. Extrahiere Punkte
        points = []
        for i, p in enumerate(gpx.tracks[0].segments[0].points):
            points.append({"lat": p.latitude, "lon": p.longitude, "elevation": p.elevation, "index": i})

        # 3. Finde nächsten Punkt
        idx, dist = find_closest_point_in_track(points, 48.1350, 11.5821)

        assert idx == 1
        assert dist < 100

    def test_distance_calculation_consistency(self):
        """Testet Konsistenz der Distanzberechnung."""
        # Gleiche Punkte wie in find_closest_point_in_track
        points = [
            {"lat": 48.0, "lon": 11.0, "index": 0},
            {"lat": 48.1351, "lon": 11.5820, "index": 1},
        ]

        target_lat, target_lon = 48.1351, 11.5820

        # Distanz via haversine
        manual_dist = haversine(48.1351, 11.5820, target_lat, target_lon)

        print(points)
        print(manual_dist)
