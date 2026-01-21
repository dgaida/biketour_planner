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

* real-world accommodation data (Booking.com & Airbnb HTML confirmations),
* existing GPX tracks of your planned or ridden tour,
* **offline bicycle routing** using **BRouter**,
* tourist attractions discovery via Geoapify API,
* and automated mountain pass detection.

The main goal is to **automatically extend and connect GPX routes** so that they lead precisely to booked accommodations, while also collecting useful tour statistics such as distance, elevation gain, and highest point. The planner generates professional PDF reports with elevation profiles, clickable maps, and comprehensive tour information.

This project is especially useful for **multi-day bike tours**, bikepacking, or long-distance cycling trips where routes and accommodations evolve independently.

---

## Key Features

* 📄 **Parse Booking.com & Airbnb confirmations (HTML)**

  * Arrival and departure dates
  * Accommodation name and address
  * Earliest check-in time
  * Amenities (kitchen, washing machine, breakfast)
  * Last date for free cancellation
  * GPS coordinates (when available)

* 🌍 **Smart Geocoding**

  * Convert postal addresses to latitude/longitude coordinates
  * Multiple fallback strategies (Nominatim, Photon)
  * Automatic address cleaning and validation
  * Robust error handling for problematic addresses

* 🗺️ **Advanced GPX Route Management**

  * **Intelligent Route Chaining**: Automatically connects multiple GPX tracks based on spatial proximity
  * **Direction Detection**: Determines optimal track direction (forward/backward)
  * **Multi-Day Tour Support**: Continues routes from previous days seamlessly
  * **Comprehensive Statistics**:
    * Total distance (km)
    * Total ascent and descent (m)
    * Maximum elevation reached (m)
    * Segment-based elevation calculation with smoothing

* 🚴 **Offline Bicycle Routing with BRouter**

  * Compute precise routes from existing GPX tracks to accommodations
  * Automatic route extension to hotel coordinates
  * Trekking profile optimized for bicycle touring
  * Preserve and intelligently merge GPX tracks

* 🏔️ **Mountain Pass Integration**

  * Automatic detection of mountain passes along the route
  * Pass-specific statistics (elevation gain, distance)
  * Association with nearest accommodations
  * Support for custom pass databases (JSON format)

* 🎯 **Tourist Sights Discovery**

  * Integration with Geoapify Places API
  * Automatic discovery of tourist attractions near accommodations
  * Configurable search radius
  * Direct Google Maps links in exports

* 📊 **Professional Export Options**

  * **PDF Export**:
    * Landscape format for optimal readability
    * Clickable links to tourist sights and passes
    * Color-coded cancellation deadlines (flexible/inflexible)
    * Elevation profiles for all routes and passes
    * Summary statistics (total km, elevation, costs)
  * **Excel Export** (alternative):
    * Pre-formatted template support
    * Automatic gap days insertion
    * Hyperlinks to tourist attractions
  * **Merged GPX Files**:
    * One GPX file per day with complete route
    * Ready for GPS device upload

---

## Project Structure

```text
biketour_planner/
├── main.py                              # Main entry point
├── pyproject.toml                       # Project configuration
├── requirements.txt                     # Python dependencies
├── environment.yml                      # Conda environment
├── setup_precommit.sh                   # Pre-commit setup script
├── start_biketour_planner.bat          # Windows launcher
├── src/
│   └── biketour_planner/
│       ├── parse_booking.py            # Parse Booking.com/Airbnb HTML
│       ├── geocode.py                  # Address geocoding with fallbacks
│       ├── gpx_utils.py                # GPX utilities wrapper
│       ├── gpx_route_manager.py        # Main route management class
│       ├── gpx_route_manager_static.py # Static GPX helper functions
│       ├── brouter.py                  # BRouter API integration
│       ├── elevation_calc.py           # Advanced elevation calculations
│       ├── elevation_profiles.py       # Elevation profile generation
│       ├── pass_finder.py              # Mountain pass detection
│       ├── geoapify.py                 # Tourist sights API
│       ├── pdf_export.py               # PDF report generation
│       ├── excel_export.py             # Excel export (alternative)
│       ├── excel_hyperlinks.py         # Excel hyperlink utilities
│       ├── excel_info_reader.py        # Read additional trip info
│       └── logger.py                   # Centralized logging
├── booking/                             # (Optional) Booking HTML files
├── gpx/                                 # (Optional) Original GPX files
├── brouter_docker/                      # Dockerfile for BRouter
├── logs/                                # Application logs
├── output/
│   ├── bookings.json                   # Processed booking data
│   ├── gpx_modified/                   # Extended GPX files
│   └── Reiseplanung_*.pdf             # Generated PDF report
└── tests/                               # Unit and integration tests
```

