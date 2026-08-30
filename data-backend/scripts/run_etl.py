"""Demo-safe ETL entrypoint."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.pipeline import run_full_pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CivSight ETL pipelines.")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=["projects", "facilities", "population", "district_population", "network", "schools", "roads", "water", "jjm", "villages", "lgd"],
        help="Run one dataset. May be passed multiple times. Omit to run the full demo refresh.",
    )
    parser.add_argument("--chunk-size", type=int, default=50000, help="Chunk size for LGD village CSV loading.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate the target tables for the selected datasets before loading (clean demo refresh). "
             "Keyed tables (coverage, villages) are upsert-idempotent and always safe to re-run.",
    )
    args = parser.parse_args()
    run_full_pipeline(args.dataset, chunk_size=args.chunk_size, reset=args.reset)
