import requests


def route_to_address(lat_from, lon_from, lat_to, lon_to):
    url = "http://localhost:17777/brouter"
    params = {
        "lonlats": f"{lon_from},{lat_from}|{lon_to},{lat_to}",
        "profile": "trekking",
        "format": "gpx"
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.text
