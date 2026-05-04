# Usage Guide

This guide covers the typical workflow, usage examples, and advanced features of the Bike Tour Planner.

## Typical Workflow

### 1. Prepare Your Data

```
biketour_planner/
├── booking/                    # Place Booking.com/Airbnb HTML files here
│   ├── Hotel_Munich.html
│   ├── Hotel_Garmisch.html
│   └── Reiseplanung_Fahrrad.xlsx  # (Optional) Additional trip info
├── gpx/                        # Place your GPX route files here
│   ├── Day1_Munich_Tegernsee.gpx
│   ├── Day2_Tegernsee_Achensee.gpx
│   ├── Day3_Achensee_Garmisch.gpx
│   └── Paesse.json            # (Optional) Mountain pass database
```

**Example `Paesse.json`:**
```json
[
  {"passname": "Achenpass, Tirol, Österreich"},
  {"passname": "Kesselberg, Bayern, Deutschland"}
]
```

**Example `Reiseplanung_Fahrrad.xlsx` (Column B = Date, Column C = Info):**
```
A         B              C
Tag       Datum          Infos
1         2026-05-15     Markt besuchen; https://example.com/restaurant
2         2026-05-16     Früh losfahren
```

### 2. Configure `main.py`

Edit the paths in `main.py`:

```python
BOOKING_DIR = Path("../2026_Croatia/booking")
GPX_DIR = Path("../2026_Croatia/gpx")
OUT_DIR = Path("../2026_Croatia/gpx_modified")
```

### 3. Start BRouter

```bash
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

### 4. Run the Planner

```bash
python main.py
```

### 5. Results

The planner generates:

* `output/bookings.json` – Structured booking & tour metadata  
* `output/gpx_modified/` – Extended GPX files (one per day)  
* `output/Reiseplanung_*.pdf` – Professional PDF report with:  
  * Daily itinerary table  
  * Elevation profiles for routes and passes  
  * Clickable links to tourist sights  
  * Summary statistics  

---

## Usage Examples

### Basic Tour Planning

```python
from pathlib import Path
from biketour_planner.gpx_route_manager import GPXRouteManager

# Initialize route manager
manager = GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/gpx_modified/"),
    max_connection_distance_m=1000  # Max distance for auto-chaining
)

# Process all bookings
bookings = [
    {
        "arrival_date": "2026-05-15",
        "hotel_name": "Hotel Munich",
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

### Custom Pass Detection

```python
from biketour_planner.pass_finder import process_passes

bookings = process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,  # Search radius around hotels
    pass_radius_km=5.0    # Search radius around passes
)
```

### Generate PDF Report

```python
from biketour_planner.pdf_export import export_bookings_to_pdf

export_bookings_to_pdf(
    json_path=Path("output/bookings.json"),
    output_path=Path("output/Tour_Report.pdf"),
    output_dir=Path("output/gpx_modified/"),
    gpx_dir=Path("gpx/"),
    title="Croatia Bike Tour 2026",
    excel_info_path=Path("booking/Reiseplanung_Fahrrad.xlsx")
)
```

---

## Data Produced

For each accommodation/day, the planner records:

* **Accommodation Details:**  
  * Name, address, phone  
  * Arrival/departure dates  
  * Check-in time  
  * Amenities (kitchen, washing machine, breakfast)  
  * Cancellation deadline  
  * Total price  
  * GPS coordinates  

* **Route Information:**  
  * List of GPX files used  
  * Total distance (km)  
  * Total ascent and descent (m)  
  * Maximum elevation (m)  
  * Final merged GPX file name  

* **Mountain Passes:**  
  * Pass name and coordinates  
  * Distance to pass  
  * Elevation gain to summit  
  * Associated GPX track  

* **Tourist Attractions:**  
  * Names and coordinates  
  * Google Maps links  

---

## Advanced Features

### Intelligent Route Chaining

The planner uses a sophisticated algorithm to connect multiple GPX tracks:

1. **Target Side Determination**: Identifies which end of the destination track is closer to the start  
2. **Start Point Optimization**: Navigates to the relevant side of the destination, not just the nearest point  
3. **Automatic Direction Detection**: Determines whether to traverse tracks forward or backward  
4. **Multi-Day Continuity**: Seamlessly continues routes from previous days  

### Elevation Calculation Methods

Three elevation calculation methods are available:

1. **Simple with Threshold** (`calculate_elevation_gain_simple`):  
   - Fast, ignores GPS noise under threshold  

2. **Smoothed** (`calculate_elevation_gain_smoothed`):  
   - Moving average smoothing + threshold  
   - Recommended for most use cases  

3. **Segment-Based** (`calculate_elevation_gain_segment_based`):  
   - Most accurate, identifies continuous climbs/descents  
   - Used by default in the planner  

### Color-Coded Cancellation Deadlines

In PDF reports, cancellation dates are color-coded:

* 🟢 **Green**: < 7 days before arrival (flexible)  
* ⚫ **Black**: 7-30 days before arrival (moderate)  
* 🔴 **Red**: > 30 days before arrival (inflexible)  

### Configuration Parameters

#### Route Manager Parameters

```python
GPXRouteManager(
    gpx_dir=Path("gpx/"),
    output_path=Path("output/"),
    max_connection_distance_m=1000,  # Max auto-chain distance
    max_chain_length=20              # Max tracks per route
)
```

#### Pass Finder Parameters

```python
process_passes(
    passes_json_path=Path("gpx/Paesse.json"),
    gpx_dir=Path("gpx/"),
    bookings=bookings,
    hotel_radius_km=5.0,    # Search radius around hotels
    pass_radius_km=5.0      # Search radius around pass summit
)
```

#### Tourist Sights Parameters

```python
find_top_tourist_sights(
    lat=43.5081,
    lon=16.4402,
    radius=5000,  # Search radius in meters
    limit=2       # Max number of POIs
)
```
