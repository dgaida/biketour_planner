# Installation

## Option 1: pip

```bash
# Clone repository
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

## Option 2: Conda / Mamba

```bash
# Clone repository
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Create and activate environment
conda env create -f environment.yml
conda activate biketour_planner
```

## Requirements

Python **3.9 or newer** is required.

## Optional: Enable Tourist Sights Discovery

To use the Geoapify integration for finding tourist attractions:

1. Create a free account at [https://www.geoapify.com](https://www.geoapify.com)
2. Get your API key (free tier: 3,000 requests/day)
3. Create a `secrets.env` file in the project root:

```bash
GEOAPIFY_API_KEY=your_api_key_here
```

---

# BRouter Setup (Required)

Bike Tour Planner relies on **BRouter** for offline bicycle routing.

BRouter is an open-source routing engine developed by Arne Brenschede:
👉 [https://github.com/abrensch/brouter](https://github.com/abrensch/brouter)

## 1. Download routing data (`.rd5` files)

BRouter uses preprocessed OpenStreetMap data split into **5° × 5° tiles**.

Download the required `.rd5` files from:

```
https://brouter.de/brouter/segments4/
```

Place them in a local directory, for example:

```text
C:/brouter/segments4/
```

Make sure to download all tiles covering your tour area.

---

## 2. Start BRouter via Docker

A running BRouter HTTP server is required.

### Using Docker (recommended):

```bash
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

### Or build from provided Dockerfile:

```bash
cd brouter_docker
docker build -t brouter .
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

The service will be available at:

```
http://localhost:17777
```

You can test it with:

```bash
curl "http://localhost:17777/brouter?lonlats=16.44,43.51|18.09,42.65&profile=trekking&format=gpx"
```
