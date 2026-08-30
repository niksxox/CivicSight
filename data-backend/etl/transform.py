"""
TRANSFORM stage.

Where the actual "planned vs actual" logic from Section C of the spec
lives:
    planned_progress  = how far along the project SHOULD be today,
                         based on planned_start/planned_end (linear model)
    actual_progress    = latest reported/verified progress
    deviation          = actual_progress - planned_progress
"""
from datetime import date
import pandas as pd


def compute_planned_progress(planned_start: date, planned_end: date, as_of: date = None) -> float:
    """
    Linear planned-progress model: 0% at planned_start, 100% at
    planned_end. Clipped to [0, 100] so projects that haven't started
    yet or are already past their deadline don't produce nonsense
    values.
    """
    as_of = as_of or date.today()
    if planned_start is None or planned_end is None or planned_end <= planned_start:
        return None
    total_days = (planned_end - planned_start).days
    elapsed_days = (as_of - planned_start).days
    pct = (elapsed_days / total_days) * 100
    return max(0.0, min(100.0, round(pct, 2)))


def transform_projects(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    today = date.today()

    df["planned_progress"] = df.apply(
        lambda row: compute_planned_progress(row["planned_start"], row["planned_end"], today), axis=1
    )
    df["actual_progress"] = df["reported_progress"].fillna(0)

    df["progress_deviation"] = df["actual_progress"] - df["planned_progress"]

    # Auto-escalate status based on deviation, but never downgrade a
    # status a human/officer already set to COMPLETED/VERIFIED.
    def resolve_status(row):
        if row["status"] in ("COMPLETED", "VERIFIED"):
            return row["status"]
        if row["progress_deviation"] is not None and row["progress_deviation"] <= -25:
            return "STALLED"
        if row["progress_deviation"] is not None and row["progress_deviation"] <= -10:
            return "DELAYED"
        if row["status"] == "PLANNED" and today >= row["planned_start"]:
            return "IN_PROGRESS"
        return row["status"]

    df["current_status"] = df.apply(resolve_status, axis=1)

    # Simple priority score: bigger negative deviation + bigger budget
    # = higher priority for officer attention. Real scoring belongs to
    # Avinash's risk engine — this is just a sane placeholder so the
    # dashboard has *something* to sort by before that's wired in.
    def priority_score(row):
        dev = row["progress_deviation"] or 0
        budget = row.get("budget_allocated") or 0
        return round(max(0, -dev) * 2 + min(budget / 1_000_000, 50), 2)

    df["priority_score"] = df.apply(priority_score, axis=1)

    return df
