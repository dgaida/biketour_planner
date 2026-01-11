from geopy.geocoders import Nominatim
from time import sleep

geolocator = Nominatim(user_agent="booking-gpx-project")


def geocode_address(address):
    location = geolocator.geocode(address)
    sleep(1)  # Nominatim-Ratelimit
    if not location:
        raise ValueError(f"Adresse nicht gefunden: {address}")
    return location.latitude, location.longitude
