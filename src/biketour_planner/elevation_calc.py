"""Verbesserte Höhenmeterberechnung mit Glättung und Schwellwert."""

import numpy as np


def calculate_elevation_gain_simple(
    elevations: list[float], threshold: float = 3.0, calculate_descent: bool = False
) -> float:
    """Berechnet positive Höhenmeter mit Schwellwert (einfache Methode).

    Diese Methode ignoriert kleine Schwankungen unter dem Schwellwert und
    zählt nur signifikante Anstiege.

    Args:
        elevations: Liste der Höhenwerte in Metern.
        threshold: Minimaler Höhenunterschied in Metern der gezählt wird (Default: 3m).
        calculate_descent: Wenn True, werden Abstiege berechnet statt Anstiege.

    Returns:
        Gesamter positiver Höhenunterschied in Metern.

    Example:
        >>> elevations = [100, 102, 99, 103, 101, 110, 108, 115]
        >>> gain = calculate_elevation_gain_simple(elevations, threshold=3.0)
        >>> print(f"{gain:.0f}m")  # Erwartet: ~15m (3+7+7)
    """
    if not elevations or len(elevations) < 2:
        return 0.0

    total_gain = 0.0
    accumulated_diff = 0.0

    for i in range(1, len(elevations)):
        if elevations[i] is None or elevations[i - 1] is None:
            continue

        diff = elevations[i] - elevations[i - 1]
        if calculate_descent:
            diff = -diff

        if diff > 0:
            accumulated_diff += diff

            # Wenn akkumulierter Anstieg über Schwellwert, zähle ihn
            if accumulated_diff >= threshold:
                total_gain += accumulated_diff
                accumulated_diff = 0.0
        else:
            # Bei Abstieg: Reset der Akkumulation
            accumulated_diff = 0.0

    return total_gain


def calculate_elevation_gain_smoothed(
    elevations: list[float], window_size: int = 5, threshold: float = 3.0, calculate_descent: bool = False
) -> float:
    """Berechnet positive Höhenmeter mit Glättung (empfohlene Methode).

    Diese Methode glättet zuerst die Höhendaten mit einem gleitenden Durchschnitt
    um GPS-Rauschen zu reduzieren, und zählt dann nur signifikante Anstiege.

    Args:
        elevations: Liste der Höhenwerte in Metern.
        window_size: Fenstergröße für gleitenden Durchschnitt (Default: 5 Punkte).
        threshold: Minimaler Höhenunterschied in Metern der gezählt wird (Default: 3m).
        calculate_descent: Wenn True, werden Abstiege berechnet statt Anstiege.

    Returns:
        Gesamter positiver Höhenunterschied in Metern.

    Example:
        >>> elevations = [100, 102, 99, 103, 101, 110, 108, 115, 113, 120]
        >>> gain = calculate_elevation_gain_smoothed(elevations)
        >>> print(f"{gain:.0f}m")  # Glattere, realistischere Werte
    """
    if not elevations or len(elevations) < 2:
        return 0.0

    # Filtere None-Werte
    valid_elevations = [e for e in elevations if e is not None]

    if len(valid_elevations) < window_size + 1:
        # Fallback auf einfache Methode bei zu wenig Punkten
        return calculate_elevation_gain_simple(valid_elevations, threshold, calculate_descent)

    # Glättung mit gleitendem Durchschnitt
    smoothed = np.convolve(valid_elevations, np.ones(window_size) / window_size, mode="valid")

    # Berechne Anstiege mit Schwellwert über die einfache Methode
    return calculate_elevation_gain_simple(smoothed.tolist(), threshold, calculate_descent)


