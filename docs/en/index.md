# Bike Tour Planner

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code Quality](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)

---

## Overview

**Bike Tour Planner** is a Python-based toolchain for planning long-distance bike tours by combining:

* real-world accommodation data (Booking.com & Airbnb HTML confirmations),
* existing GPX tracks of your planned or ridden tour,
* **offline bicycle routing** using **BRouter**,
* tourist attractions discovery via Geoapify API,
* and automated mountain pass detection.

The main goal is to **automatically extend and connect GPX routes** so that they lead precisely to booked accommodations, while also collecting useful tour statistics such as distance, elevation gain, and highest point. The planner generates professional PDF reports with elevation profiles, clickable maps, and comprehensive tour information.

---

## Key Features

* 📄 **Parse Booking.com & Airbnb confirmations (HTML)**
* 🌍 **Smart Geocoding**
* 🗺️ **Advanced GPX Route Management**
* 🚴 **Offline Bicycle Routing with BRouter**
* 🏔️ **Mountain Pass Integration**
* 🎯 **Tourist Sights Discovery**
* 📊 **Professional Export Options**

---

## Installation

See [Installation](installation.md) and [Getting Started](getting-started.md).

---

## Typical Workflow

### 1. Prepare Your Data

```
biketour_planner/
├── booking/                    # Place Booking.com/Airbnb HTML files here
├── gpx/                        # Place your GPX route files here
```

### 2. Configure `main.py` or `config.yaml`

See [Configuration](configuration.md).

### 3. Run the Planner

```bash
python main.py
```

---

## Documentation

- [Architecture](architecture/index.md)
- [API Reference](api/index.md)
- [Testing](development/testing.md)
- [Troubleshooting](troubleshooting.md)

---

## License

This project is licensed under the **MIT License**. See `LICENSE` for details.
