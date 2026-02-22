import pytest
from biketour_planner.elevation_calc import (
    calculate_elevation_gain_simple,
    calculate_elevation_gain_smoothed,
    calculate_elevation_gain_segment_based
)

def test_calculate_elevation_gain_simple():
    # Basic test
    elevations = [100, 102, 99, 103, 101, 110, 108, 115]
    # Threshold 3.0
    # 100->102 (2.0 < 3.0)
    # 102->99 (descent, reset)
    # 99->103 (4.0 >= 3.0) -> gain += 4.0
    # 103->101 (descent, reset)
    # 101->110 (9.0 >= 3.0) -> gain += 9.0
    # 110->108 (descent, reset)
    # 108->115 (7.0 >= 3.0) -> gain += 7.0
    # Total: 4+9+7 = 20
    assert calculate_elevation_gain_simple(elevations, threshold=3.0) == 20.0

def test_calculate_elevation_gain_simple_descent():
    elevations = [100, 95, 100, 90, 80]
    # calculate_descent=True, threshold=3.0
    # 100->95 (5.0 >= 3.0) -> gain += 5.0
    # 95->100 (ascent, reset)
    # 100->90 (10.0 >= 3.0) -> gain += 10.0
    # 90->80 (10.0 >= 3.0) -> gain += 10.0
    # Total: 5+10+10 = 25
    assert calculate_elevation_gain_simple(elevations, threshold=3.0, calculate_descent=True) == 25.0

def test_calculate_elevation_gain_simple_edge_cases():
    assert calculate_elevation_gain_simple([]) == 0.0
    assert calculate_elevation_gain_simple([100]) == 0.0
    assert calculate_elevation_gain_simple([100, None, 105]) == 0.0 # None skipped

def test_calculate_elevation_gain_smoothed():
    elevations = [100, 100, 100, 100, 100, 110, 110, 110, 110, 110]
    # window_size=5
    # smoothed will have length 10-5+1 = 6
    # first 5 points average to 100.0
    # next one: (100*4 + 110)/5 = 102.0
    # next one: (100*3 + 110*2)/5 = 104.0
    # ...
    # smoothed: [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
    # simple gain on smoothed with threshold 3.0:
    # 100->102 (2 < 3)
    # 102->104 (accumulated 4 >= 3) -> gain += 4.0
    # 104->106 (2 < 3)
    # 106->108 (accumulated 4 >= 3) -> gain += 4.0
    # 108->110 (2 < 3)
    # wait, 106->110 is 4.0
    # actually:
    # 100->102: acc=2
    # 102->104: acc=4 -> gain=4, acc=0
    # 104->106: acc=2
    # 106->108: acc=4 -> gain+=4 (8), acc=0
    # 108->110: acc=2
    # total 8.0
    assert calculate_elevation_gain_smoothed(elevations, window_size=5, threshold=3.0) == 8.0

def test_calculate_elevation_gain_smoothed_fallback():
    # Less than window_size+1 points
    elevations = [100, 110]
    assert calculate_elevation_gain_smoothed(elevations, window_size=5) == 10.0

def test_calculate_elevation_gain_segment_based():
    elevations = [100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 140, 135, 130, 125, 120, 125, 130, 135, 140, 145]
    # ascent segments after smoothing (window 3): 105->141.66 and 123.33->140
    # total ascent: ~36.66 + ~16.66 = ~53.33
    ascent = calculate_elevation_gain_segment_based(elevations, min_segment_length=5)
    assert ascent > 50 and ascent < 60

def test_calculate_elevation_gain_segment_based_descent():
    elevations = [100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 140, 135, 130, 125, 120, 125, 130, 135, 140, 145]
    # descent segments after smoothing: 141.66->123.33
    # total descent: ~18.33
    descent = calculate_elevation_gain_segment_based(elevations, min_segment_length=5, calculate_descent=True)
    assert descent > 15 and descent < 20

def test_calculate_elevation_gain_segment_based_short_track():
    elevations = [100, 110]
    assert calculate_elevation_gain_segment_based(elevations, min_segment_length=10) == 10.0

def test_calculate_elevation_gain_segment_based_constant():
    elevations = [100] * 20
    assert calculate_elevation_gain_segment_based(elevations) == 0.0
