# Installation

## Option 1: pip

```bash
# Repository klonen
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Abhängigkeiten installieren
pip install -r requirements.txt

# Paket im bearbeitbaren Modus installieren
pip install -e .
```

## Option 2: Conda / Mamba

```bash
# Repository klonen
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner

# Umgebung erstellen und aktivieren
conda env create -f environment.yml
conda activate biketour_planner
```

## Anforderungen

Python **3.9 oder neuer** ist erforderlich.

## Optional: Entdeckung von Sehenswürdigkeiten aktivieren

Um die Geoapify-Integration für die Suche nach Touristenattraktionen zu nutzen:

1. Erstellen Sie ein kostenloses Konto unter [https://www.geoapify.com](https://www.geoapify.com)
2. Holen Sie sich Ihren API-Schlüssel (kostenloses Kontingent: 3.000 Anfragen/Tag)
3. Erstellen Sie eine `secrets.env`-Datei im Projektstamm:

```bash
GEOAPIFY_API_KEY=ihr_api_schlüssel_hier
```

---

# BRouter Setup (Erforderlich)

Der Bike Tour Planner verlässt sich auf **BRouter** für das Offline-Fahrrad-Routing.

BRouter ist eine Open-Source-Routing-Engine, die von Arne Brenschede entwickelt wurde:
👉 [https://github.com/abrensch/brouter](https://github.com/abrensch/brouter)

## 1. Routing-Daten herunterladen (`.rd5`-Dateien)

BRouter verwendet vorverarbeitete OpenStreetMap-Daten, die in **5° × 5° Kacheln** unterteilt sind.

Laden Sie die benötigten `.rd5`-Dateien herunter von:

```
https://brouter.de/brouter/segments4/
```

Legen Sie diese in einem lokalen Verzeichnis ab, zum Beispiel:

```text
C:/brouter/segments4/
```

Stellen Sie sicher, dass Sie alle Kacheln herunterladen, die Ihr Tourengebiet abdecken.

---

## 2. BRouter über Docker starten

Ein laufender BRouter-HTTP-Server ist erforderlich.

### Verwendung von Docker (empfohlen):

```bash
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

### Oder aus dem bereitgestellten Dockerfile bauen:

```bash
cd brouter_docker
docker build -t brouter .
docker run --rm -p 17777:17777 \
  -v C:/brouter/segments4:/segments4 \
  brouter
```

Der Dienst wird verfügbar sein unter:

```
http://localhost:17777
```

Sie können ihn testen mit:

```bash
curl "http://localhost:17777/brouter?lonlats=16.44,43.51|18.09,42.65&profile=trekking&format=gpx"
```
