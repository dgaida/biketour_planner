# Bedienungsanleitung

Dieser Leitfaden deckt den typischen Arbeitsablauf, Anwendungsbeispiele und erweiterte Funktionen des Bike Tour Planners ab.

## Typischer Arbeitsablauf

### 1. Daten vorbereiten

```
biketour_planner/
├── booking/                    # Booking.com/Airbnb HTML-Dateien hier ablegen
│   ├── Hotel_Muenchen.html
│   ├── Hotel_Garmisch.html
│   └── Reiseplanung_Fahrrad.xlsx  # (Optional) Zusätzliche Reiseinfos
├── gpx/                        # GPX-Routendateien hier ablegen
│   ├── Tag1_Muenchen_Tegernsee.gpx
│   ├── Tag2_Tegernsee_Achensee.gpx
│   ├── Tag3_Achensee_Garmisch.gpx
│   └── Paesse.json            # (Optional) Passdatenbank
```

**Beispiel `Paesse.json`:**
```json
[
  {"passname": "Achenpass, Tirol, Österreich"},
  {"passname": "Kesselberg, Bayern, Deutschland"}
]
```

**Beispiel `Reiseplanung_Fahrrad.xlsx` (Spalte B = Datum, Spalte C = Info):**
```
A         B              C
Tag       Datum          Infos
1         2026-05-15     Markt besuchen; https://example.com/restaurant
2         2026-05-16     Früh losfahren
```

### 2. `main.py` konfigurieren

Passen Sie die Pfade in `main.py` an:

```python
BOOKING_DIR = Path("../2026_Kroatien/booking")
GPX_DIR = Path("../2026_Kroatien/gpx")
OUT_DIR = Path("../2026_Kroatien/gpx_modified")
```

### 3. BRouter starten

```bash
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

### 4. Planer ausführen

```bash
python main.py
```

### 5. Ergebnisse

Der Planer generiert:

* `output/bookings.json` – Strukturierte Buchungs- & Tourmetadaten  
* `output/gpx_modified/` – Erweiterte GPX-Dateien (eine pro Tag)  
* `output/Reiseplanung_*.pdf` – Professioneller PDF-Bericht mit:  
  * Täglicher Reiseplan-Tabelle  
  * Höhenprofilen für Routen und Pässe  
  * Anklickbaren Links zu Sehenswürdigkeiten  
  * Zusammenfassenden Statistiken  

---

## Anwendungsbeispiele

### Grundlegende Tourenplanung

```python
from pathlib import Path
from biketour_planner.gpx_route_manager import GPXRouteManager

# Routenmanager initialisieren
manager = GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/gpx_modified/"),
    max_connection_distance_m=1000  # Maximaler Abstand für automatische Verkettung
)

# Alle Buchungen verarbeiten
bookings = [
    {
        "arrival_date": "2026-05-15",
        "hotel_name": "Hotel München",
        "latitude": 48.1351,
        "longitude": 11.5820
    },
    {
        "arrival_date": "2026-05-16",
        "hotel_name": "Hotel Garmisch",
        "latitude": 47.4917,
        "longitude": 11.0953
    }
]

result = manager.process_all_bookings(bookings, Path("output/gpx_modified/"))
```

### Benutzerdefinierte Passerkennung

```python
from biketour_planner.pass_finder import process_passes

bookings = process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,  # Suchradius um Hotels
    pass_radius_km=5.0    # Suchradius um Pässe
)
```

### PDF-Bericht erstellen

```python
from biketour_planner.pdf_export import export_bookings_to_pdf

export_bookings_to_pdf(
    json_path=Path("output/bookings.json"),
    output_path=Path("output/Touren_Bericht.pdf"),
    output_dir=Path("output/gpx_modified/"),
    gpx_dir=Path("gpx/"),
    title="Kroatien Radtour 2026",
    excel_info_path=Path("booking/Reiseplanung_Fahrrad.xlsx")
)
```

---

## Erzeugte Daten

Für jede Unterkunft/jeden Tag zeichnet der Planer folgendes auf:

* **Unterkunftsdetails:**  
  * Name, Adresse, Telefon  
  * Ankunfts-/Abreisedaten  
  * Check-in-Zeit  
  * Ausstattung (Küche, Waschmaschine, Frühstück)  
  * Stornierungsfrist  
  * Gesamtpreis  
  * GPS-Koordinaten  

* **Routeninformationen:**  
  * Liste der verwendeten GPX-Dateien  
  * Gesamtstrecke (km)  
  * Gesamtaufstieg und -abstieg (m)  
  * Maximale Höhe (m)  
  * Dateiname der finalen zusammengeführten GPX-Datei  

* **Gebirgspässe:**  
  * Passname und Koordinaten  
  * Entfernung zum Pass  
  * Höhengewinn bis zum Gipfel  
  * Zugehöriger GPX-Track  

* **Sehenswürdigkeiten:**  
  * Namen und Koordinaten  
  * Google Maps Links  

---

## Erweiterte Funktionen

### Intelligente Routenverkettung

Der Planer verwendet einen ausgeklügelten Algorithmus, um mehrere GPX-Tracks zu verbinden:

1. **Bestimmung der Zielseite**: Identifiziert, welches Ende des Ziel-Tracks näher am Start liegt.  
2. **Startpunkt-Optimierung**: Navigiert zur relevanten Seite des Ziels, nicht nur zum nächstgelegenen Punkt.  
3. **Automatische Richtungserkennung**: Bestimmt, ob Tracks vorwärts oder rückwärts durchfahren werden sollen.  
4. **Mehrtägige Kontinuität**: Setzt Routen von den Vortagen nahtlos fort.  

### Methoden zur Höhenberechnung

Drei Methoden zur Höhenberechnung stehen zur Verfügung:

1. **Einfach mit Schwellenwert** (`calculate_elevation_gain_simple`):  
   - Schnell, ignoriert GPS-Rauschen unterhalb eines Schwellenwerts.  

2. **Geglättet** (`calculate_elevation_gain_smoothed`):  
   - Gleitender Mittelwert + Schwellenwert.  
   - Empfohlen für die meisten Anwendungsfälle.  

3. **Segmentbasiert** (`calculate_elevation_gain_segment_based`):  
   - Am genauesten, identifiziert kontinuierliche Anstiege/Abstiege.  
   - Standardmäßig im Planer verwendet.  

### Farbcodierte Stornierungsfristen

In PDF-Berichten sind Stornierungsdaten farblich gekennzeichnet:

* 🟢 **Grün**: < 7 Tage vor Ankunft (flexibel)  
* ⚫ **Schwarz**: 7-30 Tage vor Ankunft (moderat)  
* 🔴 **Rot**: > 30 Tage vor Ankunft (unflexibel)  

### Konfigurationsparameter

#### Parameter für den Routenmanager

```python
GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/"),
    max_connection_distance_m=1000,  # Max. Distanz für autom. Verkettung
    max_chain_length=20              # Max. Tracks pro Route
)
```

#### Parameter für die Passsuche

```python
process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,    # Suchradius um Hotels
    pass_radius_km=5.0      # Suchradius um Passgipfel
)
```

#### Parameter für Sehenswürdigkeiten

```python
find_top_tourist_sights(
    lat=43.5081,
    lon=16.4402,
    radius=5000,  # Suchradius in Metern
    limit=2       # Max. Anzahl an POIs
)
```
