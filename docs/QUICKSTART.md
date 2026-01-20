# Quick Start (5 Minuten)

## 1️⃣ Installation

```bash
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner
pip install -e .
```

## 2️⃣ BRouter starten

```bash
# Lade Routing-Daten für deine Region (z.B. Europa)
mkdir -p brouter_data
cd brouter_data
wget https://brouter.de/brouter/segments4/E10_N45.rd5  # Beispiel: Alpen

# Starte BRouter
docker run -d -p 17777:17777 \
  -v $(pwd):/segments4 \
  --name brouter \
  brouter/brouter:latest
```

Ich habe die Datei `start_brouter.bat` die den Docker Container startet. Docker muss dafür vorher gestartet werden.

## 3️⃣ Beispiel-Tour ausführen

```bash
# Erstelle Verzeichnisstruktur
mkdir -p my_tour/booking my_tour/gpx

# Lege deine Booking.com HTML-Bestätigungen in my_tour/booking/
# Lege deine GPX-Tracks in my_tour/gpx/

# Führe Planner aus
python main.py \
  --booking-dir my_tour/booking \
  --gpx-dir my_tour/gpx \
  --output-dir my_tour/output

# Öffne generiertes PDF
open my_tour/output/Reiseplanung_*.pdf
```

## 🎯 Nächste Schritte

- **Pässe hinzufügen:** Erstelle `my_tour/gpx/Paesse.json` mit Pass-Namen
- **Sehenswürdigkeiten:** Füge `GEOAPIFY_API_KEY` zu `secrets.env` hinzu
- **Zusatzinfos:** Erstelle `my_tour/booking/Reiseplanung_Fahrrad.xlsx`

Siehe [Workflow-Dokumentation](../README.md#typical-workflow) für Details.
