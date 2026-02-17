# Konfiguration

Die Konfiguration erfolgt über eine `config.yaml`-Datei im Projektstamm. Wenn keine Datei vorhanden ist, werden Standardwerte verwendet.

## Beispiel `config.yaml`

```yaml
directories:
  booking: "../2026_Kroatien/booking"
  gpx: "../2026_Kroatien/gpx"
  output: "../2026_Kroatien/output"

routing:
  brouter_url: "http://localhost:17777"
  max_connection_distance_m: 1000
  max_chain_length: 20
  start_search_radius_km: 3.0
  target_search_radius_km: 10.0

passes:
  hotel_radius_km: 5.0
  pass_radius_km: 5.0
  passes_file: "Paesse.json"

geoapify:
  search_radius_m: 5000
  max_pois: 2

export:
  title: "Kroatien Radtour 2026"
  excel_info_file: "Reiseplanung_Fahrrad.xlsx"

logging:
  level: "INFO"
  file: "logs/app.log"
```

## Konfigurations-Optionen

### Verzeichnisse (`directories`)
- `booking`: Pfad zu den HTML-Buchungsbestätigungen.
- `gpx`: Pfad zu den ursprünglichen GPX-Tracks.
- `output`: Pfad für generierte Dateien (PDF, merged GPX).

### Routing (`routing`)
- `brouter_url`: URL des BRouter-Servers.
- `max_connection_distance_m`: Maximale Distanz zwischen zwei Tracks, um sie automatisch zu verbinden.
- `max_chain_length`: Maximale Anzahl an Tracks, die für eine Tagesroute verkettet werden.
- `start_search_radius_km`: Suchradius um den Startpunkt, um den ersten Track zu finden.
- `target_search_radius_km`: Suchradius um die Unterkunft, um den Ziel-Track zu finden.

### Pässe (`passes`)
- `hotel_radius_km`: Suchradius um Hotels für Pässe.
- `pass_radius_km`: Suchradius um den Pass-Gipfel.
- `passes_file`: Name der JSON-Datei mit den Pässen im GPX-Verzeichnis.

### Geoapify (`geoapify`)
- `search_radius_m`: Suchradius für Sehenswürdigkeiten in Metern.
- `max_pois`: Maximale Anzahl an Sehenswürdigkeiten pro Unterkunft.

### Export (`export`)
- `title`: Titel des PDF-Berichts.
- `excel_info_file`: Name einer optionalen Excel-Datei mit Zusatzinformationen.

## Geheimnisse (`secrets.env`)

Für API-Schlüssel erstellen Sie eine `secrets.env`-Datei:

```env
GEOAPIFY_API_KEY=ihr_api_schlüssel_hier
```
