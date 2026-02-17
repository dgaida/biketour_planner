# Fehlerbehebung

## Häufige Probleme

### BRouter nicht erreichbar

**Symptom:** Fehlermeldung bezüglich Verbindung zu `localhost:17777`.

**Lösung:**
1. Stellen Sie sicher, dass der BRouter-Docker-Container läuft: `docker ps`.
2. Prüfen Sie, ob der Port 17777 gemappt ist.
3. Kontrollieren Sie, ob die benötigten `.rd5`-Kacheln im gemounteten Verzeichnis vorhanden sind.

### Geokodierung schlägt fehl

**Symptom:** Unterkunft hat keine Koordinaten (0.0, 0.0) oder Fehler bei der Adresssuche.

**Lösung:**
1. Überprüfen Sie die Adresse in der HTML-Datei. Manchmal sind Namen von Unterkünften in den Bestätigungs-E-Mails nicht eindeutig genug.
2. Versuchen Sie, die Adresse in `geocode.py` manuell zu testen oder passen Sie sie in der Quelldatei an.

### GPX-Tracks werden nicht verbunden

**Symptom:** Routen zwischen Unterkünften fehlen oder sind unvollständig.

**Lösung:**
1. Prüfen Sie den `max_connection_distance_m` Parameter in der Konfiguration. Wenn Ihre Tracks zu weit auseinander liegen, werden sie nicht automatisch verbunden.
2. Stellen Sie sicher, dass alle GPX-Dateien im konfigurierten Verzeichnis liegen.
3. Prüfen Sie die Logs auf "No tracks found within radius".

## Logs einsehen

Logs werden standardmäßig in den Ordner `logs/` geschrieben. Erhöhen Sie den Log-Level in der Konfiguration auf `DEBUG` für detailliertere Informationen.
