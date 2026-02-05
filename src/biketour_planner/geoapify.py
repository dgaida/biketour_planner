"""Geoapify API integration for tourist sight discovery."""
import os
from pathlib import Path
from typing import Optional, Any
import requests
from dotenv import load_dotenv
from .config import get_config
from .logger import get_logger
from .utils.cache import json_cache, load_json_cache
from .constants import GEOAPIFY_DEFAULT_SEARCH_RADIUS_M, GEOAPIFY_DEFAULT_MAX_POIS

logger = get_logger()
load_dotenv("secrets.env")
geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")
GEOAPIFY_CACHE_FILE = Path("output/geoapify_cache.json")
_geoapify_cache = load_json_cache(GEOAPIFY_CACHE_FILE)

@json_cache(GEOAPIFY_CACHE_FILE, "_geoapify_cache", "GEOAPIFY_CACHE_FILE")
def _fetch_tourist_sights(lat: float, lon: float, radius: int, limit: int) -> Optional[dict[str, Any]]:
    if not geoapify_api_key:
        logger.warning("GEOAPIFY_API_KEY not set - skipping tourist sight discovery")
        return {"features": []}
    url = "https://api.geoapify.com/v2/places"
    params = {"categories": "tourism.sights", "filter": f"circle:{lon},{lat},{radius}", "limit": limit, "apiKey": geoapify_api_key}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error during Geoapify request: {e}")
        return None

def find_top_tourist_sights(lat: float, lon: float, radius: Optional[int] = None, limit: Optional[int] = None) -> Optional[dict[str, Any]]:
    config = get_config()
    if radius is None:
        try: radius = config.geoapify.search_radius_m
        except (AttributeError, KeyError): radius = GEOAPIFY_DEFAULT_SEARCH_RADIUS_M
    if limit is None:
        try: limit = config.geoapify.max_pois
        except (AttributeError, KeyError): limit = GEOAPIFY_DEFAULT_MAX_POIS
    return _fetch_tourist_sights(round(lat, 4), round(lon, 4), radius, limit)

def get_names_as_comma_separated_string(data: Optional[dict[str, Any]]) -> str:
    if not data: return ""
    names = []
    for poi in data.get("features", []):
        props = poi.get("properties", {})
        if "name" in props: names.append(props["name"])
        elif "street" in props: names.append(props["street"])
        else: names.append(f"({props.get('lat')}, {props.get('lon')})")
    return ", ".join(names)
