"""Geocoding utilities for the Bike Tour Planner.

This module provides functions to convert postal addresses into geographic coordinates
using various geocoding services with fallback strategies and caching.
"""

import re
from pathlib import Path
from time import sleep

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

from .constants import GEOCONTROL_RATELIMIT_SLEEP, NOMINATIM_USER_AGENT
from .exceptions import GeocodingError
from .utils.cache import json_cache, load_json_cache

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
    """Cleans an address string from noise and local floor information.

    Args:
        address: The raw address string.

    Returns:
        The cleaned address string.
    """
    address = re.sub(r"\s+(Prizemlje|[\d]+\.\s*kat)\b", "", address, flags=re.IGNORECASE)
    address = re.sub(r"\s+-\s+\d+", "", address)
    address = re.sub(r"\bbr\.\s+\d+", "", address)
    return re.sub(r"\s+", " ", address).strip()


def extract_city_country(address: str) -> str:
    """Extracts city and country from a full address.

    Args:
        address: The full address string.

    Returns:
        The city and country part of the address.
    """
    parts = address.split(",")
    return ",".join(parts[-2:]).strip() if len(parts) >= 2 else address


def geocode_with_nominatim(address: str, retries: int = 3) -> tuple[float, float]:
    """Geocodes an address using Nominatim.

    Args:
        address: The address to geocode.
        retries: Number of retries on timeout.

    Returns:
        A tuple of (latitude, longitude).

    Raises:
        GeocodingError: If the address cannot be found or the service is unavailable.
    """
    for attempt in range(retries):
        try:
            location = geolocator_nominatim.geocode(address)
            sleep(GEOCONTROL_RATELIMIT_SLEEP)
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt < retries - 1:
                sleep(2)
                continue
            raise GeocodingError(address, str(e)) from e
    raise GeocodingError(address, "Address not found")


def geocode_with_photon(address: str) -> tuple[float, float]:
    """Geocodes an address using Photon.

    Args:
        address: The address to geocode.

    Returns:
        A tuple of (latitude, longitude).

    Raises:
        GeocodingError: If Photon is not available or the address is not found.
    """
    if not geolocator_photon:
        raise GeocodingError(address, "Photon not available")
    try:
        location = geolocator_photon.geocode(address)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        raise GeocodingError(address, str(e)) from e
    raise GeocodingError(address, "Address not found")


@json_cache(GEOCODE_CACHE_FILE, "_geocode_cache", "GEOCODE_CACHE_FILE")
def _cached_geocode(address: str) -> tuple[float, float] | None:
    """Cached internal geocoding with multiple fallback strategies.

    Args:
        address: The address to geocode.

    Returns:
        A tuple of (latitude, longitude) or None if all strategies fail.
    """
    cleaned = clean_address(address)
    try:
        return geocode_with_nominatim(cleaned)
    except GeocodingError:
        pass
    if PHOTON_AVAILABLE:
        try:
            return geocode_with_photon(cleaned)
        except GeocodingError:
            pass
    city_country = extract_city_country(address)
    try:
        return geocode_with_nominatim(city_country)
    except GeocodingError:
        pass
    return None


def geocode_address(address: str) -> tuple[float, float]:
    """Geocodes an address with caching and multiple strategies.

    This is the main public entry point for geocoding.

    Args:
        address: The address to geocode.

    Returns:
        A tuple of (latitude, longitude).

    Raises:
        GeocodingError: If all geocoding strategies fail.
    """
    result = _cached_geocode(address)
    if result:
        return tuple(result)
    raise GeocodingError(address, "All geocoding strategies failed")
