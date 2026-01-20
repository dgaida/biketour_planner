# Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_gpx_route_manager.py -v
```

**Test Coverage:**
- `test_brouter.py`: BRouter API integration
- `test_geoapify.py`: Tourist sights discovery
- `test_parse_booking.py`: HTML parsing (Booking.com/Airbnb)
- `test_gpx_route_manager.py`: Route management core
- `test_gpx_route_manager_static.py`: GPX utilities
- `test_excel_export.py`: Excel export functionality
