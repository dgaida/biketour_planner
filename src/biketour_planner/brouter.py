"""BRouter API Integration für Offline-Fahrradrouting.

Dieses Modul stellt eine einfache Schnittstelle zum BRouter-Routing-Engine bereit.
BRouter ist ein Open-Source-Routing-Engine, der speziell für Fahrräder optimiert ist
und offline mit vorberechneten OpenStreetMap-Daten arbeitet.

BRouter muss separat als Docker-Container oder lokaler Server laufen und ist unter
http://localhost:17777 erreichbar.

Mehr Informationen:
    - BRouter Repository: https://github.com/abrensch/brouter
    - Routing-Daten: https://brouter.de/brouter/segments4/

Example:
    >>> from biketour_planner.brouter import route_to_address
    >>> # Route von München nach Garmisch berechnen
    >>> gpx_route = route_to_address(48.1351, 11.5820, 47.4917, 11.0953)
    >>> print(gpx_route[:100])  # Zeige ersten Teil der GPX-Daten
    <?xml version="1.0" encoding="UTF-8"?>...
"""

import requests


def route_to_address(lat_from: float, lon_from: float, lat_to: float, lon_to: float) -> str:
    """Berechnet eine Fahrradroute zwischen zwei Koordinaten mit BRouter.

    Diese Funktion sendet eine Anfrage an den lokalen BRouter-Server und erhält
    eine GPX-Route zurück, die mit dem "trekking"-Profil optimiert wurde.

    **BRouter-Profile:**
    Das "trekking"-Profil ist für Tourenräder optimiert und bevorzugt:
    - Asphaltierte Radwege und ruhige Straßen
    - Vermeidung stark befahrener Straßen
    - Moderate Steigungen
    - Schöne, landschaftliche Strecken

    **Voraussetzungen:**
    - BRouter-Server muss unter http://localhost:17777 laufen
    - Routing-Daten (.rd5 Dateien) für die Region müssen vorhanden sein

    Args:
        lat_from: Start-Breitengrad in Dezimalgrad (z.B. 48.1351 für München).
        lon_from: Start-Längengrad in Dezimalgrad (z.B. 11.5820 für München).
        lat_to: Ziel-Breitengrad in Dezimalgrad (z.B. 47.4917 für Garmisch).
        lon_to: Ziel-Längengrad in Dezimalgrad (z.B. 11.0953 für Garmisch).

    Returns:
        GPX-String mit der berechneten Route. Dieser kann direkt gespeichert oder
        mit gpxpy.parse() weiterverarbeitet werden.

    Raises:
        requests.exceptions.HTTPError: Wenn der BRouter-Server einen Fehler zurückgibt
            (z.B. 400 bei fehlenden Routing-Daten, 404 wenn Server nicht läuft).
        requests.exceptions.ConnectionError: Wenn BRouter-Server nicht erreichbar ist.
        requests.exceptions.Timeout: Wenn die Routenberechnung zu lange dauert.

    Example:
        >>> # Route von Berlin nach Potsdam
        >>> gpx_string = route_to_address(52.5200, 13.4050, 52.3906, 13.0645)
        >>>
        >>> # GPX in Datei speichern
        >>> with open("route.gpx", "w", encoding="utf-8") as f:
        ...     f.write(gpx_string)
        >>>
        >>> # Oder mit gpxpy weiterverarbeiten
        >>> import gpxpy
        >>> gpx = gpxpy.parse(gpx_string)
        >>> print(f"Distanz: {gpx.length_2d() / 1000:.1f} km")

    Note:
        - BRouter verwendet das WGS84-Koordinatensystem (wie GPS-Geräte)
        - Die Koordinatenreihenfolge ist (lat, lon), nicht (lon, lat)
        - Für andere Routing-Profile siehe BRouter-Dokumentation:
          https://github.com/abrensch/brouter/tree/master/misc/profiles2
    """
    url = "http://localhost:17777/brouter"
    params = {"lonlats": f"{lon_from},{lat_from}|{lon_to},{lat_to}", "profile": "trekking", "format": "gpx"}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.text
