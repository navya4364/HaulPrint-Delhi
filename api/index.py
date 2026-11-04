"""HaulPrint Delhi backend: NetworkX route model + Pandas calculations, served by FastAPI.

The road network is a SYNTHETIC street grid (not real roads) so the prototype can
show the method. Replace build_zone_graph() with a real road network (for example
from OpenStreetMap) and real GPS data when available.
"""
import json
import math
import random

import networkx as nx
import pandas as pd

NAMES = ["Baseline", "Optimised Routes", "Decentralised + Hub"]

DEFAULTS = {
    "zone": "Vasant Kunj",
    "waste_t": 30.0,            # waste generated per day (tonnes)
    "mileage": 3.05,            # vehicle km per litre
    "diesel_price": 88.0,       # rupees per litre
    "other_cost_per_km": 2.3,   # rupees per km (driver, maintenance)
    "emission_factor": 2.69,    # kg CO2 per litre of diesel (assumed)
    "haul_km": 17.0,            # one-way distance to the processing site
    "local_share_pct": 30.0,    # share of waste processed near the source
    "truck_capacity_t": 10.0,   # tonnes per haul truck
    "fill_baseline": 0.60,      # average load factor, single-compartment trucks
    "fill_improved": 0.85,      # average load factor after consolidation
}


def clean_inputs(raw):
    """Merge user inputs with defaults and keep values in a safe range."""
    p = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        if key == "zone":
            p[key] = str(raw.get(key, default))
            continue
        try:
            p[key] = float(raw.get(key, default))
        except (TypeError, ValueError):
            p[key] = default
    p["mileage"] = max(p["mileage"], 0.1)
    p["truck_capacity_t"] = max(p["truck_capacity_t"], 0.1)
    p["local_share_pct"] = min(max(p["local_share_pct"], 0.0), 100.0)
    for k in ("fill_baseline", "fill_improved"):
        p[k] = min(max(p[k], 0.05), 1.0)
    for k in ("waste_t", "diesel_price", "other_cost_per_km", "emission_factor", "haul_km"):
        p[k] = max(p[k], 0.0)
    return p


def build_zone_graph(zone):
    """Synthetic 7x7 street grid (about 0.45 km blocks). Same zone name gives the same layout."""
    rng = random.Random(zone)
    G = nx.grid_2d_graph(7, 7)
    for u, v in G.edges:
        G[u][v]["weight"] = round(0.45 * rng.uniform(0.8, 1.3), 3)
    depot = (0, 0)                              # transfer station
    collection_points = [(2, 2), (2, 5), (5, 3)]  # neighbourhood collection points
    others = [n for n in G.nodes if n != depot and n not in collection_points]
    clusters = rng.sample(others, 12)           # household clusters
    return G, depot, collection_points, clusters


def shortest(G, a, b):
    return nx.shortest_path_length(G, a, b, weight="weight")


def tour_km(G, stops):
    """Length of a consolidated loop through all stops (Christofides approximation)."""
    if len(stops) < 2:
        return 0.0
    if len(stops) == 2:
        return 2 * shortest(G, stops[0], stops[1])
    path = nx.approximation.traveling_salesman_problem(
        G, nodes=stops, cycle=True, method=nx.approximation.christofides
    )
    return sum(G[u][v]["weight"] for u, v in zip(path, path[1:]))


def collection_distances(G, depot, cps, clusters, local_share_pct):
    """Local km per day inside the zone for each scenario."""
    # Baseline: every cluster has its own out-and-back trip to the nearest collection point,
    # and every collection point is emptied by a separate trip to the transfer station.
    baseline = sum(2 * min(shortest(G, c, cp) for cp in cps) for c in clusters)
    baseline += sum(2 * shortest(G, cp, depot) for cp in cps)
    # Optimised: the same stops served by one consolidated loop.
    optimised = tour_km(G, [depot] + clusters)
    # Decentralised: clusters with local processing are not collected for long haul.
    k = round(len(clusters) * local_share_pct / 100)
    decentralised = tour_km(G, [depot] + clusters[k:])
    return [baseline, optimised, decentralised]


def simulate(raw_inputs):
    """Run all three scenarios. Returns a list of dicts (one per scenario)."""
    p = clean_inputs(raw_inputs)
    G, depot, cps, clusters = build_zone_graph(p["zone"])
    local_km = collection_distances(G, depot, cps, clusters, p["local_share_pct"])

    hauled_share = [1.0, 1.0, 1.0 - p["local_share_pct"] / 100]
    df = pd.DataFrame({
        "scenario": NAMES,
        "collection_km": local_km,
        "hauled_t": [p["waste_t"] * s for s in hauled_share],
        "fill": [p["fill_baseline"], p["fill_improved"], p["fill_improved"]],
    })
    df["trips"] = (df["hauled_t"] / (p["truck_capacity_t"] * df["fill"])).apply(math.ceil)
    df["haul_total_km"] = df["trips"] * 2 * p["haul_km"]
    df["dist"] = (df["collection_km"] + df["haul_total_km"]).round().astype(int)
    df["fuel"] = (df["dist"] / p["mileage"]).round().astype(int)
    df["co2"] = (df["fuel"] * p["emission_factor"]).round().astype(int)
    cost = df["fuel"] * p["diesel_price"] + df["dist"] * p["other_cost_per_km"]
    df["cost"] = ((cost / 10).round() * 10).astype(int)
    df["tkm"] = (df["hauled_t"] * p["haul_km"]).round().astype(int)
    df["collection_km"] = df["collection_km"].round(1)
    df["hauled_t"] = df["hauled_t"].round(1)
    df["haul_total_km"] = df["haul_total_km"].round(1)
    return json.loads(df.to_json(orient="records"))


# ---------------------------------------------------------------- web API
# Vercel looks for a top-level FastAPI instance named "app" in this file.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HaulPrint Delhi API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "networkx+pandas"}


@app.post("/api/simulate")
def simulate_endpoint(body: dict):
    return {"mode": "network", "results": simulate(body)}
@app.get("/")
def root():
    return {"status": "ok", "app": "HaulPrint Delhi"}
