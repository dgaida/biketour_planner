# Architecture Overview

## System Components

The system consists of several modules working together to create a complete travel plan from booking confirmations and GPX tracks.

```mermaid
graph TD
    A[HTML Bookings] --> B[parse_booking]
    C[GPX Tracks] --> D[GPXRouteManager]
    B --> E[Booking Data]
    E --> F[geocode]
    F --> E
    E --> G[geoapify]
    G --> E
    D --> H[Route Data]
    E --> I[pass_finder]
    H --> I
    I --> J[Enhanced Booking Data]
    J --> K[pdf_export]
    J --> L[excel_export]
    J --> M[ics_export]
```

## Data Flow Diagram

Data flow follows a sequential process from extraction to export.

```mermaid
sequenceDiagram
    participant U as User
    participant P as Parser
    participant G as Geocoder
    participant RM as Route Manager
    participant B as BRouter
    participant E as Exporter

    U->>P: Provide HTML files
    P->>P: Extract data
    P->>G: Send addresses
    G-->>P: Receive coordinates
    P->>RM: Bookings + GPX folder
    RM->>RM: Analyze tracks
    RM->>B: Routing request (fill gaps)
    B-->>RM: GPX segments
    RM->>RM: Merge GPX
    RM-->>E: Enriched data
    E->>U: PDF/Excel/ICS reports
```

## Process Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initialization: Load Configuration
    Initialization --> Parsing: Read HTML Bookings
    Parsing --> Geocoding: Addresses to Coordinates
    Geocoding --> POISearch: Search Tourist Attractions
    POISearch --> RoutePlanning: Chain GPX Tracks
    RoutePlanning --> BRouter: Routing to Hotels
    BRouter --> PassSearch: Identify Mountain Passes
    PassSearch --> Export: Generate Reports
    Export --> [*]
```

## Key Abstractions

- **Booking**: Pydantic model representing an accommodation with dates, location, and amenities.
- **RoutePosition**: Dataclass representing a point in a GPX track (file and index).
- **RouteStatistics**: Dataclass for accumulating distance and elevation data.
- **RouteContext**: Dataclass for managing state during route discovery.
- **Pass**: Mountain pass with associated track data.
