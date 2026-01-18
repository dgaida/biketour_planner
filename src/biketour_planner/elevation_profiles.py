"""Höhenprofil-Generierung für GPS-Tracks mit Steigungsvisualisierung.

Dieses Modul erstellt farbcodierte Höhenprofile aus GPX-Dateien:
- Rot für Anstiege (desto steiler, desto kräftiger)
- Grün für Abfahrten (desto steiler, desto kräftiger)
"""

import numpy as np
from pathlib import Path
from typing import List, Tuple

# import gpxpy
from io import BytesIO
from reportlab.platypus import Image, PageBreak, Paragraph
from reportlab.lib.styles import ParagraphStyle

# from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm

from .gpx_route_manager_static import haversine, read_gpx_file
import matplotlib

matplotlib.use("Agg")  # Backend für Nicht-GUI-Umgebungen
import matplotlib.pyplot as plt  # noqa: E402


def extract_elevation_profile(gpx_file: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Extrahiert Distanz und Höhenprofil aus einer GPX-Datei.

    Args:
        gpx_file: Pfad zur GPX-Datei.

    Returns:
        Tuple aus (distances, elevations):
            - distances: Kumulative Distanz in Kilometern als numpy array
            - elevations: Höhe in Metern als numpy array

    Raises:
        ValueError: Wenn GPX-Datei nicht gelesen werden kann oder keine Daten enthält.
    """
    gpx = read_gpx_file(gpx_file)

    if gpx is None or not gpx.tracks:
        raise ValueError(f"Konnte {gpx_file.name} nicht lesen oder keine Tracks gefunden")

    distances = [0.0]  # Start bei 0 km
    elevations = []

    prev_point = None
    cumulative_distance = 0.0

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.elevation is None:
                    continue

                elevations.append(point.elevation)

                if prev_point is not None:
                    dist = haversine(prev_point.latitude, prev_point.longitude, point.latitude, point.longitude)
                    cumulative_distance += dist / 1000.0  # in km
                    distances.append(cumulative_distance)

                prev_point = point

    if not elevations:
        raise ValueError(f"Keine Höhendaten in {gpx_file.name} gefunden")

    return np.array(distances), np.array(elevations)


def calculate_gradient(distances: np.ndarray, elevations: np.ndarray) -> np.ndarray:
    """Berechnet die Steigung in Prozent zwischen aufeinanderfolgenden Punkten.

    Args:
        distances: Distanzen in Kilometern.
        elevations: Höhen in Metern.

    Returns:
        Steigungen in Prozent als numpy array (gleiche Länge wie Input).
    """
    gradients = np.zeros_like(elevations)

    for i in range(1, len(distances)):
        dist_diff = (distances[i] - distances[i - 1]) * 1000  # in Meter
        elev_diff = elevations[i] - elevations[i - 1]

        if dist_diff > 0:
            gradients[i] = (elev_diff / dist_diff) * 100  # in Prozent
        else:
            gradients[i] = 0

    return gradients


def get_color_for_gradient(gradient: float) -> str:
    """Bestimmt die Farbe basierend auf der Steigung.

    Steigungen (positiv = bergauf):
    - 0-3%: Hellrot
    - 3-6%: Mittelrot
    - 6-10%: Rot
    - >10%: Dunkelrot

    Gefälle (negativ = bergab):
    - 0 bis -3%: Hellgrün
    - -3 bis -6%: Mittelgrün
    - -6 bis -10%: Grün
    - < -10%: Dunkelgrün

    Args:
        gradient: Steigung in Prozent.

    Returns:
        Hex-Farbcode als String.
    """
    if gradient > 0:  # Anstieg - Rottöne
        if gradient < 3:
            return "#ffcccc"  # Hellrot
        elif gradient < 6:
            return "#ff6666"  # Mittelrot
        elif gradient < 10:
            return "#ff0000"  # Rot
        else:
            return "#cc0000"  # Dunkelrot
    else:  # Abstieg - Grüntöne
        gradient = abs(gradient)
        if gradient < 3:
            return "#ccffcc"  # Hellgrün
        elif gradient < 6:
            return "#66ff66"  # Mittelgrün
        elif gradient < 10:
            return "#00ff00"  # Grün
        else:
            return "#00cc00"  # Dunkelgrün


def create_elevation_profile_plot(
    gpx_file: Path, booking: dict, pass_track: dict = None, title: str = None, figsize: Tuple[int, int] = (12, 4)
) -> BytesIO:
    """Erstellt ein farbcodiertes Höhenprofil aus einer GPX-Datei.

    Args:
        gpx_file: Pfad zur GPX-Datei.
        booking: Buchungs-Dictionary (für Haupt-Track Statistiken).
        pass_track: Optional. Pass-Track Dictionary mit Statistiken (falls Pass-Track).
        title: Titel des Plots (Default: Dateiname).
        figsize: Größe der Figur in Zoll (Breite, Höhe).

    Returns:
        BytesIO-Objekt mit PNG-Bilddaten.

    Example:
        >>> # Haupt-Track
        >>> img_buffer = create_elevation_profile_plot(Path("route.gpx"), booking)
        >>>
        >>> # Pass-Track
        >>> pass_track = {"total_ascent_m": 1234, "total_descent_m": 567, ...}
        >>> img_buffer = create_elevation_profile_plot(Path("pass.gpx"), booking, pass_track)
    """
    # Daten extrahieren
    distances, elevations = extract_elevation_profile(gpx_file)
    gradients = calculate_gradient(distances, elevations)

    # Plot erstellen
    fig, ax = plt.subplots(figsize=figsize, dpi=100)

    # Zeichne farbcodierte Segmente
    for i in range(1, len(distances)):
        color = get_color_for_gradient(gradients[i])
        ax.fill_between(distances[i - 1 : i + 1], 0, elevations[i - 1 : i + 1], color=color, alpha=0.7, linewidth=0)

    # Schwarze Konturlinie oben
    ax.plot(distances, elevations, color="black", linewidth=1.5, zorder=10)

    # Beschriftungen
    if title is None:
        title = gpx_file.stem
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Distanz (km)", fontsize=11)
    ax.set_ylabel("Höhe (m)", fontsize=11)

    # Grid
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    # Achsenlimits
    ax.set_xlim(0, distances[-1])
    ax.set_ylim(min(elevations) * 0.8, max(elevations) * 1.1)

    # Statistiken als Text - verwende pass_track falls vorhanden, sonst booking
    if pass_track:
        total_ascent = pass_track.get("total_ascent_m", "")
        total_descent = pass_track.get("total_descent_m", "")
    else:
        total_ascent = booking.get("total_ascent_m", "")
        total_descent = booking.get("total_descent_m", "")

    stats_text = (
        f"Distanz: {distances[-1]:.1f} km  |  "
        f"Max: {max(elevations):.0f} m  |  "
        f"↑ {total_ascent:.0f} m  |  "
        f"↓ {total_descent:.0f} m"
    )
    ax.text(
        0.5,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="center",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    # In BytesIO speichern
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
    img_buffer.seek(0)
    plt.close(fig)

    return img_buffer


def add_elevation_profiles_to_story(
    story: List,
    gpx_files: List[Path],
    bookings: List[dict],
    gpx_dir: Path,
    title_style: ParagraphStyle,
    page_width_cm: float = 25.0,
) -> None:
    """Fügt Höhenprofile für alle GPX-Dateien zur PDF-Story hinzu.

    Erstellt Höhenprofile für:
    1. Haupt-Tracks (merged GPX zu Hotels)
    2. Pass-Tracks (direkt nach dem zugehörigen Haupt-Track)

    Args:
        story: reportlab Story-Liste (wird in-place modifiziert).
        gpx_files: Liste von Pfaden zu gemergten GPX-Dateien.
        bookings: Liste mit Buchungs-Dictionaries (für Pass-Zuordnung).
        gpx_dir: Verzeichnis mit Original-GPX-Dateien (für Pass-Tracks).
        title_style: ParagraphStyle für Überschriften.
        page_width_cm: Verfügbare Seitenbreite in cm für Skalierung.

    Example:
        >>> story = []
        >>> gpx_files = [Path("day1.gpx"), Path("day2.gpx")]
        >>> add_elevation_profiles_to_story(story, gpx_files, bookings, gpx_dir, title_style)
    """
    if not gpx_files and not any(b.get("paesse_tracks") for b in bookings):
        return

    # Neue Seite für Höhenprofile
    story.append(PageBreak())

    # Überschrift
    heading = Paragraph("<b>Höhenprofile</b>", title_style)
    story.append(heading)

    # Erstelle Mapping: GPX-Dateiname -> Booking (für Pass-Zuordnung)
    gpx_to_booking = {}
    for booking in bookings:
        gpx_track = booking.get("gpx_track_final")
        if gpx_track:
            gpx_to_booking[gpx_track] = booking

    # Für jede GPX-Datei ein Profil erstellen
    for gpx_file in gpx_files:
        try:
            booking = gpx_to_booking.get(gpx_file.name)

            # Haupt-Track Profil erstellen (ohne pass_track Parameter)
            img_buffer = create_elevation_profile_plot(gpx_file, booking, title=gpx_file.stem)

            # Als reportlab Image hinzufügen
            img = Image(img_buffer, width=page_width_cm * cm, height=(page_width_cm / 3) * cm)
            story.append(img)

            # Prüfe ob es Pass-Tracks für diesen Tag gibt
            if booking and booking.get("paesse_tracks"):
                for pass_track in booking["paesse_tracks"]:
                    pass_file = gpx_dir / pass_track["file"]
                    passname = pass_track.get("passname", "Pass")

                    if pass_file.exists():
                        try:
                            # Pass-Track Profil erstellen (MIT pass_track Parameter)
                            pass_img_buffer = create_elevation_profile_plot(
                                pass_file,
                                booking,
                                pass_track=pass_track,  # Übergebe Pass-Statistiken
                                title=f"{passname} ({pass_file.stem})",
                            )

                            # Als reportlab Image hinzufügen
                            pass_img = Image(pass_img_buffer, width=page_width_cm * cm, height=(page_width_cm / 3) * cm)
                            story.append(pass_img)

                        except Exception as e:
                            error_text = f"<i>Fehler beim Erstellen des Pass-Profils für {passname}: {e}</i>"
                            story.append(Paragraph(error_text, title_style))

        except Exception as e:
            # Fehler-Nachricht bei Problemen
            error_text = f"<i>Fehler beim Erstellen des Profils für {gpx_file.name}: {e}</i>"
            story.append(Paragraph(error_text, title_style))

    total_profiles = len(gpx_files) + sum(len(b.get("paesse_tracks", [])) for b in bookings)
    print(f"✅ {total_profiles} Höhenprofile erstellt")


def get_merged_gpx_files_from_bookings(bookings: List[dict], output_dir: Path) -> List[Path]:
    """Extrahiert die Pfade zu den gemergten GPX-Dateien aus den Buchungen.

    Args:
        bookings: Liste mit Buchungs-Dictionaries.
        output_dir: Verzeichnis mit den gemergten GPX-Dateien.

    Returns:
        Liste von Pfaden zu GPX-Dateien.
    """
    gpx_files = []

    for booking in bookings:
        gpx_track = booking.get("gpx_track_final")
        if gpx_track:
            gpx_path = output_dir / gpx_track
            if gpx_path.exists():
                gpx_files.append(gpx_path)

    return gpx_files
