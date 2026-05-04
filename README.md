# Bike Tour Planner

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code Quality](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)

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

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) and our [Development Documentation](https://dgaida.github.io/biketour_planner/latest/development/testing/).

## 📜 License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

**Happy Touring! 🚴‍♂️🏔️**
