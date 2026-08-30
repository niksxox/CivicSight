"""
ORM models. These map 1:1 onto db/schema.sql — if you change a column
there, change it here too (or your queries will silently return stale
columns / throw on startup).
"""
import enum

from geoalchemy2 import Geography
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime, Boolean,
    ForeignKey, Enum, func, BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    DELAYED = "DELAYED"
    STALLED = "STALLED"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"


class EvidenceSource(str, enum.Enum):
    GOVERNMENT = "GOVERNMENT"
    CITIZEN = "CITIZEN"
    AI = "AI"
    OFFICER = "OFFICER"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    external_ref = Column(String, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text, nullable=False)
    department = Column(Text)
    district = Column(Text)
    state = Column(Text)

    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    geom_extent = Column(Geography(geometry_type="GEOMETRY", srid=4326))

    budget_allocated = Column(Numeric(16, 2))
    budget_spent = Column(Numeric(16, 2))

    planned_start = Column(Date)
    planned_end = Column(Date)
    planned_progress = Column(Numeric(5, 2), default=0)
    actual_progress = Column(Numeric(5, 2), default=0)

    current_status = Column(Enum(ProjectStatus, name="project_status"), default=ProjectStatus.PLANNED, nullable=False)
    priority_score = Column(Numeric(6, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    history = relationship("ProjectHistory", back_populates="project", cascade="all, delete-orphan")
    evidence = relationship("CitizenEvidence", back_populates="project", cascade="all, delete-orphan")

    @property
    def progress_deviation(self):
        """Actual Progress - Planned Progress. Negative = behind schedule."""
        if self.actual_progress is None or self.planned_progress is None:
            return None
        return float(self.actual_progress) - float(self.planned_progress)


class ProjectHistory(Base):
    __tablename__ = "project_history"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ProjectStatus, name="project_status"))
    progress = Column(Numeric(5, 2))
    note = Column(Text)
    source = Column(Enum(EvidenceSource, name="evidence_source"), default=EvidenceSource.GOVERNMENT, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="history")


class CitizenEvidence(Base):
    __tablename__ = "citizen_evidence"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    description = Column(Text)
    photo_url = Column(Text)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    location_verified = Column(Boolean, default=False)

    ai_condition = Column(Text)
    ai_issue = Column(Text)
    ai_confidence = Column(Numeric(4, 3))
    needs_human_review = Column(Boolean, default=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="evidence")


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # school | hospital | transport | water | government
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    district = Column(Text)
    source_ref = Column(Text)
    geo_precision = Column(Text)


class DistrictPopulation(Base):
    __tablename__ = "district_population"

    id = Column(Integer, primary_key=True)
    district = Column(Text, nullable=False, unique=True)
    state = Column(Text)
    population = Column(BigInteger)
    boundary = Column(Geography(geometry_type="MULTIPOLYGON", srid=4326))
    area_sq_km = Column(Numeric(10, 2))


class InfrastructureNetwork(Base):
    __tablename__ = "infrastructure_network"

    id = Column(Integer, primary_key=True)
    source_ref = Column(Text)
    name = Column(Text)
    type = Column(Text)  # road | rail | water_line | power_line
    geom = Column(Geography(geometry_type="LINESTRING", srid=4326), nullable=False)
    district = Column(Text)
    length_km = Column(Numeric(12, 3))
    status = Column(Text)
    geo_precision = Column(Text)
    source_metadata = Column(JSONB)


class InfrastructureCoverage(Base):
    __tablename__ = "infrastructure_coverage"

    id = Column(Integer, primary_key=True)
    source = Column(Text, nullable=False)
    area_level = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    district = Column(Text)
    district_key = Column(Text, nullable=False)
    metric_name = Column(Text, nullable=False)
    metric_value = Column(Numeric(16, 3))
    secondary_metric_name = Column(Text)
    secondary_metric_value = Column(Numeric(16, 3))
    total_households_lakh = Column(Numeric(16, 3))
    geo_precision = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class LgdVillage(Base):
    __tablename__ = "lgd_villages"

    village_code = Column(Text, primary_key=True)
    village_name = Column(Text, nullable=False)
    state = Column(Text)
    district = Column(Text)
    block = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True)
    school_id = Column(Text, unique=True, nullable=False)
    school_name = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    district = Column(Text, nullable=False)
    block = Column(Text)
    village = Column(Text)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    school_category = Column(Text)
    management = Column(Text)
    student_count = Column(Integer)
    teacher_count = Column(Integer)
    classroom_count = Column(Integer)
    has_electricity = Column(Boolean)
    has_drinking_water = Column(Boolean)
    has_toilet = Column(Boolean)
    has_girls_toilet = Column(Boolean)
    has_ramp = Column(Boolean)
    has_computer = Column(Boolean)
    has_internet = Column(Boolean)
    has_library = Column(Boolean)
    has_playground = Column(Boolean)
