"""
VALIDATE stage.

Checks structure and plausibility BEFORE we spend effort cleaning or
transforming. Returns (valid_rows, rejected_rows_with_reason) so bad
government-data rows get logged and skipped instead of silently
corrupting the unified database.
"""
from typing import List, Tuple
import pandas as pd

REQUIRED_PROJECT_COLUMNS = [
    "name", "category", "latitude", "longitude",
    "planned_start", "planned_end",
]


def _coerce_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def validate_projects(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (valid_df, rejected_df). rejected_df has an extra
    'rejection_reason' column so it can be dumped to
    data/processed/rejected_projects.csv for someone to look at.
    """
    df = df.copy()
    reasons: List[List[str]] = [[] for _ in range(len(df))]

    # 1. required columns present at all
    missing_cols = [c for c in REQUIRED_PROJECT_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Source is missing required columns entirely: {missing_cols}")

    # 2. required fields non-null
    for col in REQUIRED_PROJECT_COLUMNS:
        for i, val in enumerate(df[col]):
            if pd.isna(val) or str(val).strip() == "":
                reasons[i].append(f"missing {col}")

    # 3. lat/lng plausible for India (rough bounding box, catches obvious
    #    swapped-columns or bad-geocoding errors early)
    lat = _coerce_float(df["latitude"])
    lng = _coerce_float(df["longitude"])
    for i in range(len(df)):
        if pd.isna(lat.iloc[i]) or pd.isna(lng.iloc[i]):
            reasons[i].append("non-numeric lat/lng")
        elif not (6.0 <= lat.iloc[i] <= 37.5 and 68.0 <= lng.iloc[i] <= 97.5):
            reasons[i].append("lat/lng outside India bounding box")

    # 4. planned_end should not be before planned_start
    start = pd.to_datetime(df["planned_start"], errors="coerce")
    end = pd.to_datetime(df["planned_end"], errors="coerce")
    for i in range(len(df)):
        if pd.isna(start.iloc[i]) or pd.isna(end.iloc[i]):
            reasons[i].append("unparseable planned_start/planned_end")
        elif end.iloc[i] < start.iloc[i]:
            reasons[i].append("planned_end before planned_start")

    df["_rejection_reasons"] = [r for r in reasons]
    is_valid = df["_rejection_reasons"].apply(len).eq(0)

    valid_df = df[is_valid].drop(columns=["_rejection_reasons"]).reset_index(drop=True)
    rejected_df = df[~is_valid].copy()
    rejected_df["rejection_reason"] = rejected_df["_rejection_reasons"].apply(lambda r: "; ".join(r))
    rejected_df = rejected_df.drop(columns=["_rejection_reasons"]).reset_index(drop=True)

    return valid_df, rejected_df
