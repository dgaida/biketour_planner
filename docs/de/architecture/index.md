# Architektur-Übersicht

## Systemkomponenten

Das System besteht aus mehreren Modulen, die zusammenarbeiten, um aus Buchungsbestätigungen und GPX-Tracks einen vollständigen Reiseplan zu erstellen.

```mermaid
graph TD
    A[HTML-Buchungen] --> B[parse_booking]
    C[GPX-Tracks] --> D[GPXRouteManager]
    B --> E[Buchungsdaten]
    E --> F[geocode]
    F --> E
    E --> G[geoapify]
    G --> E
    D --> H[Routendaten]
    E --> I[pass_finder]
    H --> I
    I --> J[Erweiterte Buchungsdaten]
    J --> K[pdf_export]
    J --> L[excel_export]
    J --> M[ics_export]
```

## Datenfluss-Diagramm

Der Datenfluss folgt einem sequentiellen Prozess von der Extraktion bis zum Export.

```mermaid
sequenceDiagram
    participant U as User
    participant P as Parser
    participant G as Geocoder
    participant RM as Route Manager
    participant B as BRouter
    participant E as Exporter

    U->>P: HTML-Dateien bereitstellen
    P->>P: Daten extrahieren
    P->>G: Adressen senden
    G-->>P: Koordinaten empfangen
    P->>RM: Buchungen + GPX-Ordner
    RM->>RM: Tracks analysieren
    RM->>B: Routing-Anfrage (Lücken füllen)
    B-->>RM: GPX-Segmente
    RM->>RM: GPX zusammenführen
    RM-->>E: Angereicherte Daten
    E->>U: PDF/Excel/ICS Berichte
```

## Prozess-Lebenszyklus

```mermaid
stateDiagram-v2
    [*] --> Initialisierung: Lade Konfiguration
    Initialisierung --> Parsing: Lese HTML-Buchungen
    Parsing --> Geokodierung: Adressen zu Koordinaten
    Geokodierung --> POISuche: Suche Sehenswürdigkeiten
    POISuche --> Routenplanung: Verbinde GPX-Tracks
    Routenplanung --> BRouter: Routing zu Hotels
    BRouter --> PassSuche: Identifiziere Gebirgspässe
    PassSuche --> Export: Generiere Berichte
    Export --> [*]
```

## Kernabstraktionen

- **Booking**: Pydantic-Modell, das eine Unterkunft mit Daten, Ort und Ausstattung darstellt.
- **RoutePosition**: Dataklasse, die einen Punkt in einem GPX-Track darstellt (Datei und Index).
- **RouteStatistics**: Dataklasse zur Akkumulation von Distanz- und Höhendaten.
- **RouteContext**: Dataklasse zur Verwaltung des Zustands während der Routensuche.
- **Pass**: Gebirgspass mit zugehörigen Track-Daten.
