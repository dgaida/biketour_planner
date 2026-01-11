# Bike Tour Planner

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code Quality](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)
[![Tests](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml)
[![CodeQL](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Overview

**Bike Tour Planner** is a Python-based toolchain for planning long-distance bike tours by combining:

* real-world accommodation data (Booking.com HTML confirmations),
* existing GPX tracks of your planned or ridden tour,
* and **offline bicycle routing** using **BRouter**.

The main goal is to **automatically extend and connect GPX routes** so that they lead precisely to booked accommodations, while also collecting useful tour statistics such as distance, elevation gain, and highest point.

This project is especially useful for **multi-day bike tours**, bikepacking, or long-distance cycling trips where routes and accommodations evolve independently.

---

## Key Features

* 📄 **Parse Booking.com confirmations (HTML)**

  * Arrival and departure dates
  * Accommodation name and address
  * Earliest check-in time
  * Amenities (kitchen, washing machine)
  * Last date for free cancellation

* 🌍 **Geocode accommodation addresses**

  * Convert postal addresses into latitude/longitude coordinates

* 🗺️ **GPX route analysis & manipulation**

  * Find the GPX file and exact point closest to an accommodation
  * Chain multiple GPX files to represent multi-day routes
  * Compute:

    * total distance (km)
    * total ascent (positive elevation gain)
    * highest elevation reached

* 🚴 **Offline bicycle routing with BRouter**

  * Compute a precise route from an existing GPX track to the accommodation
  * Insert the route at the correct position inside the GPX file
  * Preserve and extend your original GPX tracks

---

## Project Structure

```text
biketour_planner/
├── main.py
├── pyproject.toml
├── requirements.txt
├── environment.yml
├── src/
│   └── biketour_planner/
│       ├── parse_booking.py
│       ├── geocode.py
│       ├── gpx_utils.py
│       └── brouter.py
├── booking/          # Booking.com HTML confirmations
├── gpx/              # Original GPX route files
├── output/
│   ├── bookings.json
│   └── gpx_modified/
└── LICENSE
```

---

## Installation

### Option 1: pip

```bash
pip install -r requirements.txt
pip install -e .
```

### Option 2: Conda / Mamba

```bash
conda env create -f environment.yml
conda activate biketour_planner
```

Python **3.9 or newer** is required.

---

## BRouter Setup (Required)

Bike Tour Planner relies on **BRouter** for offline bicycle routing.

BRouter is an open-source routing engine developed by Arne Brenschede:
👉 [https://github.com/abrensch/brouter](https://github.com/abrensch/brouter)

### 1. Download routing data (`.rd5` files)

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

### 2. Start BRouter via Docker

A running BRouter HTTP server is required.

Example:

```bash
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

---

## Typical Workflow

1. Place Booking.com confirmation HTML files into `booking/`
2. Place your existing GPX route files into `gpx/`
3. Start the BRouter Docker container
4. Run the planner:

```bash
python main.py
```

5. Results:

   * `output/bookings.json` – structured booking & tour metadata
   * `output/gpx_modified/` – GPX files extended to accommodations

---

## Data Produced

For each accommodation/day, the planner records:

* accommodation name & address
* arrival / departure dates
* coordinates (lat/lon)
* list of GPX files used for that day
* total distance (km)
* total ascent (m)
* maximum elevation (m)

---

## Limitations & Assumptions

* GPX files are assumed to be ordered in riding direction
* Route chaining is based on spatial proximity of track endpoints
* Elevation data must be present in GPX files
* BRouter must be running locally

---

## Acknowledgements

* **BRouter** – offline routing engine

  * [https://github.com/abrensch/brouter](https://github.com/abrensch/brouter)
* **OpenStreetMap contributors** – underlying map data
* **Booking.com** – data source for accommodation confirmations

---

## License

This project is licensed under the **MIT License**. See `LICENSE` for details.
