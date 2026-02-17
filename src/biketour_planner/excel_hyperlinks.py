"""Excel hyperlink utilities for the Bike Tour Planner."""

from openpyxl.styles import Font


def create_tourist_sights_hyperlinks(worksheet, row: int, tourist_sights: dict | None) -> None:
    """Creates clickable hyperlinks for tourist sights across multiple Excel columns.

    The first link is inserted into column I, additional links into L, M, N, ...
    Each sight gets its own clickable hyperlink leading directly to GPS coordinates in Google Maps.

    Args:
        worksheet: The openpyxl Worksheet object.
        row: Row number (e.g., 5).
        tourist_sights: Geoapify response dictionary with "features" key or None.
                       Each feature should have properties with name, lat, and lon.

    Example:
        >>> create_tourist_sights_hyperlinks(ws, 5, booking.get("tourist_sights"))
        # Cell I5 contains the first link, L5 the second link, etc.
    """
    if not tourist_sights or "features" not in tourist_sights:
        worksheet[f"I{row}"] = ""
        return

    features = tourist_sights.get("features", [])
    if not features:
        worksheet[f"I{row}"] = ""
        return

    # Columns: I (first), then L, M, N, O, P, ...
    columns = ["I"] + [chr(ord("L") + i) for i in range(26)]  # L-Z and beyond

    for idx, poi in enumerate(features):
        if idx >= len(columns):
            # If more sights than available columns
            break

        if "properties" not in poi:
            continue

        props = poi["properties"]

        # Determine name (with fallbacks)
        if "name" in props:
            display_name = props["name"]
        elif "street" in props:
            display_name = props["street"]
        else:
            display_name = f"({props.get('lat')}, {props.get('lon')})"

        # Extract GPS coordinates
        lat = props.get("lat")
        lon = props.get("lon")

        if lat is None or lon is None:
            continue

        # Create Google Maps URL
        # Format: https://www.google.com/maps/search/?api=1&query=lat,lon
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        # Excel HYPERLINK formula: =HYPERLINK(url, "Display Name")
        # Escape double quotes in display_name
        safe_name = display_name.replace('"', '""')
        hyperlink_formula = f'=HYPERLINK("{google_maps_url}","{safe_name}")'

        # Set hyperlink in corresponding column
        cell_ref = f"{columns[idx]}{row}"
        worksheet[cell_ref] = hyperlink_formula

        # Format as hyperlink (blue, underlined)
        worksheet[cell_ref].font = Font(color="0563C1", underline="single")
