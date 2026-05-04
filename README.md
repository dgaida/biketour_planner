# Bike Tour Planner

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code Quality](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)
[![Tests](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml)
[![CodeQL](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://dgaida.github.io/biketour_planner/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/dgaida/biketour_planner/graphs/commit-activity)
![Last commit](https://img.shields.io/github/last-commit/dgaida/biketour_planner)
[![Version](https://img.shields.io/github/v/tag/dgaida/biketour_planner?label=version)](https://github.com/dgaida/biketour_planner/tags)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/main/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)

**Bike Tour Planner** is a Python-based toolchain for planning long-distance bike tours by combining:

* real accommodation data (Booking.com & Airbnb HTML confirmations),  
* existing GPX tracks of your planned or ridden tour,  
* **offline bike routing** with **BRouter**,  
* tourist attraction discovery via Geoapify API,  
* and automatic mountain pass detection.  

The main goal is to **automatically extend and connect GPX routes** so they lead precisely to the booked accommodations, while collecting useful tour statistics like distance, elevation gain, and highest point. The planner generates professional PDF reports with elevation profiles, clickable maps, and comprehensive tour information.

## 📖 Documentation

Full documentation is available at [https://dgaida.github.io/biketour_planner/](https://dgaida.github.io/biketour_planner/)

* [Installation Guide](https://dgaida.github.io/biketour_planner/latest/installation/)  
* [Getting Started](https://dgaida.github.io/biketour_planner/latest/getting-started/)  
* [Usage & Examples](https://dgaida.github.io/biketour_planner/latest/usage/)  
* [Configuration](https://dgaida.github.io/biketour_planner/latest/configuration/)  
* [API Reference](https://dgaida.github.io/biketour_planner/latest/api/)  

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Install package
pip install -e .

# Run the planner (requires BRouter)
python main.py
```

## 🏔️ Main Features

* 📄 **Parsing of Booking.com & Airbnb confirmations (HTML)**  
* 🌍 **Intelligent Geocoding**  
* 🗺️ **Advanced GPX Route Management**  
* 🚴 **Offline Bike Routing with BRouter**  
* 🏔️ **Mountain Pass Integration**  
* 🎯 **Tourist Sight Discovery**  
* 📊 **Professional PDF & Excel Exports**  

## 📁 Project Structure

```
├── pyproject.toml                       # Project configuration
├── requirements.txt                     # Python dependencies
├── environment.yml                      # Conda environment
├── setup_precommit.sh                   # Pre-commit setup script
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

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) and our [Development Documentation](https://dgaida.github.io/biketour_planner/latest/development/testing/).

## 🗺️ Roadmap

Planned features:

- [ ] Web UI for easier configuration  
- [ ] Support for more booking platforms (hotels.com, etc.)  
- [ ] Interactive map visualization  
- [ ] Weather forecast integration  
- [ ] Bike shop finder along the route  
- [ ] Automatic backup/sync to cloud storage  
- [ ] Mobile app for on-tour navigation  

## 🙏 Acknowledgements

* **BRouter** – Offline routing engine ([https://github.com/abrensch/brouter](https://github.com/abrensch/brouter))  
* **OpenStreetMap contributors** – Underlying map data  
* **Geoapify** – Places API for tourist attractions  
* **Booking.com & Airbnb** – Data source for accommodation confirmations  

## 📜 License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

**Happy Touring! 🚴‍♂️🏔️**
