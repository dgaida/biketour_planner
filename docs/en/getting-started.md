# Quick Start (5 Minutes)

## 1️⃣ Installation

```bash
git clone https://github.com/dgaida/biketour_planner.git
cd biketour_planner
pip install -e .
```

## 2️⃣ Start BRouter

```bash
# Download routing data for your region (e.g., Europe)
mkdir -p brouter_data
cd brouter_data
wget https://brouter.de/brouter/segments4/E10_N45.rd5  # Example: Alps

# Start BRouter
docker run -d -p 17777:17777 \
  -v $(pwd):/segments4 \
  --name brouter \
  brouter/brouter:latest
```

The file `start_brouter.bat` is available to start the Docker container on Windows. Docker must be running before executing it.

## 3️⃣ Run Example Tour

```bash
# Create directory structure
mkdir -p my_tour/booking my_tour/gpx

# Place your Booking.com HTML confirmations in my_tour/booking/
# Place your GPX tracks in my_tour/gpx/

# Run the planner
python main.py \
  --booking-dir my_tour/booking \
  --gpx-dir my_tour/gpx \
  --output-dir my_tour/output

# Open the generated PDF
open my_tour/output/Reiseplanung_*.pdf
```

## 🎯 Next Steps

- **Add Mountain Passes:** Create `my_tour/gpx/Paesse.json` with pass names.
- **Tourist Sights:** Add `GEOAPIFY_API_KEY` to `secrets.env`.
- **Additional Info:** Create `my_tour/booking/Reiseplanung_Fahrrad.xlsx`.

See the [Workflow Documentation](index.md#typical-workflow) for details.
