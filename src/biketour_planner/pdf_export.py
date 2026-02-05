"""PDF export module for travel planning with clickable hyperlinks.

This module creates PDFs directly from booking data with clickable
Google Maps links for tourist sights and elevation profiles.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .constants import PDF_PAGE_WIDTH_CM
from .elevation_profiles import add_elevation_profiles_to_story, get_merged_gpx_files_from_bookings
from .excel_export import create_accommodation_text, extract_city_name
from .excel_info_reader import read_daily_info_from_excel
from .gpx_route_manager_static import get_statistics4track, read_gpx_file


def create_tourist_sights_links(tourist_sights: dict | None) -> list[str]:
    """Creates HTML links for tourist sights.

    Args:
        tourist_sights: Geoapify response dictionary or None.

    Returns:
        List of HTML formatted links for reportlab Paragraph.
    """
    if not tourist_sights or "features" not in tourist_sights:
        return []

    links = []
    features = tourist_sights.get("features", [])

    for poi in features:
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
        lat, lon = props.get("lat"), props.get("lon")
        if lat is None or lon is None:
            continue

        # Create Google Maps URL
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        # HTML link for reportlab
        html_link = f'<a href="{google_maps_url}" color="blue"><u>{display_name}</u></a>'
        links.append(html_link)

    return links


def get_cancellation_cell_style(
    free_cancel_until: str | None, arrival_date: str, base_cell_style: ParagraphStyle
) -> ParagraphStyle:
    """Creates a ParagraphStyle for cancellation cells based on the timeframe.

    Args:
        free_cancel_until: ISO date of cancellation deadline or None.
        arrival_date: ISO date of arrival.
        base_cell_style: Base ParagraphStyle to copy.

    Returns:
        ParagraphStyle with adjusted text color.
    """
    text_color = colors.black

    if free_cancel_until and arrival_date:
        try:
            cancel_date = datetime.fromisoformat(free_cancel_until)
            arrival = datetime.fromisoformat(arrival_date)
            days_diff = (arrival - cancel_date).days

            if days_diff < 7:
                text_color = colors.HexColor("#008000")  # Green
            elif days_diff > 30:
                text_color = colors.HexColor("#DC143C")  # Crimson Red
        except ValueError:
            pass

    return ParagraphStyle(f"CancellationStyle_{id(free_cancel_until)}", parent=base_cell_style, textColor=text_color)


def export_bookings_to_pdf(
    json_path: Path,
    output_path: Path,
    output_dir: Path = None,
    gpx_dir: Path = None,
    title: str = "Bike Tour Planning",
    excel_info_path: Path = None,
) -> None:
    """Exports booking info to a PDF file with clickable links and elevation profiles.

    Args:
        json_path: Path to JSON file with bookings.
        output_path: Path for the output PDF file.
        output_dir: Path to directory with merged GPX files.
        gpx_dir: Path to directory with original GPX files for passes.
        title: Document title.
        excel_info_path: Path to Excel file with additional daily info.
    """
    # Register Unicode fonts
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"))
        default_font, bold_font = "DejaVuSans", "DejaVuSans-Bold"
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont("ArialUnicode", "ARIALUNI.TTF"))
            default_font, bold_font = "ArialUnicode", "ArialUnicode"
        except Exception:
            print("⚠️ Warning: No Unicode font found. Special characters might not be displayed correctly.")
            default_font, bold_font = "Helvetica", "Helvetica-Bold"

    # Load JSON
    with open(json_path, encoding="utf-8") as f:
        bookings = json.load(f)

    bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

    daily_info = {}
    if excel_info_path and excel_info_path.exists():
        daily_info = read_daily_info_from_excel(excel_info_path)

    # Create PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1f4788"),
        alignment=TA_CENTER,
        fontName=bold_font,
        spaceAfter=12,
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

    story = [Paragraph(title, title_style), Spacer(1, 0.5 * cm)]
    table_data = [
        [
            Paragraph("<b>Tag</b>", cell_style),
            Paragraph("<b>Datum</b>", cell_style),
            Paragraph("<b>Von</b>", cell_style),
            Paragraph("<b>Nach</b>", cell_style),
            Paragraph("<b>km</b>", cell_style),
            Paragraph("<b>Unterkunft</b>", cell_style),
            Paragraph("<b>Hm/Max</b>", cell_style),
            Paragraph("<b>GPX</b>", cell_style),
            Paragraph("<b>Infos, Berge und Site Seeing</b>", cell_style),
            Paragraph("<b>Preis</b>", cell_style),
            Paragraph("<b>Storno</b>", cell_style),
        ]
    ]

    previous_city = previous_departure_date = None
    day_counter, total_km, total_ascent, total_price = 1, 0.0, 0, 0.0

    for booking in bookings_sorted:
        # Check for intermediate days
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
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                        table_data.append(row)
                        day_counter += 1
            except ValueError:
                pass

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

        km_values, hm_max_values, gpx_tracks = [], [], []

        # Main track stats
        if booking.get("gpx_track_final"):
            gpx_tracks.append(str(booking.get("gpx_track_final", ""))[:12])
            km_val = booking.get("total_distance_km")
            km_values.append(f"{km_val:.0f}" if km_val else "")
            hm = booking.get("total_ascent_m")
            max_elev = booking.get("max_elevation_m")
            hm_max_values.append(f"{hm} / {max_elev}" if hm or max_elev else "")
            if km_val:
                total_km += float(km_val)
            if hm:
                total_ascent += int(hm)

        # Pass tracks stats
        for pass_track in booking.get("paesse_tracks", []):
            pass_file = pass_track.get("file", "")[:12]
            gpx_tracks.append(f"{pass_file}<br/>({pass_track.get('passname', '')})")
            pass_gpx_path = gpx_dir / pass_track.get("file", "") if gpx_dir else None
            if pass_gpx_path and pass_gpx_path.exists():
                gpx = read_gpx_file(pass_gpx_path)
                if gpx and gpx.tracks:
                    p_max, p_dist, p_asc, _ = get_statistics4track(gpx)
                    pass_km = p_dist / 1000
                    km_values.append(f"{pass_km:.0f}")
                    total_km += pass_km
                    hm_max_values.append(f"{int(round(p_asc))} / {int(round(p_max)) if p_max != float('-inf') else ''}")
                    total_ascent += int(round(p_asc))
                else:
                    km_values.append("")
                    hm_max_values.append("")
            else:
                km_values.append("")
                hm_max_values.append("")

        if booking.get("total_price"):
            total_price += float(booking.get("total_price", 0))

        sights_links = create_tourist_sights_links(booking.get("tourist_sights"))
        for pass_track in booking.get("paesse_tracks", []):
            p_lat, p_lon = pass_track.get("latitude"), pass_track.get("longitude")
            if pass_track.get("passname") and p_lat is not None and p_lon is not None:
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
                sights_links.append(f'<a href="{google_maps_url}" color="blue"><u>{pass_track["passname"]}</u></a>')

        if arrival_date in daily_info:
            sights_links.extend(daily_info[arrival_date])

        cancellation_style = get_cancellation_cell_style(
            booking.get("free_cancel_until"), booking.get("arrival_date"), cell_style
        )

        row = [
            Paragraph(str(day_counter), cell_style),
            Paragraph(date_str, cell_style),
            Paragraph(previous_city or "", cell_style),
            Paragraph(current_city, cell_style),
            Paragraph("<br/>".join(km_values), cell_style),
            Paragraph(accommodation_text.replace("\n", "<br/>"), cell_style),
            Paragraph("<br/>".join(hm_max_values), cell_style),
            Paragraph("<br/>".join(gpx_tracks), cell_style),
            Paragraph("<br/>".join(sights_links), link_style),
            Paragraph(str(booking.get("total_price", "")), cell_style),
            Paragraph(
                f"bis: {booking.get('free_cancel_until', '')}" if booking.get("free_cancel_until") else "", cancellation_style
            ),
        ]
        table_data.append(row)
        previous_city, previous_departure_date, day_counter = current_city, booking.get("departure_date"), day_counter + 1

    # Checkout row for last accommodation
    if bookings_sorted and previous_departure_date:
        last_booking = bookings_sorted[-1]
        last_departure_date = last_booking.get("departure_date")
        last_city = extract_city_name(last_booking.get("address", ""))
        if last_departure_date:
            try:
                last_arrival = datetime.fromisoformat(last_booking.get("arrival_date", ""))
                last_checkout = datetime.fromisoformat(last_departure_date)
                days_staying = (last_checkout - last_arrival).days
                if days_staying > 1:
                    for d_off in range(1, days_staying):
                        intermediate_date = last_arrival + timedelta(days=d_off)
                        table_data.append(
                            [
                                Paragraph(str(day_counter), cell_style),
                                Paragraph(intermediate_date.strftime("%a, %d.%m.%Y"), cell_style),
                                Paragraph(last_city, cell_style),
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                            ]
                        )
                        day_counter += 1
                table_data.append(
                    [
                        Paragraph(str(day_counter), cell_style),
                        Paragraph(last_checkout.strftime("%a, %d.%m.%Y"), cell_style),
                        Paragraph(last_city, cell_style),
                        Paragraph("Checkout", cell_style),
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
            except ValueError:
                pass

    col_widths = [1.0 * cm, 2.1 * cm, 2.2 * cm, 2.2 * cm, 1.0 * cm, 5.3 * cm, 1.8 * cm, 2.2 * cm, 4.1 * cm, 1.2 * cm, 2.0 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                ("ALIGN", (9, 1), (9, -1), "RIGHT"),
                ("FONTNAME", (0, 1), (-1, -1), default_font),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor("#4472C4")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.8 * cm))
    summary_text = (
        f"<b>Gesamtkilometer:</b> {total_km:.2f} km       "
        f"<b>Gesamthöhenmeter:</b> {total_ascent} m       "
        f"<b>Gesamtkosten:</b> {total_price:.2f} €"
    )
    story.append(Paragraph(summary_text, summary_style))

    if output_dir:
        gpx_files = get_merged_gpx_files_from_bookings(bookings_sorted, output_dir)
        add_elevation_profiles_to_story(
            story, gpx_files, bookings_sorted, gpx_dir or output_dir, title_style, page_width_cm=PDF_PAGE_WIDTH_CM
        )

    doc.build(story)
    print(f"PDF-Datei erstellt: {output_path}")


if __name__ == "__main__":
    export_bookings_to_pdf(json_path=Path("output/bookings.json"), output_path=Path("output/tour_plan.pdf"))
