# Schnelleinstieg (5 Minuten)

## 1️⃣ Installation

```bash
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner
pip install -e .
```

## 2️⃣ BRouter starten

```bash
# Lade Routing-Daten für deine Region (z.B. Europa) herunter
mkdir -p brouter_data
cd brouter_data
wget https://brouter.de/brouter/segments4/E10_N45.rd5  # Beispiel: Alpen

# BRouter starten
docker run -d -p 17777:17777 \
  -v $(pwd):/segments4 \
  --name brouter \
  brouter/brouter:latest
```

Es gibt auch die Datei `start_brouter.bat`, die den Docker-Container unter Windows startet. Docker muss dafür vorher gestartet sein.

## 3️⃣ Beispiel-Tour ausführen

```bash
# Verzeichnisstruktur erstellen
mkdir -p my_tour/booking my_tour/gpx

# Legen Sie Ihre Booking.com HTML-Bestätigungen in my_tour/booking/ ab
# Legen Sie Ihre GPX-Tracks in my_tour/gpx/ ab

# Planer ausführen
python main.py \
  --booking-dir my_tour/booking \
  --gpx-dir my_tour/gpx \
  --output-dir my_tour/output

# Generiertes PDF öffnen
open my_tour/output/Reiseplanung_*.pdf
```

## 🎯 Nächste Schritte

- **Pässe hinzufügen**: Erstellen Sie `my_tour/gpx/Paesse.json` mit Pass-Namen.
- **Sehenswürdigkeiten**: Fügen Sie `GEOAPIFY_API_KEY` zu `secrets.env` hinzu.
- **Zusatzinfos**: Erstellen Sie `my_tour/booking/Reiseplanung_Fahrrad.xlsx`.

Siehe [Workflow-Dokumentation](index.md#typischer-workflow) für Details.
