"""
Convenience entrypoint: python scripts/run_etl.py
(same as `python -m etl.pipeline`, kept here so it's obvious where to
look for "how do I load the data").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.pipeline import run_full_pipeline

if __name__ == "__main__":
    run_full_pipeline()
