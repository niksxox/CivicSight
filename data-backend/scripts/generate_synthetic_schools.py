#!/usr/bin/env python
import argparse
import random
from pathlib import Path

import pandas as pd
from faker import Faker

DISTRICT_BOUNDS = {
    "Vijayawada": (80.5280, 16.3862, 80.7680, 16.6262),
    "Guntur": (80.3165, 16.1867, 80.5565, 16.4267),
    "Visakhapatnam": (83.0985, 17.5668, 83.3385, 17.8068),
    "Tirupati": (79.2992, 13.5088, 79.5392, 13.7488),
    "Kurnool": (77.9173, 15.7081, 78.1573, 15.9481),
}
BLOCKS = {
    "Vijayawada": ["Vijayawada Urban", "Vijayawada Rural", "Penamaluru", "Ibrahimpatnam"],
    "Guntur": ["Guntur Urban", "Guntur Rural", "Mangalagiri", "Tenali"],
    "Visakhapatnam": ["Visakhapatnam Urban", "Bheemunipatnam", "Anakapalle", "Pendurthi"],
    "Tirupati": ["Tirupati Urban", "Tirupati Rural", "Chandragiri", "Renigunta"],
    "Kurnool": ["Kurnool Urban", "Kurnool Rural", "Dhone", "Adoni"],
}


def generate_schools(size=1000, seed=42):
    fake = Faker("en_IN")
    random.seed(seed)
    Faker.seed(seed)
    rows = []
    for i in range(size):
        district = random.choice(list(DISTRICT_BOUNDS))
        min_lng, min_lat, max_lng, max_lat = DISTRICT_BOUNDS[district]
        block = random.choice(BLOCKS[district])
        management = random.choice(["Government", "Government Aided", "Private"])
        category = random.choice(["Primary", "Upper Primary", "Secondary", "Higher Secondary"])
        rural = "Urban" not in block
        students = random.randint(15, 850)
        teachers = max(1, int(students / random.uniform(18, 38)))
        classrooms = max(1, int(students / random.uniform(25, 45)))
        has_electricity = random.random() < (0.70 if rural and management != "Private" else 0.94)
        has_toilet = random.random() < (0.62 if rural and management == "Government" else 0.93)
        has_computer = has_electricity and random.random() < (0.30 if rural and management == "Government" else 0.75)
        village = f"{fake.first_name()}{random.choice(['puram', 'palli', 'gudem', 'ur'])}"
        rows.append({
            "school_id": f"28{i + 1:09d}",
            "school_name": f"{fake.last_name()} {category} School, {village}",
            "state": "Andhra Pradesh",
            "district": district,
            "block": block,
            "village": village,
            "latitude": round(random.uniform(min_lat, max_lat), 6),
            "longitude": round(random.uniform(min_lng, max_lng), 6),
            "school_category": category,
            "management": management,
            "student_count": students,
            "teacher_count": teachers,
            "classroom_count": classrooms,
            "has_electricity": has_electricity,
            "has_drinking_water": random.random() < 0.82,
            "has_toilet": has_toilet,
            "has_girls_toilet": has_toilet and random.random() < 0.82,
            "has_ramp": random.random() < 0.65,
            "has_computer": has_computer,
            "has_internet": has_computer and random.random() < 0.60,
            "has_library": random.random() < 0.62,
            "has_playground": random.random() < 0.72,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic/representative school infrastructure data.")
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = Path(__file__).resolve().parent.parent / "data" / "raw" / "schools.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_schools(args.size, args.seed).to_csv(out, index=False)
    print(f"Synthetic school data written to {out} (rows={args.size}, seed={args.seed})")


if __name__ == "__main__":
    main()
