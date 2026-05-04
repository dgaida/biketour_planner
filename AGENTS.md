# AGENTS.md

This file provides context and instructions for AI coding agents working on the **Bike Tour Planner** project.

---

## Project Overview

**Bike Tour Planner** is a Python package (`src/biketour_planner/`) for planning long-distance bike tours. It parses Booking.com and Airbnb HTML confirmation emails, chains GPX tracks together, routes to accommodations via BRouter (offline bicycle routing engine), detects mountain passes, queries tourist attractions via Geoapify, and exports the result as a PDF (with elevation profiles), ICS calendar, or Excel spreadsheet.

Key entry point: `main.py`. Core package lives under `src/biketour_planner/`.

---

## Dev Environment Setup

```bash
# Clone and install in editable mode
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner
pip install -e .
pip install pytest pytest-cov pytest-mock pytest-asyncio

# Optional: install pre-commit hooks
./setup_precommit.sh
```

If you use conda/mamba:
```bash
conda env create -f environment.yml
conda activate biketour_planner
```

Set the Python path when running tests from the repo root:
```bash
export PYTHONPATH=$(pwd)/src
```

For tourist-sight discovery, create a `secrets.env` file:
```
GEOAPIFY_API_KEY=your_api_key_here
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run a single test file
pytest tests/test_brouter.py -v

# Run a single test by name
pytest -k "test_route_to_address_success" -v

# Run only unit tests (skip integration tests)
pytest -m "not integration"
```

All tests must pass before committing. Add or update tests for any code you change.

---

## Code Style

This project uses **Black** (line length 127) and **Ruff** for linting.

```bash
# Format code
black . --line-length=127

# Check formatting without applying
black --check --diff .

# Lint with Ruff
ruff check .

# Type checking (relaxed mode, continue-on-error in CI)
mypy src --ignore-missing-imports --no-strict-optional
```

Key conventions:  
- Line length: **127 characters**  
- **Google-style docstrings** on all public classes and methods (Args, Returns, Raises, Example)  
- Type annotations on all function signatures  
- No `from __future__ import annotations` unless already present in the file  
- Imports sorted with `isort` (profile: `black`)  

---

## Project Structure

```
src/biketour_planner/
├── __init__.py
├── brouter.py              # BRouter API integration (offline routing)
├── config.py               # YAML config loader (singleton via get_config())
├── constants.py            # Central constants
├── elevation_calc.py       # Elevation gain calculation methods
├── elevation_profiles.py   # Matplotlib elevation profile generation for PDF
├── excel_export.py         # Excel export
├── excel_hyperlinks.py     # Excel hyperlink utilities
├── excel_info_reader.py    # Read additional trip info from xlsx
├── exceptions.py           # Custom exceptions
├── geoapify.py             # Geoapify Places API
├── geocode.py              # Address geocoding (Nominatim / Photon)
├── gpx_route_manager.py    # Main route management class (GPXRouteManager)
├── gpx_route_manager_static.py  # Static GPX helper functions
├── gpx_utils.py            # Wrapper for compatibility
├── ics_export.py           # ICS calendar export
├── logger.py               # Centralized logging (get_logger())
├── models.py               # Pydantic models + dataclasses
├── parse_booking.py        # Parse Booking.com / Airbnb HTML confirmations
├── pass_finder.py          # Mountain pass detection
├── pdf_export.py           # PDF export with reportlab
└── utils/
    └── cache.py            # JSON-based caching decorator
```

---

## Architecture Notes

- **Configuration** is always accessed via `get_config()` (singleton). Never hardcode paths or parameters; read from the `Config` object.  
- **Logging** is always via `get_logger()`. Never use `print()` for debug/info output in library code (only `main.py` uses `print()` for user-facing messages).  
- **Caching**: geocoding and Geoapify results are cached to `output/geocode_cache.json` and `output/geoapify_cache.json` via the `@json_cache` decorator.  
- **External services**: BRouter must be running locally (default: `http://localhost:17777`). Tests mock all external HTTP calls with `unittest.mock.patch`.  
- **GPX processing**: `GPXRouteManager` preprocesses all GPX files into an in-memory index on init. Never re-read files inside hot loops.  
- **Booking data** flows as plain Python dicts (not Pydantic models) through most of the pipeline, for JSON serialisability. The `Booking` Pydantic model exists for validation only.  

---

## Adding New Features

- Place new source files in `src/biketour_planner/`.  
- Add corresponding test files in `tests/test_<module>.py`.  
- Update `docs/de/api/index.md` and `docs/en/api/index.md` with `:::` autodoc entries.  
- Export public symbols from `__init__.py` if they form part of the public API.  
- Keep docstring coverage above 95% (`interrogate src/biketour_planner`).  

---

## Testing Instructions

- Tests live in `tests/`. Unit tests cover individual modules; integration/E2E tests are marked with `@pytest.mark.integration`.  
- Mock **all** external services (BRouter, Geoapify, Nominatim). Never make real network calls in tests.  
- Use `tmp_path` (pytest fixture) for temporary files; never write to the project directory.  
- When patching module-level globals (e.g., `_geoapify_cache`), always reset them in the test to avoid state leaking between tests.  
- The `output/` directory is listed in `.gitignore` and is created at runtime; never commit files from it.  

---

## PR / Commit Guidelines

- Follow **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, etc.  
- Run `black --check .`, `ruff check .`, and `pytest` before pushing.  
- Do not commit `secrets.env`, `.env`, or any file under `output/`.  
- For a full multi-platform test matrix, include `[full-test]` or `[full ci]` in the commit message.  

---

## Known Gotchas

- `elevation_profiles.py` uses `matplotlib` with the `Agg` backend (no GUI). Always call `matplotlib.use("Agg")` before importing pyplot, or use `matplotlib.figure.Figure` directly (as the code already does).  
- `pdf_export.py` tries to register DejaVu fonts; it falls back to Helvetica silently if they are missing. Do not break this fallback chain.  
- `brouter.py` calls BRouter with `format=geojson` for `get_route2address_with_stats` (surface statistics) and `format=gpx` for plain routing. Keep these separate.  
- The `json_cache` decorator checks for `"non_existent.json"` in the path string as a heuristic to skip disk writes during tests. Always pass `Path("non_existent.json")` as `GEOAPIFY_CACHE_FILE` / `GEOCODE_CACHE_FILE` when patching in tests.  
- `GPXRouteManager` uses `ThreadPoolExecutor` internally for preprocessing. Tests that create a `GPXRouteManager` with real GPX files on `tmp_path` are safe; tests that mock `read_gpx_file` inside the executor need `patch` to be active before the manager is instantiated.  
