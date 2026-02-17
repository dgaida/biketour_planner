# Testing

This project uses `pytest` for automated testing.

## Running Tests

Run all tests from the project root:

```bash
export PYTHONPATH=$(pwd)/src
pytest
```

## Test Structure

- `tests/unit/`: Unit tests for individual modules.
- `tests/integration/`: Integration tests checking the interaction between components.

## Coverage

To generate a coverage report:

```bash
pytest --cov=src --cov-report=html
```

The report will be available in `htmlcov/index.html`.

## CI/CD

Tests are automatically executed on every push and pull request via GitHub Actions.
