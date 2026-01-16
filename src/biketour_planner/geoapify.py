"""Geoapify API Integration für Sehenswürdigkeiten-Suche.

Dieses Modul nutzt die Geoapify Places API um touristische Sehenswürdigkeiten
in der Nähe eines bestimmten Standorts zu finden.

API-Dokumentation:
    - https://apidocs.geoapify.com/docs/places/#quick-start
    - https://apidocs.geoapify.com/docs/places/
"""

import os
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

from .logger import get_logger

# Initialisiere Logger
logger = get_logger()

# Lade Umgebungsvariablen
load_dotenv("secrets.env")

# Lade API-Key aus Umgebung
geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")


def find_top_tourist_sights(lat: float, lon: float, radius: int = 5000, limit: int = 2) -> Optional[Dict]:
    """Findet touristische Sehenswürdigkeiten in der Nähe einer Koordinate.

    Nutzt die Geoapify Places API um Sehenswürdigkeiten (POIs der Kategorie
    "tourism.sights") im angegebenen Radius zu finden.

    Args:
        lat: Breitengrad in Dezimalgrad.
        lon: Längengrad in Dezimalgrad.
        radius: Suchradius in Metern (Default: 5000m = 5km).
        limit: Maximale Anzahl zurückzugebender Ergebnisse (Default: 2).

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

    Note:
        Benötigt einen gültigen GEOAPIFY_API_KEY in der secrets.env Datei.
    """
    if not geoapify_api_key:
        logger.error("GEOAPIFY_API_KEY nicht in Umgebungsvariablen gefunden")
        return None

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


def get_names_as_comma_separated_string(data: Optional[Dict]) -> str:
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
    if result:
        result += ", "  # Trailing comma für Konsistenz

    logger.debug(f"Extrahierte {len(names)} POI-Namen")

    return result
