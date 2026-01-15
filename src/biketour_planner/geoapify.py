import requests
from dotenv import load_dotenv
import os

load_dotenv("secrets.env")

# Load API keys from environment
geoapify_api_key = os.getenv("GEOAPIFY_API_KEY")

# https://apidocs.geoapify.com/docs/places/#quick-start
# https://apidocs.geoapify.com/docs/places/


def find_top_tourist_sights(lat, lon):
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": "tourism.sights",  # Sehenswürdigkeiten
        "filter": f"circle:{lon},{lat},5000",  # Stadt
        "limit": 2,  # 5,
        "apiKey": geoapify_api_key,
    }

    response = requests.get(url, params=params)
    data = response.json()

    # print(data)

    for poi in data.get("features", []):
        props = poi["properties"]
        print(props)
        try:
            print(props["name"], props["lat"], props["lon"])
        except KeyError:
            print(props["lat"], props["lon"])

    return data


def get_names_as_comma_separated_string(data):
    cs_string = ""

    if data:
        for poi in data.get("features", []):
            props = poi["properties"]
            try:
                cs_string += props["name"] + ", "
            except KeyError:
                try:
                    cs_string += props["street"] + ", "
                except KeyError:
                    cs_string += f"({props['lat']}, {props['lon']})" + ", "

    return cs_string
