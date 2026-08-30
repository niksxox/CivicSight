"""
CivicSight AI Infrastructure Intelligence
------------------------------------------

Shared application constants.

This module contains:
- Infrastructure categories
- Issue categories
- Condition levels
- Severity levels
- Priority levels
- Project statuses
- Verification statuses
- Score boundaries
- Confidence boundaries
- Progress boundaries
- Image/video processing defaults

Business logic belongs in the service modules.
This file only defines shared constants and enums.
"""

from __future__ import annotations

from enum import Enum


# ============================================================
# Infrastructure Types
# ============================================================


class InfrastructureType(str, Enum):
    """Supported infrastructure categories."""

    ROAD = "Road"

    BRIDGE = "Bridge"

    DRAINAGE = "Drainage"

    STREETLIGHT = "Streetlight"

    WATER_FACILITY = "Water Facility"

    PUBLIC_BUILDING = "Public Building"

    ROAD_FACILITY = "Road Facility"

    OTHER = "Other"


# ============================================================
# Issue Types
# ============================================================


class IssueType(str, Enum):
    """Supported infrastructure issue categories."""

    POTHOLE = "Pothole"

    CRACK = "Crack"

    ROAD_DAMAGE = "Road Damage"

    BROKEN_STREETLIGHT = "Broken Streetlight"

    DAMAGED_DRAINAGE = "Damaged Drainage"

    GARBAGE_ACCUMULATION = "Garbage Accumulation"

    DAMAGED_STRUCTURE = "Damaged Structure"

    INCOMPLETE_WORK = "Incomplete Work"

    ABANDONED_INFRASTRUCTURE = (
        "Abandoned Infrastructure"
    )

    CONSTRUCTION_PROGRESS = (
        "Construction Progress"
    )

    VISIBLE_DETERIORATION = (
        "Visible Deterioration"
    )

    OTHER = "Other"


# ============================================================
# Condition Levels
# ============================================================


class ConditionLevel(str, Enum):
    """Observed infrastructure condition."""

    GOOD = "Good"

    FAIR = "Fair"

    POOR = "Poor"

    CRITICAL = "Critical"

    UNKNOWN = "Unknown"


# ============================================================
# Severity Levels
# ============================================================


class SeverityLevel(str, Enum):
    """Severity classification for an infrastructure issue."""

    LOW = "Low"

    MEDIUM = "Medium"

    HIGH = "High"


# ============================================================
# Priority Levels
# ============================================================


class PriorityLevel(str, Enum):
    """Priority classification for an infrastructure issue."""

    LOW = "Low"

    MEDIUM = "Medium"

    HIGH = "High"

    CRITICAL = "Critical"


# ============================================================
# Project Status
# ============================================================


class ProjectStatus(str, Enum):
    """Infrastructure project progress/status."""

    ON_TRACK = "on_track"

    DELAYED = "delayed"

    AHEAD = "ahead"

    COMPLETED = "completed"

    NOT_STARTED = "not_started"

    HALTED = "halted"

    UNKNOWN = "unknown"


# ============================================================
# Verification Status
# ============================================================


class VerificationStatus(str, Enum):
    """Resolution/progress verification result."""

    COMPLETION_APPEARS_GENUINE = (
        "completion_appears_genuine"
    )

    IMPROVEMENT_DETECTED = (
        "improvement_detected"
    )

    NO_IMPROVEMENT_DETECTED = (
        "no_improvement_detected"
    )

    UNCERTAIN = "uncertain"

    VERIFICATION_FAILED = (
        "verification_failed"
    )


# ============================================================
# Generic Score Boundaries
# ============================================================


MIN_SCORE = 0.0

MAX_SCORE = 100.0


# ============================================================
# Confidence Boundaries
# ============================================================


MIN_CONFIDENCE = 0.0

MAX_CONFIDENCE = 1.0


# ============================================================
# Percentage Boundaries
# ============================================================


MIN_PERCENTAGE = 0.0

MAX_PERCENTAGE = 100.0


# ============================================================
# Priority Score Boundaries
# ============================================================


PRIORITY_LOW_MAX = 24.99

PRIORITY_MEDIUM_MAX = 49.99

PRIORITY_HIGH_MAX = 74.99

PRIORITY_CRITICAL_MIN = 75.0


# ============================================================
# Severity Score Boundaries
# ============================================================


SEVERITY_LOW_MAX = 33.33

SEVERITY_MEDIUM_MAX = 66.66

SEVERITY_HIGH_MIN = 66.67


# ============================================================
# Progress Deviation Boundaries
# ============================================================


# Difference between actual and planned progress.
#
# Example:
#
# planned = 80
# actual = 58
#
# deviation = -22


PROGRESS_ON_TRACK_MIN_DEVIATION = -5.0

PROGRESS_ON_TRACK_MAX_DEVIATION = 5.0

PROGRESS_AHEAD_THRESHOLD = 5.0

PROGRESS_DELAYED_THRESHOLD = -5.0


# ============================================================
# Video Processing Defaults
# ============================================================


DEFAULT_VIDEO_FRAME_SAMPLE_COUNT = 10

MIN_VIDEO_FRAME_SAMPLE_COUNT = 1


# ============================================================
# Image Processing Defaults
# ============================================================


SUPPORTED_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
)


# MIME types accepted by the image API.
SUPPORTED_IMAGE_CONTENT_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
)


# ============================================================
# Video File Extensions
# ============================================================


SUPPORTED_VIDEO_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
)


# ============================================================
# Video MIME Types
# ============================================================


SUPPORTED_VIDEO_CONTENT_TYPES = (
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
)


# ============================================================
# File Size Defaults
# ============================================================


MAX_IMAGE_SIZE_BYTES = (
    10 * 1024 * 1024
)

MAX_VIDEO_SIZE_BYTES = (
    100 * 1024 * 1024
)