"""PDF-Export-Modul für Reiseplanung mit klickbaren Hyperlinks.

Dieses Modul erstellt PDFs direkt aus den Buchungsdaten mit klickbaren
Google Maps Links für Sehenswürdigkeiten.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # , PageBreak

# from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER  # TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .excel_export import extract_city_name, create_accommodation_text
from .elevation_profiles import add_elevation_profiles_to_story, get_merged_gpx_files_from_bookings
from .gpx_route_manager_static import get_statistics4track, read_gpx_file


def create_tourist_sights_links(tourist_sights: Optional[Dict]) -> List[str]:
    """Erstellt HTML-Links für Sehenswürdigkeiten.

    Args:
        tourist_sights: Geoapify-Response-Dictionary mit "features" Key oder None.

    Returns:
        Liste von HTML-formatierten Links für reportlab Paragraph.
    """
    if not tourist_sights or "features" not in tourist_sights:
        return []

    links = []
    features = tourist_sights.get("features", [])

    for poi in features:
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
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        # HTML-Link für reportlab
        html_link = f'<a href="{google_maps_url}" color="blue"><u>{display_name}</u></a>'
        links.append(html_link)

    return links


def export_bookings_to_pdf(
    json_path: Path,
    output_path: Path,
    output_dir: Path = None,  # Pfad zu gemergten GPX-Dateien
    gpx_dir: Path = None,  # NEU: Pfad zu Original-GPX-Dateien (für Pass-Tracks)
    title: str = "Reiseplanung Kroatien 2026",
) -> None:
    """Exportiert Buchungsinformationen in eine PDF-Datei mit klickbaren Links.

    Erstellt ein PDF im Querformat mit einer Tabelle ähnlich dem Excel-Template.
    Sehenswürdigkeiten werden als klickbare Google Maps Links eingefügt.
    Am Ende werden Höhenprofile für alle Tage und Pässe hinzugefügt.

    Args:
        json_path: Pfad zur JSON-Datei mit Buchungen.
        output_path: Pfad für die Ausgabe-PDF-Datei.
        output_dir: Pfad zum Verzeichnis mit gemergten GPX-Dateien (Default: None).
        gpx_dir: Pfad zum Verzeichnis mit Original-GPX-Dateien für Pässe (Default: None).
        title: Titel des Dokuments (wird auf jeder Seite angezeigt).
    """
    # Registriere Unicode-Schriftarten (für kroatische Zeichen wie č, ć, ž, š, đ)
    try:
        # Versuche DejaVu Sans (häufig verfügbar auf Linux/Mac)
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"))
        default_font = "DejaVuSans"
        bold_font = "DejaVuSans-Bold"
    except Exception:
        try:
            # Fallback: Arial Unicode (Windows)
            pdfmetrics.registerFont(TTFont("ArialUnicode", "ARIALUNI.TTF"))
            default_font = "ArialUnicode"
            bold_font = "ArialUnicode"
        except Exception:
            # Letzter Fallback: Standard Helvetica (kann einige Zeichen nicht darstellen)
            print(
                "⚠️  Warnung: Keine Unicode-Schriftart gefunden. Sonderzeichen werden möglicherweise nicht korrekt dargestellt."
            )
            default_font = "Helvetica"
            bold_font = "Helvetica-Bold"

    # JSON laden
    with open(json_path, "r", encoding="utf-8") as f:
        bookings = json.load(f)

    # Nach Anreisedatum sortieren
    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    # PDF erstellen
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1f4788"),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName=bold_font,
    )

    cell_style = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=9, leading=11, fontName=default_font)

    link_style = ParagraphStyle(
        "LinkStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.blue, fontName=default_font
    )

    summary_style = ParagraphStyle(
        "SummaryStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        fontName=bold_font,
        textColor=colors.HexColor("#1f4788"),
        spaceAfter=6,
    )

    # Story (Inhalt) aufbauen
    story = []

    # Titel
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Tabellendaten vorbereiten
    table_data = []

    # Header
    header = [
        Paragraph("<b>Tag</b>", cell_style),
        Paragraph("<b>Datum</b>", cell_style),
        Paragraph("<b>Von</b>", cell_style),
        Paragraph("<b>Nach</b>", cell_style),
        Paragraph("<b>km</b>", cell_style),
        Paragraph("<b>Unterkunft</b>", cell_style),
        Paragraph("<b>Hm/Max</b>", cell_style),
        Paragraph("<b>GPX</b>", cell_style),
        Paragraph("<b>Sehenswürdigkeiten</b>", cell_style),
        Paragraph("<b>Preis</b>", cell_style),
        Paragraph("<b>Storno</b>", cell_style),
    ]
    table_data.append(header)

    # Daten + Summen
    previous_city = None
    previous_departure_date = None
    day_counter = 1

    total_km = 0.0
    total_ascent = 0
    total_price = 0.0

    for booking in bookings_sorted:
        # Prüfe ob Leerzeilen für Zwischentage eingefügt werden müssen
        if previous_departure_date and booking.get("arrival_date"):
            try:
                prev_departure = datetime.fromisoformat(previous_departure_date)
                current_arrival = datetime.fromisoformat(booking["arrival_date"])
                days_between = (current_arrival - prev_departure).days

                if days_between > 0:
                    for day_offset in range(days_between):
                        intermediate_date = prev_departure + timedelta(days=day_offset)
                        row = [
                            Paragraph(str(day_counter), cell_style),
                            Paragraph(intermediate_date.strftime("%a, %d.%m.%Y"), cell_style),
                            Paragraph(previous_city or "", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                            Paragraph("", cell_style),
                        ]
                        table_data.append(row)
                        day_counter += 1

            except ValueError:
                pass

        # Normale Buchungszeile
        arrival_date = booking.get("arrival_date", "")
        if arrival_date:
            try:
                date_obj = datetime.fromisoformat(arrival_date)
                date_str = date_obj.strftime("%a, %d.%m.%Y")
            except ValueError:
                date_str = arrival_date
        else:
            date_str = ""

        current_city = extract_city_name(booking.get("address", ""))

        accommodation_text = create_accommodation_text(booking)

        # Berechne Statistiken für alle Tracks (Haupt-Track + Pass-Tracks)
        km_values = []
        hm_max_values = []
        gpx_tracks = []

        # Haupt-Track
        if booking.get("gpx_track_final"):
            gpx_tracks.append(str(booking.get("gpx_track_final", ""))[:12])

            # km-Wert für Haupt-Track
            km_val = booking.get("total_distance_km", "")
            km_values.append(str(km_val) if km_val else "")

            # Hm/Max für Haupt-Track
            hm = booking.get("total_ascent_m", "")
            max_elev = booking.get("max_elevation_m", "")
            hm_max_values.append(f"{hm} / {max_elev}" if hm or max_elev else "")

            # Summierung Haupt-Track
            if km_val:
                total_km += float(km_val)
            if hm:
                total_ascent += int(hm)

        # Pass-Tracks
        for pass_track in booking.get("paesse_tracks", []):
            pass_file = pass_track.get("file", "")[:15]
            passname = pass_track.get("passname", "")
            gpx_tracks.append(f"{pass_file}<br/>({passname})")

            # Lade Statistiken für Pass-Track aus GPX-Datei
            pass_gpx_path = gpx_dir / pass_track.get("file", "") if gpx_dir else None
            if pass_gpx_path and pass_gpx_path.exists():
                gpx = read_gpx_file(pass_gpx_path)
                if gpx and gpx.tracks:
                    pass_max_elevation, pass_distance, pass_ascent = get_statistics4track(gpx)

                    # Füge km-Wert hinzu
                    pass_km = pass_distance / 1000
                    km_values.append(f"{pass_km:.2f}")
                    total_km += pass_km

                    # Füge Hm/Max hinzu
                    pass_hm = int(round(pass_ascent))
                    pass_max = int(round(pass_max_elevation)) if pass_max_elevation != float("-inf") else ""
                    hm_max_values.append(f"{pass_hm} / {pass_max}" if pass_max else f"{pass_hm} / ")
                    total_ascent += pass_hm
                else:
                    km_values.append("")
                    hm_max_values.append("")
            else:
                km_values.append("")
                hm_max_values.append("")

        # Erstelle mehrzeilige Strings
        gpx_text = "<br/>".join(gpx_tracks) if gpx_tracks else ""
        km_text = "<br/>".join(km_values) if km_values else ""
        hm_max_text = "<br/>".join(hm_max_values) if hm_max_values else ""

        # Summierung Preis
        if booking.get("total_price"):
            total_price += float(booking.get("total_price", 0))

        # Sehenswürdigkeiten mit Links + Pass-Namen
        sights_links = create_tourist_sights_links(booking.get("tourist_sights"))

        # Füge Pass-Namen als Links hinzu
        for pass_track in booking.get("paesse_tracks", []):
            passname = pass_track.get("passname", "")
            pass_lat = pass_track.get("latitude")
            pass_lon = pass_track.get("longitude")

            if passname and pass_lat is not None and pass_lon is not None:
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={pass_lat},{pass_lon}"
                html_link = f'<a href="{google_maps_url}" color="blue"><u>{passname}</u></a>'
                sights_links.append(html_link)

        sights_html = "<br/>".join(sights_links) if sights_links else ""

        row = [
            Paragraph(str(day_counter), cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(previous_city or "", cell_style),
            Paragraph(current_city, cell_style),
            Paragraph(km_text, cell_style),
            Paragraph(accommodation_text.replace("\n", "<br/>"), cell_style),
            Paragraph(hm_max_text, cell_style),
            Paragraph(gpx_text, cell_style),
            Paragraph(sights_html, link_style),
            Paragraph(str(booking.get("total_price", "")), cell_style),
            Paragraph(f"bis: {booking.get('free_cancel_until', '')}" if booking.get("free_cancel_until") else "", cell_style),
        ]
        table_data.append(row)

        previous_city = current_city
        previous_departure_date = booking.get("departure_date")
        day_counter += 1

    # Tabelle erstellen
    col_widths = [
        1.2 * cm,  # Tag
        2.5 * cm,  # Datum
        2.2 * cm,  # Von
        2.2 * cm,  # Nach
        1.2 * cm,  # km
        4.5 * cm,  # Unterkunft
        1.8 * cm,  # Hm/Max
        2.0 * cm,  # GPX
        4.0 * cm,  # Sehenswürdigkeiten
        1.5 * cm,  # Preis
        2.0 * cm,  # Storno
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                # Body
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Tag zentriert
                ("ALIGN", (4, 1), (4, -1), "RIGHT"),  # km rechts
                ("ALIGN", (9, 1), (9, -1), "RIGHT"),  # Preis rechts
                ("FONTNAME", (0, 1), (-1, -1), default_font),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                # Gitternetz
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#4472C4")),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )

    story.append(table)

    # Zusammenfassung unter der Tabelle
    story.append(Spacer(1, 0.8 * cm))

    summary_text = (
        f"<b>Gesamtkilometer:</b> {total_km:.2f} km       "
        f"<b>Gesamthöhenmeter:</b> {total_ascent} m       "
        f"<b>Gesamtkosten:</b> {total_price:.2f} €"
    )
    story.append(Paragraph(summary_text, summary_style))

    # Höhenprofile hinzufügen
    if output_dir:
        gpx_files = get_merged_gpx_files_from_bookings(bookings_sorted, output_dir)
        add_elevation_profiles_to_story(
            story, gpx_files, bookings_sorted, gpx_dir or output_dir, title_style, page_width_cm=25.0  # NEU!  # NEU!
        )

    # PDF generieren
    doc.build(story)
    print(f"PDF-Datei erstellt: {output_path}")


if __name__ == "__main__":
    # Beispielaufruf
    export_bookings_to_pdf(
        json_path=Path("output/bookings.json"),
        output_path=Path("output/Reiseplanung_Kroatien_2026.pdf"),
        title="Reiseplanung Kroatien 2026",
    )