---

## Installation

### Option 1: pip

```bash
# Clone repository
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Option 2: Conda / Mamba

```bash
# Clone repository
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Create and activate environment
conda env create -f environment.yml
conda activate biketour_planner
```

For detailed installation instructions see [docs/Installation.md](docs/Installation.md).

---

## Typical Workflow

### 1. Prepare Your Data

```
biketour_planner/
├── booking/                    # Place Booking.com/Airbnb HTML files here
│   ├── Hotel_Munich.html
│   ├── Hotel_Garmisch.html
│   └── Reiseplanung_Fahrrad.xlsx  # (Optional) Additional trip info
├── gpx/                        # Place your GPX route files here
│   ├── Day1_Munich_Tegernsee.gpx
│   ├── Day2_Tegernsee_Achensee.gpx
│   ├── Day3_Achensee_Garmisch.gpx
│   └── Paesse.json            # (Optional) Mountain pass database
```

**Example `Paesse.json`:**
```json
[
  {"passname": "Achenpass, Tirol, Österreich"},
  {"passname": "Kesselberg, Bayern, Deutschland"}
]
```

**Example `Reiseplanung_Fahrrad.xlsx` (Column B = Date, Column C = Info):**
```
A         B              C
Tag       Datum          Infos
1         2026-05-15     Markt besuchen; https://example.com/restaurant
2         2026-05-16     Früh losfahren
```

### 2. Configure `main.py`

Edit the paths in `main.py`:

```python
BOOKING_DIR = Path("../2026_Croatia/booking")
GPX_DIR = Path("../2026_Croatia/gpx")
OUT_DIR = Path("../2026_Croatia/gpx_modified")
```

### 3. Start BRouter

```bash
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

### 4. Run the Planner

```bash
python main.py
```

### 5. Results

The planner generates:

* `output/bookings.json` – Structured booking & tour metadata
* `output/gpx_modified/` – Extended GPX files (one per day)
* `output/Reiseplanung_*.pdf` – Professional PDF report with:
  * Daily itinerary table
  * Elevation profiles for routes and passes
  * Clickable links to tourist sights
  * Summary statistics

---

## Usage Examples

### Basic Tour Planning

```python
from pathlib import Path
from biketour_planner.gpx_route_manager import GPXRouteManager

# Initialize route manager
manager = GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/gpx_modified/"),
    max_connection_distance_m=1000  # Max distance for auto-chaining
)

# Process all bookings
bookings = [
    {
        "arrival_date": "2026-05-15",
        "hotel_name": "Hotel Munich",
        "latitude": 48.1351,
        "longitude": 11.5820
    },
    {
        "arrival_date": "2026-05-16",
        "hotel_name": "Hotel Garmisch",
        "latitude": 47.4917,
        "longitude": 11.0953
    }
]

result = manager.process_all_bookings(bookings, Path("output/gpx_modified/"))
```

### Custom Pass Detection

```python
from biketour_planner.pass_finder import process_passes

bookings = process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,  # Search radius around hotels
    pass_radius_km=5.0    # Search radius around passes
)
```

### Generate PDF Report

```python
from biketour_planner.pdf_export import export_bookings_to_pdf

export_bookings_to_pdf(
    json_path=Path("output/bookings.json"),
    output_path=Path("output/Tour_Report.pdf"),
    output_dir=Path("output/gpx_modified/"),
    gpx_dir=Path("gpx/"),
    title="Croatia Bike Tour 2026",
    excel_info_path=Path("booking/Reiseplanung_Fahrrad.xlsx")
)
```

