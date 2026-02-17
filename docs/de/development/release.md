# Release-Workflow

Dieses Projekt verwendet [Conventional Commits](https://www.conventionalcommits.org/) und [git-cliff](https://git-cliff.org/) für automatisierte Changelog-Generierung.

## Commit-Konventionen

Commits sollten dem folgenden Format folgen:

- `feat: ...` für neue Funktionen.
- `fix: ...` für Fehlerbehebungen.
- `docs: ...` für Dokumentationsänderungen.
- `style: ...` für Formatierungsänderungen.
- `refactor: ...` für Code-Refactoring.
- `test: ...` für Tests.
- `chore: ...` für Wartungsaufgaben.

## Changelog generieren

Das Changelog kann manuell mit folgendem Befehl aktualisiert werden:

```bash
git-cliff -o CHANGELOG.md
```

## Neuen Release erstellen

1. Version in `pyproject.toml` erhöhen.
2. Changelog aktualisieren: `git-cliff -o CHANGELOG.md`.
3. Änderungen committen: `git commit -am "chore(release): prepare for vX.Y.Z"`.
4. Tag erstellen: `git tag vX.Y.Z`.
5. Pushen: `git push && git push --tags`.
