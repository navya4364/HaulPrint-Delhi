# HaulPrint Delhi

A geospatial transport-emissions simulator for solid waste in Delhi. It compares three waste transport strategies for a selected zone and estimates distance, fuel, CO₂, transport cost and tonne-km.

**Scenarios**
1. Baseline: the existing collection and haulage system
2. Optimised Routes: better routing, fewer empty trips
3. Decentralised Wet Waste + Hub: local processing of wet waste and a compaction hub for dry waste

## Data notice
All inputs are illustrative sample values, not official data. The project is not affiliated with any government body. Results are calculated from whatever inputs are entered.

## How it works
Enter waste generated, baseline route distance, vehicle mileage, diesel price, running cost and an emission factor. The simulator then calculates:

- Distance = baseline km × (1 − route distance cut)
- Fuel = distance ÷ mileage
- CO₂ = fuel × emission factor
- Cost = fuel × diesel price + distance × other running cost
- Tonne-km = waste hauled × average haul distance

## Tech used
Frontend: HTML, Tailwind CSS, JavaScript, Leaflet.js with OpenStreetMap, Chart.js.
Backend: Python, FastAPI, NetworkX, Pandas (in `api/index.py`). Hosted on Vercel.

## Limitations
Static waste weights, assumed distances (no live traffic), standard estimated emission factors, and scenario percentages that are assumptions until replaced by routing results.

## Backend
Choose **Network route model** in the dashboard. The backend builds a synthetic street grid with NetworkX, compares separate trips with consolidated loops, counts truck trips from load factors and calculates fuel, CO₂, cost and tonne-km with Pandas. The grid is synthetic, not real roads.

Run locally: `pip install -r requirements.txt` then `uvicorn api.index:app --reload`.

## Roadmap
Replace the synthetic grid with real road networks and validate against real GPS logs from a pilot zone.
