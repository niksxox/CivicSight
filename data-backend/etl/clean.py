"""
CLEAN stage.

Takes VALIDATED rows (structurally sound) and normalizes them:
consistent casing, real dtypes instead of strings, trimmed whitespace,
safe defaults for optional fields. No business logic here — that's
transform.py.
"""
import pandas as pd

STATUS_ALIASES = {
    "planned": "PLANNED", "not started": "PLANNED",
    "in progress": "IN_PROGRESS", "ongoing": "IN_PROGRESS", "in-progress": "IN_PROGRESS",
    "delayed": "DELAYED", "behind schedule": "DELAYED",
    "stalled": "STALLED", "stopped": "STALLED", "halted": "STALLED",
    "completed": "COMPLETED", "done": "COMPLETED", "finished": "COMPLETED",
    "verified": "VERIFIED",
}


def clean_projects(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Strings: trim + collapse whitespace
    text_cols = ["name", "category", "department", "district", "state", "external_ref"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"nan": None, "": None})

    df["category"] = df["category"].str.lower()

    # Numerics
    for col in ["latitude", "longitude", "budget_allocated", "budget_spent", "reported_progress"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["reported_progress"] = df.get("reported_progress", pd.Series(dtype=float)).clip(0, 100)

    # Dates
    df["planned_start"] = pd.to_datetime(df["planned_start"], errors="coerce").dt.date
    df["planned_end"] = pd.to_datetime(df["planned_end"], errors="coerce").dt.date

    # Status normalization -> our enum values
    if "status" in df.columns:
        df["status"] = (
            df["status"].astype(str).str.strip().str.lower().map(STATUS_ALIASES).fillna("PLANNED")
        )
    else:
        df["status"] = "PLANNED"

    return df
