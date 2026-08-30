"""
Pydantic schemas — what actually goes out over the wire.

Kept separate from app/models.py on purpose: ORM models describe the
database, these describe the API contract. They will drift from each
other over time and that's fine (e.g. we never expose raw PostGIS
geography objects here, only lat/lng floats).
"""
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: Optional[str] = None
    name: str
    category: str
    department: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None

    latitude: float
    longitude: float

    budget_allocated: Optional[float] = None
    budget_spent: Optional[float] = None

    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    planned_progress: Optional[float] = None
    actual_progress: Optional[float] = None
    progress_deviation: Optional[float] = None

    current_status: str
    priority_score: Optional[float] = None

    updated_at: datetime


class ProjectListOut(BaseModel):
    total: int
    items: List[ProjectOut]


class NearbyFacilityOut(BaseModel):
    id: int
    name: str
    type: str
    distance_meters: float


class NearbyOut(BaseModel):
    project_id: int
    radius_meters: int
    estimated_nearby_population: Optional[int] = None
    facilities: List[NearbyFacilityOut]
    connectivity_notes: List[str]


class HistoryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Optional[str] = None
    progress: Optional[float] = None
    note: Optional[str] = None
    source: str
    recorded_at: datetime


class AnalyticsOut(BaseModel):
    project_id: int
    planned_progress: Optional[float]
    actual_progress: Optional[float]
    progress_deviation: Optional[float]
    days_elapsed: Optional[int]
    days_remaining: Optional[int]
    schedule_health: str          # "on_track" | "behind" | "ahead" | "unknown"
    citizen_reports_count: int
    open_flags_needing_review: int


class DistrictAnalyticsOut(BaseModel):
    district: str
    total_projects: int
    avg_deviation: Optional[float]
    delayed_count: int
    completed_count: int
    verified_count: int
    total_budget_allocated: Optional[float]


class MapPointOut(BaseModel):
    id: int
    name: str
    category: str
    latitude: float
    longitude: float
    current_status: str
    progress_deviation: Optional[float] = None
