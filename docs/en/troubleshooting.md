# Troubleshooting

## Common Issues

### BRouter Unreachable

**Symptom:** Error message regarding connection to `localhost:17777`.

**Solution:**
1. Ensure the BRouter Docker container is running: `docker ps`.
2. Check if port 17777 is correctly mapped.
3. Verify that the required `.rd5` tiles are present in the mounted directory.

### Geocoding Fails

**Symptom:** Accommodation has no coordinates (0.0, 0.0) or error during address search.

**Solution:**
1. Check the address in the HTML file. Sometimes accommodation names in confirmation emails are not unique enough.
2. Try testing the address manually in `geocode.py` or adjust it in the source file.

### GPX Tracks Not Chained

**Symptom:** Routes between accommodations are missing or incomplete.

**Solution:**
1. Check the `max_connection_distance_m` parameter in the configuration. If your tracks are too far apart, they won't be chained automatically.
2. Ensure all GPX files are in the configured directory.
3. Check logs for "No tracks found within radius".

## Viewing Logs

Logs are written to the `logs/` folder by default. Increase the log level in the configuration to `DEBUG` for more detailed information.
