"""
Generates realistic-shaped sample CSVs into data/raw/ so the whole
ETL pipeline + API can be demoed end-to-end without real government
data on hand. Swap these files for real extracts later — the ETL
code doesn't change, only what's in data/raw/.

Run: python scripts/generate_sample_data.py
"""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("en_IN")
random.seed(42)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Rough district centers around Andhra Pradesh, used just to scatter
# demo points realistically — swap for your actual region.
DISTRICTS = {
    "Vijayawada":  (16.5062, 80.6480),
    "Guntur":      (16.3067, 80.4365),
    "Visakhapatnam": (17.6868, 83.2185),
    "Tirupati":    (13.6288, 79.4192),
    "Kurnool":     (15.8281, 78.0373),
}

CATEGORIES = ["road", "school", "hospital", "water", "government_building", "bridge"]
DEPARTMENTS = ["PWD", "Rural Development", "Health Dept", "Water Resources", "Urban Development"]


def jitter(lat, lng, spread=0.06):
    return lat + random.uniform(-spread, spread), lng + random.uniform(-spread, spread)


def gen_projects(n=60):
    rows = []
    for i in range(n):
        district = random.choice(list(DISTRICTS.keys()))
        base_lat, base_lng = DISTRICTS[district]
        lat, lng = jitter(base_lat, base_lng)

        start = date.today() - timedelta(days=random.randint(30, 500))
        duration = random.randint(90, 600)
        end = start + timedelta(days=duration)

        # Simulate real-world spread: some on track, some badly behind
        elapsed_ratio = min(1.0, max(0.0, (date.today() - start).days / duration))
        noise = random.uniform(-35, 10)
        reported_progress = max(0, min(100, round(elapsed_ratio * 100 + noise, 1)))

        category = random.choice(CATEGORIES)
        budget = random.randint(2_000_000, 150_000_000)

        rows.append({
            "external_ref": f"PRJ-{1000 + i}",
            "name": f"{category.replace('_', ' ').title()} project — {fake.street_name()}, {district}",
            "description": fake.sentence(nb_words=10),
            "category": category,
            "department": random.choice(DEPARTMENTS),
            "district": district,
            "state": "Andhra Pradesh",
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "budget_allocated": budget,
            "budget_spent": round(budget * random.uniform(0.1, 0.95)),
            "planned_start": start.isoformat(),
            "planned_end": end.isoformat(),
            "reported_progress": reported_progress,
            "status": random.choice(["planned", "in progress", "in progress", "delayed", "completed"]),
        })
    return pd.DataFrame(rows)


def gen_facilities(n=40):
    rows = []
    types = ["school", "hospital", "transport", "water", "government"]
    for i in range(n):
        district = random.choice(list(DISTRICTS.keys()))
        base_lat, base_lng = DISTRICTS[district]
        lat, lng = jitter(base_lat, base_lng, spread=0.05)
        ftype = random.choice(types)
        rows.append({
            "name": f"{fake.company()} {ftype.title()}",
            "type": ftype,
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "district": district,
        })
    return pd.DataFrame(rows)


def gen_district_population():
    rows = []
    for district, (lat, lng) in DISTRICTS.items():
        # crude ~0.12deg square "boundary" around the center — good enough for a demo
        d = 0.12
        poly_wkt = (
            f"POLYGON(({lng-d} {lat-d}, {lng+d} {lat-d}, {lng+d} {lat+d}, "
            f"{lng-d} {lat+d}, {lng-d} {lat-d}))"
        )
        rows.append({
            "district": district,
            "state": "Andhra Pradesh",
            "population": random.randint(900_000, 2_200_000),
            "area_sq_km": round((2 * d * 111) ** 2, 1),  # rough deg->km conversion
            "boundary_wkt": poly_wkt,
        })
    return pd.DataFrame(rows)


def gen_network(n=15):
    rows = []
    for i in range(n):
        district = random.choice(list(DISTRICTS.keys()))
        base_lat, base_lng = DISTRICTS[district]
        lat1, lng1 = jitter(base_lat, base_lng, spread=0.05)
        lat2, lng2 = jitter(base_lat, base_lng, spread=0.05)
        rows.append({
            "name": f"{fake.street_name()} Road",
            "type": "road",
            "district": district,
            "geom_wkt": f"LINESTRING({lng1} {lat1}, {lng2} {lat2})",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    gen_projects().to_csv(RAW_DIR / "projects.csv", index=False)
    gen_facilities().to_csv(RAW_DIR / "facilities.csv", index=False)
    gen_district_population().to_csv(RAW_DIR / "district_population.csv", index=False)
    gen_network().to_csv(RAW_DIR / "network.csv", index=False)
    print(f"Sample data written to {RAW_DIR}")
