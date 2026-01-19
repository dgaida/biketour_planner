"""Geoapify API Integration für Sehenswürdigkeiten-Suche.

Dieses Modul nutzt die Geoapify Places API um touristische Sehenswürdigkeiten
in der Nähe eines bestimmten Standorts zu finden.

API-Dokumentation:
    - https://apidocs.geoapify.com/docs/places/#quick-start
    - https://apidocs.geoapify.com/docs/places/
"""

import json
import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

from .config import get_config
from .logger import get_logger

# Initialisiere Logger
logger = get_logger()

# Lade Umgebungsvariablen
load_dotenv("secrets.env")

# Lade API-Key aus Umgebung
geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")


GEOAPIFY_CACHE_FILE = Path("output/geoapify_cache.json")


def load_geoapify_cache() -> dict:
    """Lädt Geoapify-Cache von Disk."""
    if GEOAPIFY_CACHE_FILE.exists():
        return json.loads(GEOAPIFY_CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_geoapify_cache(cache: dict) -> None:
    """Speichert Geoapify-Cache auf Disk."""
    GEOAPIFY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GEOAPIFY_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


_geoapify_cache = load_geoapify_cache()


def _make_cache_key(lat: float, lon: float, radius: int, limit: int) -> str:
    """Erstellt Cache-Key aus Suchparametern.

    Rundet Koordinaten auf 4 Dezimalstellen (~11m Genauigkeit), damit
    minimal unterschiedliche Koordinaten den gleichen Cache-Eintrag nutzen.

    Args:
        lat: Breitengrad in Dezimalgrad.
        lon: Längengrad in Dezimalgrad.
        radius: Suchradius in Metern.
        limit: Maximale Anzahl Ergebnisse.

    Returns:
        Cache-Key als String im Format "lat_lon_radius_limit".

    Example:
        >>> _make_cache_key(43.508134, 16.440235, 5000, 2)
        '43.5081_16.4402_5000_2'
    """
    # Runde auf 4 Dezimalstellen (~11m Genauigkeit)
    # Das verhindert, dass minimal unterschiedliche Hotel-Koordinaten
    # zu separaten API-Calls führen
    lat_rounded = round(lat, 4)
    lon_rounded = round(lon, 4)

    return f"{lat_rounded}_{lon_rounded}_{radius}_{limit}"


def find_top_tourist_sights(lat: float, lon: float, radius: int = None, limit: int = None) -> Optional[dict]:
    """Findet touristische Sehenswürdigkeiten in der Nähe einer Koordinate.

    Nutzt die Geoapify Places API um Sehenswürdigkeiten (POIs der Kategorie
    "tourism.sights") im angegebenen Radius zu finden.

    Args:
        lat: Breitengrad in Dezimalgrad.
        lon: Längengrad in Dezimalgrad.
        radius: Suchradius in Metern. Falls None, wird config.geoapify.search_radius_m verwendet.
        limit: Maximale Anzahl zurückzugebender Ergebnisse. Falls None, wird config.geoapify.max_pois verwendet.

    Returns:
        Dictionary mit GeoJSON-Features der gefundenen Sehenswürdigkeiten
        oder None bei Fehler.

        Struktur des Returns:
            {
                "features": [
                    {
                        "properties": {
                            "name": str,
                            "lat": float,
                            "lon": float,
                            ...
                        }
                    }
                ]
            }

    Example:
        >>> # Finde Sehenswürdigkeiten in Split, Kroatien
        >>> data = find_top_tourist_sights(43.5081, 16.4402)
        >>> if data:
        ...     for poi in data.get("features", []):
        ...         print(poi["properties"]["name"])
        >>>
        >>> # Mit benutzerdefinierten Parametern
        >>> data = find_top_tourist_sights(43.5081, 16.4402, radius=10000, limit=5)

    Note:
        Benötigt einen gültigen GEOAPIFY_API_KEY in der secrets.env Datei.
    """
    # Lade Config für Defaults
    config = get_config()

    if radius is None:
        radius = config.geoapify.search_radius_m

    if limit is None:
        limit = config.geoapify.max_pois

    # Cache-Lookup
    cache_key = _make_cache_key(lat, lon, radius, limit)

    if cache_key in _geoapify_cache:
        logger.info(f"Cache-Hit für Koordinaten ({lat:.4f}, {lon:.4f})")
        return _geoapify_cache[cache_key]

    if not geoapify_api_key:
        logger.warning("GEOAPIFY_API_KEY nicht gesetzt - überspringe Sehenswürdigkeiten-Suche")
        return {"features": []}  # Statt None, damit Code nicht crasht

    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": "tourism.sights",
        "filter": f"circle:{lon},{lat},{radius}",
        "limit": limit,
        "apiKey": geoapify_api_key,
    }

    try:
        logger.info(f"Suche Sehenswürdigkeiten bei ({lat:.4f}, {lon:.4f}), Radius: {radius}m")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Logge gefundene POIs
        feature_count = len(data.get("features", []))
        logger.info(f"{feature_count} Sehenswürdigkeiten gefunden")

        for poi in data.get("features", []):
            props = poi["properties"]
            poi_name = props.get("name", f"({props.get('lat')}, {props.get('lon')})")
            logger.debug(f"  - {poi_name}")

        # Speichere im Cache
        _geoapify_cache[cache_key] = data
        save_geoapify_cache(_geoapify_cache)
        logger.debug(f"Cache gespeichert für Key: {cache_key}")

        return data

    except requests.exceptions.Timeout:
        logger.error(f"Timeout bei Geoapify-Anfrage für ({lat:.4f}, {lon:.4f})")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Fehler bei Geoapify-Anfrage: {e}")
        return None
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in find_top_tourist_sights: {e}")
        return None


def get_names_as_comma_separated_string(data: Optional[dict]) -> str:
    """Extrahiert POI-Namen aus Geoapify-Daten als Komma-separierte Liste.

    Args:
        data: Geoapify-Response-Dictionary mit "features" Key oder None.

    Returns:
        Komma-separierte Liste der POI-Namen. Bei fehlenden Namen werden
        Straßennamen oder Koordinaten als Fallback verwendet.
        Leerer String wenn data None ist.

    Example:
        >>> data = find_top_tourist_sights(43.5081, 16.4402)
        >>> names = get_names_as_comma_separated_string(data)
        >>> print(names)
        'Diokletianpalast, Marjan Park, '
    """
    if not data:
        logger.debug("Keine Daten für Namen-Extraktion vorhanden")
        return ""

    names = []

    for poi in data.get("features", []):
        if "properties" not in poi:
            continue

        props = poi["properties"]

        # Versuche verschiedene Namensquellen
        if "name" in props:
            names.append(props["name"])
        elif "street" in props:
            names.append(props["street"])
        else:
            # Fallback auf Koordinaten
            coord_str = f"({props.get('lat')}, {props.get('lon')})"
            names.append(coord_str)

    result = ", ".join(names)

    logger.debug(f"Extrahierte {len(names)} POI-Namen")

    return result
