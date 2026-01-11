import re
from time import sleep
from typing import Tuple

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Photon als Alternative zu Nominatim (nutzt auch OpenStreetMap)
try:
    from geopy.geocoders import Photon

    PHOTON_AVAILABLE = True
except ImportError:
    PHOTON_AVAILABLE = False

# Google Maps als Fallback (benötigt API-Key)
try:
    from googlemaps import Client as GoogleMaps

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

geolocator_nominatim = Nominatim(user_agent="booking-gpx-project")
geolocator_photon = Photon(user_agent="booking-gpx-project") if PHOTON_AVAILABLE else None


def clean_address(address: str) -> str:
    """Entfernt Details wie Etage, Hausnummer-Zusätze aus Adresse.

    Args:
        address: Rohadresse aus Booking

    Returns:
        Bereinigte Adresse für besseres Geocoding
    """
    # Entferne Angaben wie "Prizemlje" (Erdgeschoss), "2. kat" (2. Stock)
    address = re.sub(r'\s+(Prizemlje|[\d]+\.\s*kat)\b', '', address, flags=re.IGNORECASE)

    # Entferne komplexe Hausnummer-Zusätze wie "- 3" oder "br. 4"
    address = re.sub(r'\s+-\s+\d+', '', address)
    address = re.sub(r'\bbr\.\s+\d+', '', address)

    # Mehrfache Leerzeichen entfernen
    address = re.sub(r'\s+', ' ', address).strip()

    return address


def extract_city_country(address: str) -> str:
    """Extrahiert nur Stadt und Land aus der Adresse.

    Args:
        address: Vollständige Adresse

    Returns:
        Nur Stadt und Land
    """
    # Format: "Straße, PLZ Stadt, Land"
    parts = address.split(',')
    if len(parts) >= 2:
        # Nimm die letzten 2 Teile (Stadt + Land)
        return ','.join(parts[-2:]).strip()
    return address


def geocode_with_nominatim(address: str, retries: int = 3) -> Tuple[float, float]:
    """Geocoding mit Nominatim/OSM.

    Args:
        address: Adresse zum Geocoden
        retries: Anzahl Wiederholungsversuche bei Timeout

    Returns:
        Tuple (latitude, longitude)

    Raises:
        ValueError: Wenn Adresse nicht gefunden wurde
    """
    for attempt in range(retries):
        try:
            location = geolocator_nominatim.geocode(address)
            sleep(1)  # Nominatim-Ratelimit

            if location:
                return location.latitude, location.longitude

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt < retries - 1:
                sleep(2)
                continue
            raise ValueError(f"Geocoding-Fehler für '{address}': {e}")

    raise ValueError(f"Adresse nicht gefunden: {address}")


def geocode_with_photon(address: str) -> Tuple[float, float]:
    """Geocoding mit Photon (alternative OSM-basierte API).

    Args:
        address: Adresse zum Geocoden

    Returns:
        Tuple (latitude, longitude)

    Raises:
        ValueError: Wenn Adresse nicht gefunden wurde
    """
    if not geolocator_photon:
        raise ValueError("Photon nicht verfügbar")

    location = geolocator_photon.geocode(address)
    if location:
        return location.latitude, location.longitude

    raise ValueError(f"Adresse nicht gefunden: {address}")


def geocode_address(address: str) -> Tuple[float, float]:
    """Geocodiert eine Adresse mit mehreren Fallback-Strategien.

    Probiert verschiedene Geocoding-Dienste und Adressformate:
    1. Nominatim mit bereinigter Adresse
    2. Nominatim mit nur Stadt+Land
    3. Photon mit bereinigter Adresse (falls verfügbar)
    4. Photon mit nur Stadt+Land (falls verfügbar)

    Args:
        address: Vollständige Adresse

    Returns:
        Tuple (latitude, longitude)

    Raises:
        ValueError: Wenn keine Geocoding-Methode erfolgreich war
    """
    errors = []

    # Bereinigte Adresse
    cleaned = clean_address(address)

    print("cleaned:", cleaned)

    # 1. Versuch: Nominatim mit bereinigter Adresse
    try:
        return geocode_with_nominatim(cleaned)
    except ValueError as e:
        errors.append(f"Nominatim (bereinigt): {e}")

    # 2. Versuch: Photon mit bereinigter Adresse
    if PHOTON_AVAILABLE:
        try:
            return geocode_with_photon(cleaned)
        except ValueError as e:
            errors.append(f"Photon (bereinigt): {e}")

    # 3. Versuch: Nominatim nur mit Stadt+Land
    city_country = extract_city_country(address)

    print("city_country:", city_country)

    try:
        return geocode_with_nominatim(city_country)
    except ValueError as e:
        errors.append(f"Nominatim (Stadt+Land): {e}")

    # 4. Versuch: Photon mit Stadt+Land
    if PHOTON_AVAILABLE:
        try:
            return geocode_with_photon(city_country)
        except ValueError as e:
            errors.append(f"Photon (Stadt+Land): {e}")

    # Alle Versuche fehlgeschlagen
    error_msg = f"Adresse konnte nicht geocodiert werden: {address}\n"
    error_msg += "Versuche:\n" + "\n".join(f"  - {e}" for e in errors)
    raise ValueError(error_msg)