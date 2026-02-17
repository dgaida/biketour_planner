# Tests

Dieses Projekt verwendet `pytest` für automatisierte Tests.

## Tests ausführen

Führen Sie alle Tests aus dem Projektstamm aus:

```bash
export PYTHONPATH=$(pwd)/src
pytest
```

## Test-Struktur

- `tests/unit/`: Unit-Tests für einzelne Module.
- `tests/integration/`: Integrationstests, die das Zusammenspiel mehrerer Komponenten prüfen.

## Abdeckung (Coverage)

Um einen Abdeckungsbericht zu generieren:

```bash
pytest --cov=src --cov-report=html
```

Der Bericht wird in `htmlcov/index.html` verfügbar sein.

## CI/CD

Tests werden automatisch bei jedem Push und Pull Request über GitHub Actions ausgeführt.
