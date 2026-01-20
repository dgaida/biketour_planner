# Troubleshooting

## BRouter Connection Issues

**Problem:** `ConnectionError: BRouter Server nicht erreichbar`

**Solutions:**
1. Check if Docker container is running: `docker ps`
2. Verify port 17777 is accessible: `curl http://localhost:17777`
3. Ensure routing data is mounted correctly

## Geocoding Failures

**Problem:** `ValueError: Adresse konnte nicht geocodiert werden`

**Solutions:**
1. Check internet connection (Nominatim/Photon require internet)
2. Simplify address (remove apartment numbers, floor info)
3. Manually add coordinates to booking JSON

## Missing Elevation Data

**Problem:** `max_elevation_m: None` in output

**Solutions:**
1. Ensure GPX files contain `<ele>` tags
2. Use tools like GPSBabel to add elevation data
3. Download elevation-enriched tracks from sources like Komoot

## Pass Detection Failures

**Problem:** No passes detected despite having `Paesse.json`

**Solutions:**
1. Increase `hotel_radius_km` and `pass_radius_km`
2. Verify pass names can be geocoded (test manually)
3. Check that GPX tracks actually pass near the summit
