import re
from pathlib import Path
from time import sleep
from typing import Optional, Any
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from .exceptions import GeocodingError
from .utils.cache import json_cache, load_json_cache
from .constants import NOMINATIM_USER_AGENT, GEOCONTROL_RATELIMIT_SLEEP

try:
    from geopy.geocoders import Photon
    PHOTON_AVAILABLE = True
except ImportError:
    PHOTON_AVAILABLE = False

geolocator_nominatim = Nominatim(user_agent=NOMINATIM_USER_AGENT)
geolocator_photon = Photon(user_agent=NOMINATIM_USER_AGENT) if PHOTON_AVAILABLE else None
GEOCODE_CACHE_FILE = Path("output/geocode_cache.json")
_geocode_cache = load_json_cache(GEOCODE_CACHE_FILE)

def clean_address(address: str) -> str:
    address = re.sub(r"\s+(Prizemlje|[\d]+\.\s*kat)\b", "", address, flags=re.IGNORECASE)
    address = re.sub(r"\s+-\s+\d+", "", address)
    address = re.sub(r"\bbr\.\s+\d+", "", address)
    return re.sub(r"\s+", " ", address).strip()

def extract_city_country(address: str) -> str:
    parts = address.split(",")
    return ",".join(parts[-2:]).strip() if len(parts) >= 2 else address

def geocode_with_nominatim(address: str, retries: int = 3) -> tuple[float, float]:
    for attempt in range(retries):
        try:
            location = geolocator_nominatim.geocode(address)
            sleep(GEOCONTROL_RATELIMIT_SLEEP)
            if location: return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt < retries - 1:
                sleep(2)
                continue
            raise GeocodingError(address, str(e))
    raise GeocodingError(address, "Address not found")

def geocode_with_photon(address: str) -> tuple[float, float]:
    if not geolocator_photon: raise GeocodingError(address, "Photon not available")
    try:
        location = geolocator_photon.geocode(address)
        if location: return location.latitude, location.longitude
    except Exception as e: raise GeocodingError(address, str(e))
    raise GeocodingError(address, "Address not found")

@json_cache(GEOCODE_CACHE_FILE, "_geocode_cache", "GEOCODE_CACHE_FILE")
def _cached_geocode(address: str) -> Optional[tuple[float, float]]:
    cleaned = clean_address(address)
    try: return geocode_with_nominatim(cleaned)
    except GeocodingError: pass
    if PHOTON_AVAILABLE:
        try: return geocode_with_photon(cleaned)
        except GeocodingError: pass
    city_country = extract_city_country(address)
    try: return geocode_with_nominatim(city_country)
    except GeocodingError: pass
    return None

def geocode_address(address: str) -> tuple[float, float]:
    result = _cached_geocode(address)
    if result: return tuple(result)
    raise GeocodingError(address, "All geocoding strategies failed")
