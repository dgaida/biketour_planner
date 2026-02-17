# Google-Style Docstrings

This project uses the Google style for Python docstrings. All public APIs (modules, classes, methods, functions) must be documented.

## Example

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the haversine distance between two coordinates.

    Args:
        lat1 (float): Latitude of the first point.
        lon1 (float): Longitude of the first point.
        lat2 (float): Latitude of the second point.
        lon2 (float): Longitude of the second point.

    Returns:
        float: Distance in meters.

    Raises:
        ValueError: If coordinates are out of valid range.
    """
```

## Enforcement

Documentation coverage is measured using `interrogate`. The goal is a coverage of > 95%.

```bash
interrogate src
```
