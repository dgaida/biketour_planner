# Dokumentationsmetriken

Hier werden die Qualitätsmetriken der Dokumentation verfolgt.

## API-Abdeckung

![Interrogate Badge](../badges/interrogate.svg)

Die aktuelle Abdeckung der Docstrings kann lokal mit folgendem Befehl geprüft werden:

```bash
interrogate -v src
```

## Build-Status

Die Dokumentation wird automatisch über GitHub Actions gebaut und veröffentlicht.

## Link-Prüfung

Regelmäßige Prüfungen auf defekte Links werden im CI-Prozess durchgeführt.
