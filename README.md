# Bike Tour Planner

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code Quality](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)
[![Tests](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/tests.yml)
[![CodeQL](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/codeql.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Automated bike tour planning based on Booking.com confirmations,
GPX route files and BRouter routing.

## Features
- Parse booking confirmations (HTML)
- Geocode accommodation addresses
- Extend GPX bike routes automatically
- Offline routing with BRouter

## Requirements
- Docker (for BRouter)
- Python 3.9+
