# Google-Style Docstrings

Dieses Projekt verwendet den Google-Stil für Python-Docstrings. Alle öffentlichen APIs (Module, Klassen, Methoden, Funktionen) müssen dokumentiert werden.

## Beispiel

```python
def berechne_distanz(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Berechnet die Haversine-Distanz zwischen zwei Koordinaten.

    Args:
        lat1 (float): Breitengrad des ersten Punktes.
        lon1 (float): Längengrad des ersten Punktes.
        lat2 (float): Breitengrad des zweiten Punktes.
        lon2 (float): Längengrad des zweiten Punktes.

    Returns:
        float: Distanz in Metern.

    Raises:
        ValueError: Wenn die Koordinaten außerhalb des gültigen Bereichs liegen.
    """
```

## Prüfung

Die Dokumentationsabdeckung wird mit `interrogate` geprüft. Das Ziel ist eine Abdeckung von > 95 %.

```bash
interrogate src
```
