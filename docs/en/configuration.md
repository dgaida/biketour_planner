# Configuration

Configuration is managed via a `config.yaml` file in the project root. If no file is present, default values are used.

## Example `config.yaml`

```yaml
directories:
  booking: "../2026_Croatia/booking"
  gpx: "../2026_Croatia/gpx"
  output: "../2026_Croatia/output"

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
  title: "Croatia Bike Tour 2026"
  excel_info_file: "Reiseplanung_Fahrrad.xlsx"

logging:
  level: "INFO"
  file: "logs/app.log"
```

## Configuration Options

### Directories (`directories`)
- `booking`: Path to HTML booking confirmations.
- `gpx`: Path to original GPX tracks.
- `output`: Path for generated files (PDF, merged GPX).

### Routing (`routing`)
- `brouter_url`: URL of the BRouter server.
- `max_connection_distance_m`: Maximum distance between two tracks for automatic chaining.
- `max_chain_length`: Maximum number of tracks to chain for a daily route.
- `start_search_radius_km`: Search radius around the starting point to find the first track.
- `target_search_radius_km`: Search radius around the accommodation to find the target track.

### Mountain Passes (`passes`)
- `hotel_radius_km`: Search radius around hotels for passes.
- `pass_radius_km`: Search radius around the pass summit.
- `passes_file`: Name of the JSON file containing passes in the GPX directory.

### Geoapify (`geoapify`)
- `search_radius_m`: Search radius for tourist attractions in meters.
- `max_pois`: Maximum number of attractions per accommodation.

### Export (`export`)
- `title`: Title of the PDF report.
- `excel_info_file`: Name of an optional Excel file with additional trip info.

## Secrets (`secrets.env`)

For API keys, create a `secrets.env` file:

```env
GEOAPIFY_API_KEY=your_api_key_here
```
