from openpyxl.styles import Font
from typing import Optional


def create_tourist_sights_hyperlinks(worksheet, row: int, tourist_sights: Optional[dict]) -> None:
    """Erstellt anklickbare Hyperlinks für Sehenswürdigkeiten über mehrere Excel-Spalten.

    Der erste Link wird in Spalte I eingefügt, weitere Links in L, M, N, ...
    Jede Sehenswürdigkeit erhält ihren eigenen anklickbaren Hyperlink, der direkt
    zu den GPS-Koordinaten in Google Maps führt.

    Args:
        worksheet: Das openpyxl Worksheet-Objekt.
        row: Zeilennummer (z.B. 5 für Zeile 5).
        tourist_sights: Geoapify-Response-Dictionary mit "features" Key oder None.
                       Jedes Feature sollte properties mit name, lat, lon enthalten.

    Example:
        >>> create_tourist_sights_hyperlinks(ws, 5, booking.get("tourist_sights"))
        # Zelle I5 enthält ersten Link, L5 zweiten Link, etc.
    """
    if not tourist_sights or "features" not in tourist_sights:
        worksheet[f"I{row}"] = ""
        return

    features = tourist_sights.get("features", [])
    if not features:
        worksheet[f"I{row}"] = ""
        return

    # Spalten: I (erste), dann L, M, N, O, P, ...
    columns = ["I"] + [chr(ord("L") + i) for i in range(26)]  # L-Z und darüber hinaus

    for idx, poi in enumerate(features):
        if idx >= len(columns):
            # Falls mehr Sehenswürdigkeiten als Spalten verfügbar
            break

        if "properties" not in poi:
            continue

        props = poi["properties"]

        # Bestimme Namen (mit Fallbacks)
        if "name" in props:
            display_name = props["name"]
        elif "street" in props:
            display_name = props["street"]
        else:
            display_name = f"({props.get('lat')}, {props.get('lon')})"

        # GPS-Koordinaten extrahieren
        lat = props.get("lat")
        lon = props.get("lon")

        if lat is None or lon is None:
            continue

        # Google Maps URL erstellen
        # Format: https://www.google.com/maps/search/?api=1&query=lat,lon
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        # Excel HYPERLINK-Formel: =HYPERLINK(url, "Anzeigetext")
        # Escape double quotes in display_name
        safe_name = display_name.replace('"', '""')
        hyperlink_formula = f'=HYPERLINK("{google_maps_url}","{safe_name}")'

        # Setze Hyperlink in entsprechende Spalte
        cell_ref = f"{columns[idx]}{row}"
        worksheet[cell_ref] = hyperlink_formula

        # Formatiere als Hyperlink (blau, unterstrichen)
        worksheet[cell_ref].font = Font(color="0563C1", underline="single")
