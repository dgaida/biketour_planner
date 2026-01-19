import json
import re
from pathlib import Path
from time import sleep

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# Photon als Alternative zu Nominatim (nutzt auch OpenStreetMap)
try:
    from geopy.geocoders import Photon

    PHOTON_AVAILABLE = True
except ImportError:
    PHOTON_AVAILABLE = False

# Google Maps als Fallback (benötigt API-Key)
try:
    # from googlemaps import Client as GoogleMaps  # F401 ignore

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

geolocator_nominatim = Nominatim(user_agent="booking-gpx-project")
geolocator_photon = Photon(user_agent="booking-gpx-project") if PHOTON_AVAILABLE else None


GEOCODE_CACHE_FILE = Path("output/geocode_cache.json")


def load_geocode_cache() -> dict:
    """Lädt Geocoding-Cache von Disk."""
    if GEOCODE_CACHE_FILE.exists():
        return json.loads(GEOCODE_CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_geocode_cache(cache: dict) -> None:
    """Speichert Geocoding-Cache auf Disk."""
    GEOCODE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GEOCODE_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


_geocode_cache = load_geocode_cache()


def clean_address(address: str) -> str:
    """Entfernt Details wie Etage, Hausnummer-Zusätze aus Adresse.

    Args:
        address: Rohadresse aus Booking

    Returns:
        Bereinigte Adresse für besseres Geocoding
    """
    # Entferne Angaben wie "Prizemlje" (Erdgeschoss), "2. kat" (2. Stock)
    address = re.sub(r"\s+(Prizemlje|[\d]+\.\s*kat)\b", "", address, flags=re.IGNORECASE)

    # Entferne komplexe Hausnummer-Zusätze wie "- 3" oder "br. 4"
    address = re.sub(r"\s+-\s+\d+", "", address)
    address = re.sub(r"\bbr\.\s+\d+", "", address)

    # Mehrfache Leerzeichen entfernen
    address = re.sub(r"\s+", " ", address).strip()

    return address


def extract_city_country(address: str) -> str:
    """Extrahiert nur Stadt und Land aus der Adresse.

    Args:
        address: Vollständige Adresse

    Returns:
        Nur Stadt und Land
    """
    # Format: "Straße, PLZ Stadt, Land"
    parts = address.split(",")
    if len(parts) >= 2:
        # Nimm die letzten 2 Teile (Stadt + Land)
        return ",".join(parts[-2:]).strip()
    return address


def geocode_with_nominatim(address: str, retries: int = 3) -> tuple[float, float]:
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


def geocode_with_photon(address: str) -> tuple[float, float]:
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


def geocode_address(address: str) -> tuple[float, float]:
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
    # Cache-Lookup
    if address in _geocode_cache:
        cached = _geocode_cache[address]
        return cached["lat"], cached["lon"]

    errors = []

    # Bereinigte Adresse
    cleaned = clean_address(address)

    print("cleaned:", cleaned)

    # 1. Versuch: Nominatim mit bereinigter Adresse
    try:
        # TODO: ich kann auch ein dict mit einzelnen Elementen hier angeben, s.:
        #  https://geopy.readthedocs.io/en/stable/#nominatim
        lat1, lon1 = geocode_with_nominatim(cleaned)
    except ValueError as e:
        lat1 = lon1 = None
        errors.append(f"Nominatim (bereinigt): {e}")

    # 2. Versuch: Photon mit bereinigter Adresse
    if PHOTON_AVAILABLE:
        try:
            lat2, lon2 = geocode_with_photon(cleaned)
            print(lat1, lat2, lon1, lon2)
            if lat1:
                print(lat1 - lat2, lon1 - lon2)
                # wenn Angaben fast identisch, dann vertraue nominatim mehr
                # wenn weit auseinander, dann nehme nur die Stadt, s.u.
                # hinweis dafür, dass adresse gar nicht verstanden wurde
                if abs(lat1 - lat2) < 1.2 and abs(lon1 - lon2) < 0.6:
                    _geocode_cache[address] = {"lat": lat1, "lon": lon1}
                    save_geocode_cache(_geocode_cache)

                    return lat1, lon1
            else:
                _geocode_cache[address] = {"lat": lat2, "lon": lon2}
                save_geocode_cache(_geocode_cache)

                return lat2, lon2
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
