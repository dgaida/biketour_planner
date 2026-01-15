import gpxpy
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from .gpx_utils import haversine, read_gpx_file, find_closest_point_in_track, get_base_filename
from .brouter import route_to_address

GPXIndex = Dict[str, Dict]
PointDict = Dict[str, float]
StartPosResult = Tuple[Optional[str], Optional[int], Optional[str]]
TargetPosResult = Tuple[Optional[str], Optional[int], Optional[float], Optional[float]]
TrackStats = Tuple[float, float, float]


class GPXRouteManager:
    """Verwaltet GPX-Routen und ermöglicht die Verkettung von Tracks zwischen Standorten.

    Diese Klasse implementiert einen intelligenten Algorithmus zur Routenplanung für
    mehrtägige Fahrradtouren. Der Kernalgorithmus arbeitet wie folgt:

    1. **Ziel-Seiten-Bestimmung**: Findet heraus, welche Seite (Anfang oder Ende) des
       Ziel-Tracks näher am Startpunkt liegt. Dies ist entscheidend, um die richtige
       Fahrtrichtung durch Zwischen-Tracks zu bestimmen.

    2. **Start-Punkt-Optimierung**: Im Start-Track wird nicht zum nächstgelegenen Punkt
       zum Ziel gefahren, sondern zum Punkt, der der relevanten Ziel-Seite am nächsten
       ist. Dies verhindert ineffiziente Routen.

    3. **Track-Verkettung**: Verbindet mehrere GPX-Tracks unter Berücksichtigung von:
       - Räumlicher Nähe (max_connection_distance_m)
       - Vermeidung von Duplikaten (gleiche Basis-Dateinamen)
       - Fortsetzung vorheriger Routen (für mehrtägige Touren)

    4. **Richtungserkennung**: Bestimmt automatisch, ob ein Track vorwärts oder
       rückwärts durchfahren werden muss.

    Attributes:
        gpx_dir: Verzeichnis mit GPX-Dateien.
        gpx_index: Vorverarbeitete Metadaten aller GPX-Dateien mit Start-/Endpunkten,
                   Distanzen, Höhenprofilen und allen Trackpunkten.
        max_connection_distance_m: Maximale Distanz in Metern für die automatische
                                   Verkettung von Tracks. Tracks die weiter auseinander
                                   liegen werden nicht verbunden.
        max_chain_length: Maximale Anzahl zu verkettender Tracks. Verhindert
                         Endlosschleifen bei Routing-Problemen.

    Example:
        >>> manager = GPXRouteManager(Path("gpx/"), max_connection_distance_m=1000)
        >>> booking = {"arrival_date": "2026-05-15", "hotel_name": "Hotel Alpenblick"}
        >>> manager.collect_route_between_locations(
        ...     start_lat=47.5, start_lon=11.1,
        ...     target_lat=47.6, target_lon=11.3,
        ...     booking=booking
        ... )
        >>> print(f"Route: {booking['total_distance_km']} km")
    """

    def __init__(
        self,
        gpx_dir: Path,
        max_connection_distance_m: float = 1000.0,
        max_chain_length: int = 20,
    ):
        """Initialisiert den GPXRouteManager und lädt alle GPX-Dateien.

        Args:
            gpx_dir: Verzeichnis mit GPX-Dateien.
            max_connection_distance_m: Maximale Distanz für Track-Verkettung in Metern.
                                       Tracks die weiter entfernt sind werden nicht
                                       automatisch verbunden. Default: 1000m.
            max_chain_length: Maximale Anzahl zu verkettender Tracks. Verhindert
                             Endlosschleifen. Default: 20.
        """
        self.gpx_dir = gpx_dir
        self.max_connection_distance_m = max_connection_distance_m
        self.max_chain_length = max_chain_length
        self.gpx_index = self._preprocess_gpx_directory()

    def _preprocess_gpx_directory(self) -> GPXIndex:
        """Liest alle GPX-Dateien genau einmal ein und speichert relevante Metadaten.

        Diese Vorverarbeitung vermeidet wiederholtes Parsen derselben GPX-Dateien
        während der Routensuche und beschleunigt die Verarbeitung erheblich.

        Returns:
            Dictionary mit Dateinamen als Key und Metadaten-Dictionary als Value:
                - file (Path): Pfad zur GPX-Datei.
                - start_lat, start_lon (float): Koordinaten des ersten Punkts.
                - end_lat, end_lon (float): Koordinaten des letzten Punkts.
                - total_distance_m (float): Gesamtdistanz des Tracks in Metern.
                - total_ascent_m (float): Gesamter positiver Höhenunterschied in Metern.
                - max_elevation_m (int): Höchster Punkt des Tracks in Metern.
                - points (List[Dict]): Alle Trackpunkte mit lat, lon, elevation, index.

        Note:
            Dateien die nicht geparst werden können werden stillschweigend übersprungen.
        """
        gpx_index: GPXIndex = {}

        for gpx_file in Path(self.gpx_dir).glob("*.gpx"):
            gpx = read_gpx_file(gpx_file)
            if gpx is None or not gpx.tracks:
                continue

            total_distance = 0.0
            total_ascent = 0.0
            max_elevation = float("-inf")

            first_point = None
            last_point = None
            all_points = []

            point_index = 0
            for track in gpx.tracks:
                for seg in track.segments:
                    prev = None
                    for p in seg.points:
                        if first_point is None:
                            first_point = p
                        last_point = p

                        # Speichere alle Punkte mit Index
                        all_points.append(
                            {"lat": p.latitude, "lon": p.longitude, "elevation": p.elevation, "index": point_index}
                        )
                        point_index += 1

                        if p.elevation is not None:
                            max_elevation = max(max_elevation, p.elevation)

                        if prev:
                            d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
                            total_distance += d

                            if prev.elevation is not None and p.elevation is not None and p.elevation > prev.elevation:
                                total_ascent += p.elevation - prev.elevation
                        prev = p

            if first_point is None or last_point is None:
                continue

            gpx_index[gpx_file.name] = {
                "file": gpx_file,
                "start_lat": first_point.latitude,
                "start_lon": first_point.longitude,
                "end_lat": last_point.latitude,
                "end_lon": last_point.longitude,
                "total_distance_m": total_distance,
                "total_ascent_m": total_ascent,
                "max_elevation_m": (int(round(max_elevation)) if max_elevation != float("-inf") else None),
                "points": all_points,
            }

        return gpx_index

    def _find_start_pos(
        self,
        start_lat: float,
        start_lon: float,
        previous_last_file: Optional[Dict],
    ) -> StartPosResult:
        """Bestimmt die Startposition für die Routensuche.

        Wenn eine vorherige Route existiert (mehrtägige Tour), wird diese fortgesetzt.
        Dabei wird die Fahrtrichtung des Vortags erzwungen, um konsistente Routen
        zu gewährleisten. Ohne Vorgänger wird der nächstgelegene Punkt in allen
        GPX-Dateien gesucht.

        Args:
            start_lat: Breitengrad des Startpunkts in Dezimalgrad.
            start_lon: Längengrad des Startpunkts in Dezimalgrad.
            previous_last_file: Optional. Dictionary der letzten verwendeten GPX-Datei
                               vom Vortag mit Keys:
                               - 'file' (str): Dateiname
                               - 'end_index' (int): Letzter verwendeter Index
                               - 'reversed' (bool): Ob Track rückwärts durchfahren wurde

        Returns:
            Tuple aus:
                - start_file (str): Dateiname der Start-GPX-Datei.
                - start_index (int): Startindex im Track.
                - force_direction (str|None): Erzwungene Richtung ('forward'/'backward')
                  falls Fortsetzung vom Vortag, sonst None.

        Note:
            Die erzwungene Richtung stellt sicher, dass mehrtägige Touren konsistent
            in eine Richtung fortgesetzt werden und nicht hin- und hergefahren wird.
        """
        start_file = None
        start_index = None
        start_distance = float("inf")
        force_direction = None

        for filename, meta in self.gpx_index.items():
            if previous_last_file and filename == previous_last_file["file"]:
                start_file = filename
                start_index = previous_last_file["end_index"]
                last_point = meta["points"][start_index]
                start_distance = haversine(start_lat, start_lon, last_point["lat"], last_point["lon"])

                force_direction = "backward" if previous_last_file.get("reversed", False) else "forward"

                print(f"🔗 Fortsetzung erkannt: {start_file} ab Index {start_index}")
                print(f"🔗 Erzwungene Richtung: {force_direction} (vom Vortag)")
                break
            else:
                idx, dist = find_closest_point_in_track(meta["points"], start_lat, start_lon)
                if dist < start_distance:
                    start_distance = dist
                    start_file = filename
                    start_index = idx

        print(f"📍 Start: {start_file} (Index {start_index}, Distanz: {start_distance:.1f}m)")

        return start_file, start_index, force_direction

    def _find_target_pos(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
    ) -> TargetPosResult:
        """Bestimmt die Zielposition und die relevante Ziel-Seite für die Routensuche.

        Diese Methode implementiert die zentrale Logik für effizientes Routing:

        1. Findet den Track der dem Ziel am nächsten liegt
        2. Bestimmt, welche Seite dieses Tracks (Anfang oder Ende) näher am Start ist
        3. Diese "Ziel-Seite" wird zur Referenz für alle Zwischenschritte

        **Warum die Ziel-Seite wichtig ist:**
        Stell dir vor, der Ziel-Track verläuft von Nord nach Süd. Wenn der Startpunkt
        im Norden liegt, sollten alle Zwischen-Tracks zum Nord-Ende des Ziel-Tracks
        führen. Würden wir stattdessen den nächsten Punkt zum Ziel selbst suchen,
        könnten wir ineffiziente Routen erhalten, die erst zum Süd-Ende fahren und
        dann zurück.

        Args:
            start_lat: Breitengrad des Startpunkts in Dezimalgrad.
            start_lon: Längengrad des Startpunkts in Dezimalgrad.
            target_lat: Breitengrad des Zielpunkts (Unterkunft) in Dezimalgrad.
            target_lon: Längengrad des Zielpunkts (Unterkunft) in Dezimalgrad.

        Returns:
            Tuple aus:
                - target_file (str): Dateiname der Ziel-GPX-Datei.
                - target_index (int): Index des dem Ziel nächstgelegenen Punkts.
                - target_side_lat (float): Breitengrad der relevanten Ziel-Seite
                  (Start- oder End-Punkt des Ziel-Tracks).
                - target_side_lon (float): Längengrad der relevanten Ziel-Seite
                  (Start- oder End-Punkt des Ziel-Tracks).

        Note:
            Die Ziel-Seite (target_side_lat/lon) repräsentiert denjenigen Endpunkt
            des Ziel-Tracks (Anfang oder Ende), der dem Startort am nächsten ist.
            Diese Koordinate wird in allen folgenden Routenschritten als Zielpunkt
            verwendet, um eine konsistente Annäherung zu gewährleisten.
        """
        target_file = None
        target_index = None
        target_distance = float("inf")
        start_point = None
        end_point = None

        for filename, meta in self.gpx_index.items():
            idx, dist = find_closest_point_in_track(meta["points"], target_lat, target_lon)
            if dist < target_distance:
                target_distance = dist
                target_file = filename
                target_index = idx

                start_point = meta["points"][0]
                end_point = meta["points"][-1]

        dist_to_start = haversine(start_lat, start_lon, start_point["lat"], start_point["lon"])
        dist_to_end = haversine(start_lat, start_lon, end_point["lat"], end_point["lon"])

        if dist_to_start < dist_to_end:
            target_side_lat = start_point["lat"]
            target_side_lon = start_point["lon"]
            print(f"🎯 Ziel-Track {target_file}: Start-Seite näher am Startort")
        else:
            target_side_lat = end_point["lat"]
            target_side_lon = end_point["lon"]
            print(f"🎯 Ziel-Track {target_file}: End-Seite näher am Startort")

        print(f"🎯 Ziel: {target_file} (Index {target_index}, Distanz: {target_distance:.1f}m)")
        print(f"🎯 Ziel-Seite Position: ({target_side_lat:.6f}, {target_side_lon:.6f})")
        print()

        return target_file, target_index, target_side_lat, target_side_lon

    def _init_end_index(
        self,
        current_index: int,
        meta: Dict,
        force_direction: str,
        target_side_lat: float,
        target_side_lon: float,
    ) -> int:
        """Initialisiert den Endindex bei erzwungener Fahrtrichtung (Fortsetzung vom Vortag).

        Bei mehrtägigen Touren muss die Richtung vom Vortag beibehalten werden.
        Diese Methode findet in der erzwungenen Richtung den Punkt, der der
        relevanten Ziel-Seite am nächsten ist.

        Args:
            current_index: Aktueller Startindex im Track (Fortsetzungspunkt vom Vortag).
            meta: Metadaten des aktuellen GPX-Tracks aus gpx_index.
            force_direction: Erzwungene Richtung - entweder 'forward' (vorwärts durch
                            den Track) oder 'backward' (rückwärts durch den Track).
            target_side_lat: Breitengrad der relevanten Ziel-Seite (siehe _find_target_pos).
            target_side_lon: Längengrad der relevanten Ziel-Seite (siehe _find_target_pos).

        Returns:
            Berechneter Endindex im Track. Dies ist der Punkt in der erzwungenen Richtung,
            der der Ziel-Seite am nächsten ist.

        Note:
            Bei 'forward' werden nur Punkte nach current_index betrachtet,
            bei 'backward' nur Punkte vor current_index.
        """
        if force_direction == "forward":
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                if point["index"] <= current_index:
                    continue
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Vorwärts (erzwungen): Index {end_index} (Distanz: {best_dist:.1f}m)")

        else:  # backward
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                if point["index"] >= current_index:
                    continue
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Rückwärts (erzwungen): Index {end_index} (Distanz: {best_dist:.1f}m)")

        return end_index

    def _set_end_index(
        self,
        current_index: int,
        meta: Dict,
        force_direction: Optional[str],
        target_side_lat: float,
        target_side_lon: float,
        iteration: int,
    ) -> int:
        """Bestimmt den Endindex für den aktuellen Track-Abschnitt.

        In der ersten Iteration bei Fortsetzung vom Vortag wird die erzwungene Richtung
        verwendet. In allen anderen Fällen wird der Punkt im gesamten Track gesucht,
        der der Ziel-Seite am nächsten ist (unabhängig von der Fahrtrichtung).

        **Warum zur Ziel-Seite navigieren:**
        Durch die Orientierung an der Ziel-Seite (nicht am Ziel selbst) wird in jedem
        Schritt der Routensuche auf die richtige Seite des Ziel-Tracks zugesteuert.
        Dies verhindert ineffiziente Umwege.

        Args:
            current_index: Aktueller Startindex im Track.
            meta: Metadaten des aktuellen GPX-Tracks aus gpx_index.
            force_direction: Optional erzwungene Richtung ('forward'/'backward') bei
                            Fortsetzung vom Vortag, sonst None.
            target_side_lat: Breitengrad der relevanten Ziel-Seite. Dies ist die
                            Koordinate, zu der wir in jedem Schritt navigieren.
            target_side_lon: Längengrad der relevanten Ziel-Seite.
            iteration: Aktuelle Iterationsnummer (0-basiert). Bei 0 mit force_direction
                      wird die erzwungene Richtung verwendet.

        Returns:
            Berechneter Endindex im Track. Dies ist der Punkt, der der Ziel-Seite
            am nächsten ist (unter Berücksichtigung der Richtungsvorgabe).
        """
        if iteration == 0 and force_direction is not None:
            end_index = self._init_end_index(current_index, meta, force_direction, target_side_lat, target_side_lon)
        else:
            best_idx = current_index
            best_dist = float("inf")

            for point in meta["points"]:
                dist = haversine(target_side_lat, target_side_lon, point["lat"], point["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_idx = point["index"]

            end_index = best_idx
            print(f"   🔍 Nächster Punkt zur Ziel-Seite: Index {end_index} (Distanz: {best_dist:.1f}m)")

        return end_index

    def _get_statistics4track(
        self,
        meta: Dict,
        current_index: int,
        end_index: int,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
        reversed_direction: bool,
    ) -> TrackStats:
        """Berechnet Statistiken für einen Track-Abschnitt zwischen zwei Indizes.

        Lädt die GPX-Datei, extrahiert den relevanten Abschnitt und berechnet:
        - Maximale Höhe
        - Distanz (aufsummiert über Punktabstände)
        - Positiver Höhenunterschied (nur Anstiege)

        Args:
            meta: Metadaten des GPX-Tracks aus gpx_index.
            current_index: Startindex des Abschnitts.
            end_index: Endindex des Abschnitts.
            max_elevation: Bisherige maximale Höhe in Metern (wird aktualisiert).
            total_distance: Bisherige Gesamtdistanz in Metern (wird aktualisiert).
            total_ascent: Bisheriger Gesamtanstieg in Metern (wird aktualisiert).
            reversed_direction: Wenn True, wird der Track-Abschnitt rückwärts
                               durchlaufen (Punkte in umgekehrter Reihenfolge).

        Returns:
            Tuple aus (max_elevation, total_distance, total_ascent) mit aktualisierten Werten.

        Note:
            Die Statistiken werden kumulativ berechnet, d.h. die übergebenen Werte
            werden mit den Werten des aktuellen Abschnitts erweitert.
        """
        mystart_index = min(current_index, end_index)
        myend_index = max(current_index, end_index)

        gpx = read_gpx_file(meta["file"])
        if gpx:
            segment_points = []
            point_counter = 0
            for track in gpx.tracks:
                for seg in track.segments:
                    if reversed_direction:
                        for p in seg.points[::-1]:
                            if mystart_index <= point_counter <= myend_index:
                                segment_points.append(p)
                            point_counter += 1
                    else:
                        for p in seg.points:
                            if mystart_index <= point_counter <= myend_index:
                                segment_points.append(p)
                            point_counter += 1

            prev = None
            for p in segment_points:
                if p.elevation is not None:
                    max_elevation = max(max_elevation, p.elevation)

                if prev:
                    d = haversine(prev.latitude, prev.longitude, p.latitude, p.longitude)
                    total_distance += d

                    if prev.elevation is not None and p.elevation is not None and p.elevation > prev.elevation:
                        total_ascent += p.elevation - prev.elevation
                prev = p

        print(f"   Punkte: {myend_index - mystart_index + 1}")

        return max_elevation, total_distance, total_ascent

    def _find_next_gpx_file(
        self,
        visited: set,
        used_base_files: set,
        current_lat: float,
        current_lon: float,
    ) -> Tuple[Optional[str], Optional[int]]:
        """Findet die nächste GPX-Datei in der Routenkette.

        Sucht unter allen noch nicht besuchten Dateien diejenige mit dem nächstgelegenen
        Punkt zur aktuellen Position. Berücksichtigt dabei:
        - Maximale Verbindungsdistanz (max_connection_distance_m)
        - Vermeidung bereits besuchter Dateien
        - Vermeidung derselben Basis-Route (z.B. Route und Route_reversed)
        - Bei ähnlichen Distanzen wird die kürzere Datei bevorzugt

        **Logik der Dateiauswahl:**
        Die Methode wählt primär nach geringster Distanz aus. Bei mehreren Kandidaten
        mit ähnlicher Distanz (<300m Unterschied) wird jedoch die kürzere Route
        bevorzugt, um unnötige Umwege zu vermeiden.

        Args:
            visited: Set mit bereits besuchten Dateinamen zur Vermeidung von Schleifen.
            used_base_files: Set mit bereits verwendeten Basis-Dateinamen (ohne
                            Richtungssuffixe) um zu verhindern, dass derselbe Track
                            in verschiedenen Richtungen verwendet wird.
            current_lat: Aktueller Breitengrad in Dezimalgrad.
            current_lon: Aktueller Längengrad in Dezimalgrad.

        Returns:
            Tuple aus:
                - next_file (str|None): Dateiname der nächsten GPX-Datei oder None
                  wenn keine passende Datei gefunden wurde.
                - next_index (int|None): Startindex im nächsten Track oder None.

        Note:
            Gibt (None, None) zurück wenn keine Datei innerhalb der max_connection_distance_m
            gefunden werden kann. In diesem Fall wird die Routensuche unterbrochen.
        """
        next_file = None
        next_index = None
        best_dist = None
        length_best_file = float("inf")

        print("   Suche nächste GPX-Datei...")
        for name, cand in self.gpx_index.items():
            if name in visited:
                continue

            cand_base = get_base_filename(name)
            if cand_base in used_base_files:
                continue

            length_file = cand["total_distance_m"]

            idx, dist = find_closest_point_in_track(cand["points"], current_lat, current_lon)

            print(length_file, name, dist)

            if dist > self.max_connection_distance_m:
                continue

            if best_dist is None or dist < best_dist or (dist <= best_dist + 300 and length_file < length_best_file):
                best_dist = dist
                next_file = name
                next_index = idx
                length_best_file = length_file

        if next_file:
            print(f"   ➡️  Nächste: {next_file} (Index {next_index}, Distanz: {best_dist:.1f}m)")
            print()

        return next_file, next_index

    def _add_target_track_to_route(
        self,
        target_file: str,
        target_index: int,
        current_lat: float,
        current_lon: float,
        route_files: List[Dict],
    ) -> None:
        """Fügt den Ziel-Track zur Route hinzu wenn kein Zwischen-Track gefunden wurde.

        Diese Methode wird aufgerufen, wenn die automatische Routensuche keinen
        passenden Zwischen-Track mehr findet (Distanz > max_connection_distance_m),
        aber der Ziel-Track noch nicht erreicht wurde. Der Ziel-Track wird dann
        direkt angehängt.

        **Richtungsbestimmung:**
        Die Methode wählt die Fahrtrichtung durch den Ziel-Track basierend darauf,
        welches Ende (Start oder Ende) näher an der aktuellen Position liegt.

        Args:
            target_file: Dateiname der Ziel-GPX-Datei.
            target_index: Index des Zielpunkts (Unterkunft) im Ziel-Track.
            current_lat: Aktueller Breitengrad in Dezimalgrad.
            current_lon: Aktueller Längengrad in Dezimalgrad.
            route_files: Liste von Route-Dictionaries die um den Ziel-Track erweitert
                        wird (in-place Modifikation).

        Note:
            Die Methode modifiziert route_files direkt ohne Rückgabewert.
        """
        print(f"   ➕ Füge Ziel-Track hinzu: {target_file}")

        target_meta = self.gpx_index[target_file]
        target_start_idx = 0
        target_end_idx = target_index

        dist_to_start = haversine(current_lat, current_lon, target_meta["points"][0]["lat"], target_meta["points"][0]["lon"])
        dist_to_end = haversine(current_lat, current_lon, target_meta["points"][-1]["lat"], target_meta["points"][-1]["lon"])

        if dist_to_end < dist_to_start:
            target_start_idx = len(target_meta["points"]) - 1
            target_end_idx = target_index
            reversed_dir = True
        else:
            target_start_idx = 0
            target_end_idx = target_index
            reversed_dir = False

        if reversed_dir:
            route_files.append(
                {
                    "file": target_file,
                    "end_index": min(target_start_idx, target_end_idx),
                    "start_index": max(target_start_idx, target_end_idx),
                    "reversed": reversed_dir,
                }
            )
        else:
            route_files.append(
                {
                    "file": target_file,
                    "start_index": min(target_start_idx, target_end_idx),
                    "end_index": max(target_start_idx, target_end_idx),
                    "reversed": reversed_dir,
                }
            )

    def _process_route_iteration(
        self,
        iteration: int,
        current_file: str,
        current_index: int,
        target_file: str,
        target_index: int,
        visited: set,
        used_base_files: set,
        route_files: List[Dict],
        force_direction: Optional[str],
        target_side_lat: float,
        target_side_lon: float,
        max_elevation: float,
        total_distance: float,
        total_ascent: float,
    ) -> Tuple[bool, Optional[str], Optional[int], float, float, float, float, float]:
        """Verarbeitet eine einzelne Iteration der Routensuche.

        Führt für einen einzelnen Track-Abschnitt folgende Schritte aus:
        1. Validierung (bereits besucht? Metadaten vorhanden?)
        2. Bestimmung des Endindex (wohin im Track fahren?)
        3. Bestimmung der Fahrtrichtung (vorwärts/rückwärts)
        4. Aktualisierung der Statistiken (Distanz, Höhenmeter)
        5. Suche nach dem nächsten Track (falls Ziel noch nicht erreicht)

        Args:
            iteration: Aktuelle Iterationsnummer (0-basiert) für Logging.
            current_file: Name der aktuellen GPX-Datei.
            current_index: Aktueller Startindex im Track.
            target_file: Name der Ziel-GPX-Datei für Zielprüfung.
            target_index: Index des Zielpunkts im Ziel-Track.
            visited: Set mit bereits besuchten Dateinamen (wird erweitert).
            used_base_files: Set mit bereits verwendeten Basis-Dateinamen (wird erweitert).
            route_files: Liste von Route-Dictionaries (wird erweitert).
            force_direction: Optional erzwungene Richtung bei Fortsetzung vom Vortag.
            target_side_lat: Breitengrad der relevanten Ziel-Seite für Navigation.
            target_side_lon: Längengrad der relevanten Ziel-Seite für Navigation.
            max_elevation: Bisherige maximale Höhe in Metern (wird aktualisiert).
            total_distance: Bisherige Gesamtdistanz in Metern (wird aktualisiert).
            total_ascent: Bisheriger Gesamtanstieg in Metern (wird aktualisiert).

        Returns:
            Tuple aus:
                - should_continue (bool): True wenn weitere Iteration nötig, False wenn
                  Ziel erreicht oder Fehler aufgetreten.
                - next_file (str|None): Dateiname der nächsten GPX-Datei.
                - next_index (int|None): Startindex im nächsten Track.
                - current_lat (float): Aktueller Breitengrad nach diesem Schritt.
                - current_lon (float): Aktueller Längengrad nach diesem Schritt.
                - max_elevation (float): Aktualisierte maximale Höhe.
                - total_distance (float): Aktualisierte Gesamtdistanz.
                - total_ascent (float): Aktualisierter Gesamtanstieg.

        Note:
            Bei Fehlern (bereits besuchte Datei, fehlende Metadaten) wird should_continue=False
            zurückgegeben um die Routensuche zu beenden.
        """
        # Validierungen
        if current_file in visited:
            print(f"⚠️  Iteration {iteration + 1}: Datei {current_file} bereits besucht - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        meta = self.gpx_index.get(current_file)
        if meta is None:
            print(f"⚠️  Iteration {iteration + 1}: Keine Metadaten für {current_file} - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        base_name = get_base_filename(current_file)
        if base_name in used_base_files:
            print(f"⚠️  Iteration {iteration + 1}: Basis-Datei {base_name} bereits verwendet - Abbruch")
            return False, None, None, 0.0, 0.0, max_elevation, total_distance, total_ascent

        print(f"📁 Iteration {iteration + 1}: {current_file} (aktueller Index: {current_index})")

        # Bestimme Endindex
        if current_file == target_file:
            end_index = target_index
            print(f"   ✅ Zieldatei erreicht! Fahre zu Index {end_index}")
        else:
            end_index = self._set_end_index(current_index, meta, force_direction, target_side_lat, target_side_lon, iteration)

        # Bestimme Richtung
        if current_index <= end_index:
            reversed_direction = False
            direction_str = "vorwärts"
        else:
            reversed_direction = True
            direction_str = "rückwärts"

        print(f"   Richtung: {direction_str} (Index {current_index} -> {end_index})")

        # Markiere als besucht
        visited.add(current_file)
        used_base_files.add(base_name)

        # Füge zur Route hinzu
        route_files.append(
            {"file": current_file, "start_index": current_index, "end_index": end_index, "reversed": reversed_direction}
        )

        # Berechne Statistiken
        max_elevation, total_distance, total_ascent = self._get_statistics4track(
            meta, current_index, end_index, max_elevation, total_distance, total_ascent, reversed_direction
        )

        # Aktualisiere Position
        end_point = meta["points"][end_index]
        current_lat = end_point["lat"]
        current_lon = end_point["lon"]

        print(f"   Neue Position: ({current_lat:.6f}, {current_lon:.6f})")

        # Prüfe ob Ziel erreicht
        if current_file == target_file:
            print("✅ Ziel erreicht!")
            return False, None, None, current_lat, current_lon, max_elevation, total_distance, total_ascent

        # Finde nächste GPX
        next_file, next_index = self._find_next_gpx_file(visited, used_base_files, current_lat, current_lon)

        if next_file is None:
            print(f"⚠️  Keine passende nächste GPX gefunden (max. Distanz: {self.max_connection_distance_m}m)")

            if target_file not in visited:
                self._add_target_track_to_route(target_file, target_index, current_lat, current_lon, route_files)
            return False, None, None, current_lat, current_lon, max_elevation, total_distance, total_ascent

        return True, next_file, next_index, current_lat, current_lon, max_elevation, total_distance, total_ascent

    def collect_route_between_locations(
        self,
        start_lat: float,
        start_lon: float,
        target_lat: float,
        target_lon: float,
        booking: Dict,
        previous_last_file: Optional[Dict] = None,
    ) -> None:
        """Sammelt und verkettet GPX-Dateien zwischen Start- und Zielort.

        Dies ist die Hauptmethode für die Routenplanung. Sie implementiert einen
        intelligenten Algorithmus zur Verkettung mehrerer GPX-Tracks:

        **Algorithmus-Übersicht:**
        1. **Ziel-Seiten-Identifikation**: Bestimmt welche Seite (Anfang oder Ende)
           des Ziel-Tracks näher am Startort liegt. Diese Seite wird zur Referenz
           für die gesamte Routensuche.

        2. **Start-Optimierung**: Im Start-Track wird nicht zum nächsten Punkt zum
           Ziel selbst gefahren, sondern zum Punkt der der Ziel-Seite am nächsten
           ist. Dies verhindert ineffiziente Routenführung.

        3. **Iterative Verkettung**: Von diesem Punkt aus werden sukzessive weitere
           Tracks aneinandergehängt, wobei jeder Schritt zur Ziel-Seite navigiert.

        4. **Richtungserkennung**: Für jeden Track wird automatisch bestimmt, ob er
           vorwärts oder rückwärts durchfahren werden muss.

        **Beispiel:**
        Start in München, Ziel-Unterkunft in Garmisch. Der Ziel-Track verläuft
        von Mittenwald nach Garmisch. Da München nördlich von beiden liegt, ist
        das Nord-Ende (Mittenwald) die relevante Ziel-Seite. Alle Zwischen-Tracks
        werden so ausgewählt, dass sie sukzessive näher an Mittenwald führen, nicht
        direkt an Garmisch. Im Ziel-Track wird dann von Mittenwald nach Garmisch
        gefahren.

        Args:
            start_lat: Breitengrad des Startorts in Dezimalgrad.
            start_lon: Längengrad des Startorts in Dezimalgrad.
            target_lat: Breitengrad des Zielorts (Unterkunft) in Dezimalgrad.
            target_lon: Längengrad des Zielorts (Unterkunft) in Dezimalgrad.
            booking: Buchungs-/Tages-Dictionary zum Anreichern mit Route-Informationen.
                    Wird mit folgenden Keys erweitert:
                    - gpx_files: Liste der verwendeten Track-Abschnitte
                    - total_distance_km: Gesamtdistanz in Kilometern
                    - total_ascent_m: Gesamter positiver Höhenunterschied in Metern
                    - max_elevation_m: Höchster Punkt in Metern
                    - _last_gpx_file: Letzte Datei für Fortsetzung am nächsten Tag
            previous_last_file: Optional. Dictionary der letzten verwendeten GPX-Datei
                               vom Vortag für mehrtägige Touren mit Keys:
                               - 'file' (str): Dateiname
                               - 'end_index' (int): Letzter Index
                               - 'reversed' (bool): Fahrtrichtung

        Note:
            Die Methode modifiziert das booking-Dictionary direkt (in-place).
            Bei Fehlern werden Null-Werte in booking eingetragen.
        """
        print(f"\n{'=' * 80}")
        print(f"Route-Suche: ({start_lat:.6f}, {start_lon:.6f}) -> ({target_lat:.6f}, {target_lon:.6f})")
        if previous_last_file:
            print(f"🔗 Fortsetzung von: {previous_last_file['file']} (Index {previous_last_file['end_index']})")
        print(f"{'=' * 80}")

        # 1. Finde Start-Position
        start_file, start_index, force_direction = self._find_start_pos(start_lat, start_lon, previous_last_file)

        # 2. Finde Ziel-Position UND welche Seite des Ziel-Tracks näher am Start ist
        target_file, target_index, target_side_lat, target_side_lon = self._find_target_pos(
            start_lat, start_lon, target_lat, target_lon
        )

        if not start_file or not target_file:
            print("⚠️  Keine passenden GPX-Dateien gefunden!")
            booking["gpx_files"] = []
            booking["total_distance_km"] = 0
            booking["total_ascent_m"] = 0
            booking["max_elevation_m"] = None
            return

        visited = set()
        used_base_files = set()
        route_files = []

        current_file = start_file
        current_index = start_index

        total_distance = 0.0
        total_ascent = 0.0
        max_elevation = float("-inf")

        # Hauptschleife: Fahre von Start Richtung Ziel
        for iteration in range(self.max_chain_length):
            should_continue, next_file, next_index, current_lat, current_lon, max_elevation, total_distance, total_ascent = (
                self._process_route_iteration(
                    iteration=iteration,
                    current_file=current_file,
                    current_index=current_index,
                    target_file=target_file,
                    target_index=target_index,
                    visited=visited,
                    used_base_files=used_base_files,
                    route_files=route_files,
                    force_direction=force_direction,
                    target_side_lat=target_side_lat,
                    target_side_lon=target_side_lon,
                    max_elevation=max_elevation,
                    total_distance=total_distance,
                    total_ascent=total_ascent,
                )
            )

            if not should_continue:
                break

            current_file = next_file
            current_index = next_index

        print("\n📊 Zusammenfassung:")
        print(f"   Dateien: {len(route_files)}")
        print(f"   Gesamt-Distanz: {total_distance / 1000:.2f} km")
        print(f"   Gesamt-Aufstieg: {total_ascent:.0f} m")
        print(f"   Max. Höhe: {max_elevation:.0f} m" if max_elevation != float("-inf") else "   Max. Höhe: N/A")
        print(f"{'=' * 80}\n")

        booking["gpx_files"] = route_files
        booking["total_distance_km"] = round(total_distance / 1000, 2)
        booking["total_ascent_m"] = int(round(total_ascent))
        booking["max_elevation_m"] = int(round(max_elevation)) if max_elevation != float("-inf") else None

        # Speichere letzte Datei für nächste Suche
        if route_files:
            last = route_files[-1]
            booking["_last_gpx_file"] = {
                "file": last["file"],
                "end_index": last["end_index"],
                "reversed": last["reversed"],
            }

    def merge_gpx_files(self, route_files: List[Dict], output_dir: Path, booking: Dict) -> Optional[Path]:
        """Merged mehrere GPX-Track-Abschnitte zu einer einzelnen GPX-Datei.

        Erstellt eine neue GPX-Datei, die alle Track-Abschnitte der Route in der
        richtigen Reihenfolge und Richtung enthält. Berücksichtigt dabei Start- und
        End-Indizes für Teilstrecken sowie die Fahrtrichtung (vorwärts/rückwärts).

        Args:
            route_files: Liste von Dictionaries mit Track-Abschnittsinformationen.
                        Jedes Dictionary muss folgende Keys enthalten:
                        - file (str): GPX-Dateiname
                        - start_index (int): Start-Index im Track
                        - end_index (int): End-Index im Track
                        - reversed (bool): True für rückwärts, False für vorwärts
            output_dir: Ausgabeverzeichnis für die merged GPX-Datei.
            booking: Buchungs-Dictionary zur Generierung des Dateinamens.
                    Verwendet werden:
                    - arrival_date: Für Datumsprefix im Dateinamen
                    - hotel_name: Für lesbaren Dateinamen

        Returns:
            Path zur geschriebenen GPX-Datei oder None bei Fehler (z.B. leere route_files,
            Parsing-Fehler).

        Note:
            Der Dateiname wird automatisch generiert im Format:
            "{arrival_date}_{hotel_name_clean}_merged.gpx"
            Problematische Zeichen im Hotelnamen werden entfernt/ersetzt.
        """
        if route_files is None or len(route_files) == 0:
            print(f"route_files: {route_files}")
            return None

        merged_gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        merged_gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for entry in route_files:
            gpx_file = self.gpx_dir / entry["file"]
            start_idx = entry["start_index"]
            end_idx = entry["end_index"]
            reversed_dir = entry["reversed"]
            if reversed_dir:
                start_idx, end_idx = end_idx, start_idx

            gpx = read_gpx_file(gpx_file)
            if gpx is None or not gpx.tracks:
                continue

            # Sammle alle Punkte mit Index
            all_points = []
            point_counter = 0
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for p in seg.points:
                        if start_idx <= point_counter <= end_idx:
                            all_points.append(p)
                        point_counter += 1

            # Invertiere falls nötig
            if reversed_dir:
                all_points = all_points[::-1]

            # Füge Punkte zum merged Track hinzu
            for p in all_points:
                segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(latitude=p.latitude, longitude=p.longitude, elevation=p.elevation, time=p.time)
                )

        output_dir.parent.mkdir(parents=True, exist_ok=True)

        # Erstelle aussagekräftigen Dateinamen
        arrival_date = booking.get("arrival_date", "unknown_date")
        hotel_name = booking.get("hotel_name", "unknown_hotel")
        # Entferne problematische Zeichen aus Hotelnamen
        hotel_name_clean = "".join(c for c in hotel_name if c.isalnum() or c in (" ", "-", "_")).strip()
        hotel_name_clean = hotel_name_clean.replace(" ", "_")[:30]

        out_name = f"{arrival_date}_{hotel_name_clean}_merged.gpx"
        output_path = output_dir / out_name

        output_path.write_text(merged_gpx.to_xml(), encoding="utf-8")

        print(f"💾 Merged GPX gespeichert: {output_path.name}")

        return output_path

    def process_all_bookings(self, bookings: List[Dict], output_dir: Path) -> List[Dict]:
        """Verarbeitet alle Buchungen und erstellt GPS-Tracks für jeden Reisetag.

        Durchläuft alle Buchungen chronologisch und sammelt für jeden Tag die
        passenden GPS-Tracks. Berücksichtigt dabei die Fortsetzung mehrtägiger
        Touren (previous_last_file).

        **Ablauf:**
        1. Sortierung der Buchungen nach Anreisedatum
        2. Für jede Buchung (außer der ersten):
           - Sammle Route vom vorherigen Zielort zum aktuellen
           - Merge alle Track-Abschnitte zu einer GPX-Datei
           - Speichere letzte verwendete Datei für nächsten Tag
        3. Rückgabe der angereicherten Buchungen

        Args:
            bookings: Liste mit Buchungs-Dictionaries. Jedes Dictionary sollte
                     mindestens folgende Keys enthalten:
                     - arrival_date: ISO-formatiertes Datum (YYYY-MM-DD)
                     - hotel_name: Name der Unterkunft
                     - latitude: Breitengrad der Unterkunft
                     - longitude: Längengrad der Unterkunft
            output_dir: Ausgabepfad für merged GPX-Dateien.

        Returns:
            Sortierte Liste der Buchungen angereichert mit GPS-Track-Informationen:
            - gpx_files: Liste der verwendeten Track-Abschnitte
            - total_distance_km: Gesamtdistanz in Kilometern
            - total_ascent_m: Gesamter positiver Höhenunterschied in Metern
            - max_elevation_m: Höchster Punkt in Metern
            - _last_gpx_file: Letzte Datei für Fortsetzung (interne Information)

        Note:
            Die erste Buchung erhält keine Route-Informationen, da kein Startpunkt
            existiert. Buchungen ohne Koordinaten werden übersprungen.
        """
        # Nach Anreisedatum sortieren
        bookings_sorted = sorted(bookings, key=lambda x: x.get("arrival_date", "9999-12-31"))

        prev_lat = prev_lon = None
        previous_last_file = None

        for booking in bookings_sorted:
            print(booking.get("hotel_name"))

            lat = booking.get("latitude", None)
            lon = booking.get("longitude", None)

            if prev_lon and lon and lat:
                self.collect_route_between_locations(
                    prev_lat, prev_lon, lat, lon, booking, previous_last_file=previous_last_file
                )

                # TODO: ergänze _last_gpx_file um die Strecke bis zur Unterkunft
                self.extend_track2hotel(booking, output_dir)

                self.merge_gpx_files(booking.get("gpx_files"), output_dir, booking)

                # Speichere letzte Datei für nächste Iteration
                previous_last_file = booking.get("_last_gpx_file")

            prev_lat = lat
            prev_lon = lon

        return bookings_sorted

    def extend_track2hotel(self, booking: Dict, output_path: Path):
        lat = booking["latitude"]
        lon = booking["longitude"]

        # closest = find_closest_gpx_point(GPX_DIR, lat, lon)

        # Cache closest point für spätere Verwendung
        # booking["_closest_point_cache"] = {
        #     "file": str(closest["file"]),
        #     "distance": closest["distance"],
        #     "index": closest["index"],
        # }

        output_path = self.extend_gpx_route(
            # hier anderes Argument übergeben, im Grunde _last_gpx_file aus booking, Argument umbenennen
            closest_point=booking["_last_gpx_file"],
            target_lat=lat,
            target_lon=lon,
            route_provider_func=route_to_address,
            output_dir=output_path,
            filename_suffix=booking["arrival_date"],
        )

        if output_path:
            print(f"GPX erweitert: {output_path}")
        else:
            print(f"Fehler beim Erweitern der Route für {booking['hotel_name']}")

    def extend_gpx_route(
        self,
        closest_point: Dict,
        target_lat: float,
        target_lon: float,
        route_provider_func,
        output_dir: Path,
        filename_suffix: str,
    ) -> Optional[Path]:
        """Erweitert eine GPX-Route um eine berechnete Strecke zu einer Zieladresse.

        # TODO: Methode so ändern, dass _last_gpx_file von dem nächsten Punkt zur Unterkunft (target_lon, lat), das
        #  müsste der end_point des tracks sein, bis zur unterkunft verlängert wird.

        Fügt eine neue Route vom nächstgelegenen Punkt in der GPX-Datei zur Zieladresse
        ein und speichert die modifizierte GPX-Datei. Die Route wird vom route_provider_func
        berechnet (z.B. BRouter).

        **Anwendungsfall:**
        Diese Funktion wird verwendet, um GPX-Tracks direkt zu Unterkünften zu verlängern,
        wenn die Unterkunft nicht auf dem Track liegt. Die Hauptverwendung ist jedoch durch
        GPXRouteManager.collect_route_between_locations ersetzt worden.

        Args:
            closest_point: Dictionary mit Informationen zum nächstgelegenen Punkt.
                          Muss folgende Keys enthalten:
                          - file (Path): Pfad zur GPX-Datei
                          - segment: GPX-Segment-Objekt
                          - index (int): Index des Punkts im Segment
                          Typischerweise von find_closest_gpx_point() zurückgegeben.
            target_lat: Ziel-Breitengrad in Dezimalgrad.
            target_lon: Ziel-Längengrad in Dezimalgrad.
            route_provider_func: Funktion zur Routenberechnung. Muss die Signatur
                                (lat_from, lon_from, lat_to, lon_to) haben und einen
                                GPX-String zurückgeben. Beispiel: route_to_address von BRouter.
            output_dir: Ausgabeverzeichnis für die modifizierte GPX-Datei.
            filename_suffix: Suffix für den Dateinamen (z.B. Anreisedatum im Format YYYY-MM-DD).

        Returns:
            Path zur gespeicherten GPX-Datei oder None bei Fehler.

        Raises:
            ValueError: Wenn die Route nicht berechnet werden kann oder die GPX-Datei
                       nicht geladen werden kann.

        Note:
            Diese Funktion ist für Kompatibilität mit älterem Code vorhanden.
            Für neue Implementierungen sollte GPXRouteManager verwendet werden.
        """
        try:
            # Original GPX laden
            gpx = read_gpx_file(closest_point["file"])
            if gpx is None:
                raise ValueError(f"Konnte {closest_point['file'].name} nicht lesen")

            # WICHTIG: closest_point["segment"] ist eine Referenz aus einer anderen
            # GPX-Instanz. Wir müssen das entsprechende Segment in der neu geladenen
            # GPX-Datei finden. Dazu nutzen wir den gespeicherten Index.
            idx = closest_point["index"]

            # Finde das richtige Segment durch erneutes Durchsuchen
            target_point = closest_point["segment"].points[idx]
            found_seg = None
            found_idx = None

            for track in gpx.tracks:
                for seg in track.segments:
                    for i, p in enumerate(seg.points):
                        # Prüfe ob dies der gleiche Punkt ist (mit kleiner Toleranz)
                        if (
                            abs(p.latitude - target_point.latitude) < 0.000001
                            and abs(p.longitude - target_point.longitude) < 0.000001
                        ):
                            found_seg = seg
                            found_idx = i
                            break
                    if found_seg:
                        break
                if found_seg:
                    break

            if found_seg is None:
                raise ValueError("Konnte Einfügepunkt in neu geladener GPX nicht finden")

            seg = found_seg
            idx = found_idx

            if idx >= len(seg.points):
                raise ValueError(f"Index {idx} außerhalb des gültigen Bereichs")

            p = seg.points[idx]

            # Route zur Zieladresse berechnen
            route_gpx_str = route_provider_func(p.latitude, p.longitude, target_lat, target_lon)

            if not route_gpx_str or not route_gpx_str.strip():
                raise ValueError("Route-Provider gab leere Antwort zurück")

            # Route parsen
            route_gpx = gpxpy.parse(route_gpx_str)

            # Validierung: Route muss mindestens einen Track mit Segment haben
            if not route_gpx.tracks or not route_gpx.tracks[0].segments:
                raise ValueError("Berechnete Route enthält keine Tracks/Segmente")

            new_points = route_gpx.tracks[0].segments[0].points

            if not new_points:
                raise ValueError("Berechnete Route enthält keine Punkte")

            # Route in Original-GPX einfügen (nach dem nächsten Punkt)
            seg.points[idx + 1 : idx + 1] = new_points

            # Ausgabedatei speichern
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = f"{closest_point['file'].stem}_{filename_suffix}.gpx"
            output_path = output_dir / out_name

            output_path.write_text(gpx.to_xml(), encoding="utf-8")

            return output_path

        except gpxpy.gpx.GPXException as e:
            print(f"GPX-Fehler: {e}")
            return None
        except Exception as e:
            print(f"Fehler beim Erweitern der Route: {e}")
            return None