---

## Data Produced

For each accommodation/day, the planner records:

* **Accommodation Details:**
  * Name, address, phone
  * Arrival/departure dates
  * Check-in time
  * Amenities (kitchen, washing machine, breakfast)
  * Cancellation deadline
  * Total price
  * GPS coordinates

* **Route Information:**
  * List of GPX files used
  * Total distance (km)
  * Total ascent and descent (m)
  * Maximum elevation (m)
  * Final merged GPX file name

* **Mountain Passes:**
  * Pass name and coordinates
  * Distance to pass
  * Elevation gain to summit
  * Associated GPX track

* **Tourist Attractions:**
  * Names and coordinates
  * Google Maps links

---

## Advanced Features

### Intelligent Route Chaining

The planner uses a sophisticated algorithm to connect multiple GPX tracks:

1. **Target Side Determination**: Identifies which end of the destination track is closer to the start
2. **Start Point Optimization**: Navigates to the relevant side of the destination, not just the nearest point
3. **Automatic Direction Detection**: Determines whether to traverse tracks forward or backward
4. **Multi-Day Continuity**: Seamlessly continues routes from previous days

### Elevation Calculation Methods

Three elevation calculation methods are available:

1. **Simple with Threshold** (`calculate_elevation_gain_simple`):
   - Fast, ignores GPS noise under threshold

2. **Smoothed** (`calculate_elevation_gain_smoothed`):
   - Moving average smoothing + threshold
   - Recommended for most use cases

3. **Segment-Based** (`calculate_elevation_gain_segment_based`):
   - Most accurate, identifies continuous climbs/descents
   - Used by default in the planner

### Color-Coded Cancellation Deadlines

In PDF reports, cancellation dates are color-coded:

* 🟢 **Green**: < 7 days before arrival (flexible)
* ⚫ **Black**: 7-30 days before arrival (moderate)
* 🔴 **Red**: > 30 days before arrival (inflexible)

---

## Configuration Options

### Route Manager Parameters

```python
GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/"),
    max_connection_distance_m=1000,  # Max auto-chain distance
    max_chain_length=20              # Max tracks per route
)
```

### Pass Finder Parameters

```python
process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,    # Search radius around hotels
    pass_radius_km=5.0      # Search radius around pass summit
)
```

### Tourist Sights Parameters

```python
find_top_tourist_sights(
    lat=43.5081,
    lon=16.4402,
    radius=5000,  # Search radius in meters
    limit=2       # Max number of POIs
)
```

---

## Testing

See [docs/TESTING.md](docs/TESTING.md)

---

## Limitations & Assumptions

* GPX files are assumed to be ordered chronologically
* Route chaining is based on spatial proximity of track endpoints
* Elevation data must be present in GPX files
* BRouter must be running locally on port 17777
* First booking in the list receives no route (no start point)
* Geocoding relies on external services (Nominatim, Photon)

---

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Acknowledgements

* **BRouter** – Offline routing engine
  * [https://github.com/abrensch/brouter](https://github.com/abrensch/brouter)
  * Developed by Arne Brenschede
* **OpenStreetMap contributors** – Underlying map data
* **Geoapify** – Places API for tourist attractions
  * [https://www.geoapify.com](https://www.geoapify.com)
* **Booking.com & Airbnb** – Data source for accommodation confirmations

---

## Roadmap

Planned features:

- [ ] Web UI for easier configuration
- [ ] Support for more booking platforms (hotels.com, etc.)
- [ ] Interactive map visualization
- [ ] Weather forecast integration
- [ ] Bike shop finder along the route
- [ ] Automatic backup/sync to cloud storage
- [ ] Mobile app for on-tour navigation

---

## License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

## Contact

**Daniel Gaida**  
📧 daniel.gaida@th-koeln.de  
🔗 [GitHub](https://github.com/dgaida/biketour_planner)

---

## Screenshots

*Coming soon: PDF report preview, elevation profiles, route visualization*

---

**Happy Touring! 🚴‍♂️🏔️**
