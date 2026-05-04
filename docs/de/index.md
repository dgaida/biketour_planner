# Bike Tour Planner

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/dgaida/biketour_planner/branch/master/graph/badge.svg)](https://codecov.io/gh/dgaida/biketour_planner)
[![Code-Qualität](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml/badge.svg)](https://github.com/dgaida/biketour_planner/actions/workflows/lint.yml)

---

## Übersicht

**Bike Tour Planner** ist eine Python-basierte Toolchain zur Planung von Langstrecken-Radtouren durch die Kombination von:

* realen Unterkunftsdaten (Booking.com & Airbnb HTML-Bestätigungen),  
* existierenden GPX-Tracks Ihrer geplanten oder gefahrenen Tour,  
* **Offline-Fahrrad-Routing** mit **BRouter**,  
* Entdeckung von Touristenattraktionen über die Geoapify-API,  
* und automatischer Passerkennung.  

Das Hauptziel besteht darin, **GPX-Routen automatisch zu erweitern und zu verbinden**, sodass sie präzise zu den gebuchten Unterkünften führen, während gleichzeitig nützliche Tourstatistiken wie Distanz, Höhengewinn und höchster Punkt gesammelt werden. Der Planer generiert professionelle PDF-Berichte mit Höhenprofilen, anklickbaren Karten und umfassenden Tourinformationen.

---

## Hauptmerkmale

* 📄 **Parsing von Booking.com & Airbnb Bestätigungen (HTML)**  
* 🌍 **Intelligente Geokodierung**  
* 🗺️ **Erweitertes GPX-Routenmanagement**  
* 🚴 **Offline-Fahrrad-Routing mit BRouter**  
* 🏔️ **Integration von Gebirgspässen**  
* 🎯 **Entdeckung von Sehenswürdigkeiten**  
* 📊 **Professionelle Exportoptionen**  

---

## Installation

Siehe [Installation](installation.md) und [Erste Schritte](getting-started.md).

---

## Typischer Workflow

### 1. Daten vorbereiten

```
biketour_planner/
├── booking/                    # Booking.com/Airbnb HTML-Dateien hier ablegen
├── gpx/                        # GPX-Routendateien hier ablegen
```

### 2. Konfiguration

Siehe [Konfiguration](configuration.md).

### 3. Planer ausführen

```bash
python main.py
```

---

## Dokumentation

- [Architektur](architecture/index.md)  
- [API-Referenz](api/index.md)  
- [Tests](development/testing.md)  
- [Fehlerbehebung](troubleshooting.md)  

---

## Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert. Siehe `LICENSE` für Details.