def calculate_elevation_gain_segment_based(
    elevations: list[float], min_segment_length: int = 10, calculate_descent: bool = False
) -> float:
    """Berechnet positive oder negative Höhenmeter segment-basiert (robusteste Methode).

    Diese Methode identifiziert zusammenhängende Anstiegs- und Abstiegssegmente
    und summiert nur die Netto-Anstiege bzw. Netto-Abstiege jedes Segments.
    Dies ist die genaueste Methode für reale GPS-Tracks.

    Args:
        elevations: Liste der Höhenwerte in Metern.
        min_segment_length: Minimale Anzahl Punkte für ein gültiges Segment (Default: 10).
        calculate_descent: Wenn True, werden Abstiege berechnet statt Anstiege (Default: False).

    Returns:
        Gesamter positiver Höhenunterschied (Anstiege) oder negativer Höhenunterschied
        (Abstiege) in Metern, je nach calculate_descent Parameter.

    Example:
        >>> elevations = list(range(100, 200, 5)) + list(range(200, 180, -2)) + list(range(180, 250, 3))
        >>> ascent = calculate_elevation_gain_segment_based(elevations)
        >>> descent = calculate_elevation_gain_segment_based(elevations, calculate_descent=True)
        >>> print(f"Anstiege: {ascent:.0f}m, Abstiege: {descent:.0f}m")
    """
    if not elevations or len(elevations) < 2:
        return 0.0

    # Filtere None-Werte
    valid_elevations = [e for e in elevations if e is not None]

    if len(valid_elevations) < min_segment_length:
        # Fallback auf einfache Methode (ohne Schwellwert) für sehr kurze Tracks
        return calculate_elevation_gain_simple(valid_elevations, threshold=0.0, calculate_descent=calculate_descent)

    # Glättung (kleines Fenster um nur Rauschen zu entfernen)
    window = 3
    smoothed = np.convolve(valid_elevations, np.ones(window) / window, mode="valid")

    # Finde Wendepunkte (Übergang Anstieg <-> Abstieg)
    is_ascending = []
    for i in range(1, len(smoothed)):
        is_ascending.append(smoothed[i] > smoothed[i - 1])

    # Identifiziere Segmente
    segments = []
    segment_start = 0
    current_direction = is_ascending[0] if is_ascending else None

    for i in range(1, len(is_ascending)):
        if is_ascending[i] != current_direction:
            # Richtungswechsel -> Segment abschließen
            segments.append(
                {
                    "start": segment_start,
                    "end": i,
                    "ascending": current_direction,
                    "elevation_change": smoothed[i] - smoothed[segment_start],
                }
            )
            segment_start = i
            current_direction = is_ascending[i]

    # Letztes Segment
    if segment_start < len(smoothed) - 1:
        segments.append(
            {
                "start": segment_start,
                "end": len(smoothed) - 1,
                "ascending": current_direction,
                "elevation_change": smoothed[-1] - smoothed[segment_start],
            }
        )

    # Summiere aufsteigende oder absteigende Segmente
    if calculate_descent:
        # Summiere Abstiege (negative elevation_change, als Absolutwert)
        total = sum(abs(seg["elevation_change"]) for seg in segments if not seg["ascending"] and seg["elevation_change"] < 0)
    else:
        # Summiere Anstiege (positive elevation_change)
        total = sum(seg["elevation_change"] for seg in segments if seg["ascending"] and seg["elevation_change"] > 0)

    return total


# Beispiel-Vergleich der drei Methoden
if __name__ == "__main__":
    # Simuliere realistischen GPS-Track mit Rauschen
    # 100m Start, Anstieg auf 300m, Abstieg auf 250m, Anstieg auf 400m
    np.random.seed(42)

    # Perfekte Höhenwerte
    perfect_elevations = (
        list(range(100, 300, 2))
        + list(range(300, 250, -1))  # 200m Anstieg
        + list(range(250, 400, 3))  # 50m Abstieg  # 150m Anstieg
    )

    # Füge GPS-Rauschen hinzu (±5m)
    noisy_elevations = [e + np.random.uniform(-5, 5) for e in perfect_elevations]

    print("Vergleich der Berechnungsmethoden:")
    print("Erwartete Höhenmeter: 350m (200m + 150m)")
    print()

    # Alte Methode (wie in deinem Code)
    old_method = 0.0
    for i in range(1, len(noisy_elevations)):
        if noisy_elevations[i] > noisy_elevations[i - 1]:
            old_method += noisy_elevations[i] - noisy_elevations[i - 1]

    print(f"Alte Methode (jeder Punkt):     {old_method:.0f}m ❌ (zu hoch wegen Rauschen)")
    print(f"Einfach mit Schwellwert (3m):   {calculate_elevation_gain_simple(noisy_elevations):.0f}m")
    print(f"Geglättet (empfohlen):          {calculate_elevation_gain_smoothed(noisy_elevations):.0f}m ✅")
    print(f"Segment-basiert (robustest):    {calculate_elevation_gain_segment_based(noisy_elevations):.0f}m ✅")
