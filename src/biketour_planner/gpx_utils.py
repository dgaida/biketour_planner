import gpxpy
import math
from pathlib import Path


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_closest_gpx_point(gpx_dir, lat, lon):
    best = None

    for gpx_file in Path(gpx_dir).glob("*.gpx"):
        gpx = gpxpy.parse(gpx_file.read_text())
        for track in gpx.tracks:
            for seg in track.segments:
                for i, p in enumerate(seg.points):
                    d = haversine(lat, lon, p.latitude, p.longitude)
                    if best is None or d < best["distance"]:
                        best = {
                            "file": gpx_file,
                            "segment": seg,
                            "index": i,
                            "distance": d
                        }
    return best
