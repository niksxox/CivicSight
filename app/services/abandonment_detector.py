"""
CivicSight Abandonment & Underutilization Detection Service.

Combines citizen ground evidence (text keywords, image markers) with
government maintenance records to determine whether a public facility is
underutilized, defunct, or abandoned.
"""

from __future__ import annotations

import re
from typing import Any


ABANDONMENT_KEYWORDS = {
    "abandoned": 30,
    "locked": 25,
    "padlock": 25,
    "defunct": 25,
    "closed": 20,
    "not functioning": 25,
    "not worked": 25,
    "dry tap": 25,
    "weeds": 15,
    "overgrown": 20,
    "vegetation": 15,
    "broken window": 15,
    "cracked": 10,
    "rust": 15,
    "rusted": 15,
    "dumping ground": 20,
    "no student": 25,
    "zero enrollment": 30,
    "no doctor": 20,
    "waste": 10,
}


def detect_abandonment(
    text: str,
    months_since_inspection: float = 0.0,
    citizen_report_count: int = 1,
    visual_tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Compute abandonment score and classification.
    """
    text_lower = text.lower()
    score = 0.0
    detected_signals: list[str] = []

    for kw, weight in ABANDONMENT_KEYWORDS.items():
        if kw in text_lower:
            score += weight
            detected_signals.append(f"Text keyword '{kw}' detected")

    # Factor in maintenance inspection lapse
    if months_since_inspection > 24:
        score += 30
        detected_signals.append(f"Inspection lapse: {months_since_inspection:.0f} months without official audit")
    elif months_since_inspection > 12:
        score += 15
        detected_signals.append(f"Inspection lapse: {months_since_inspection:.0f} months without official audit")
    elif months_since_inspection > 6:
        score += 8

    # Factor in citizen report concentration
    if citizen_report_count >= 10:
        score += 25
        detected_signals.append(f"High citizen complaint volume: {citizen_report_count} reports")
    elif citizen_report_count >= 5:
        score += 15
        detected_signals.append(f"Elevated citizen complaints: {citizen_report_count} reports")
    elif citizen_report_count >= 2:
        score += 8

    # Factor in visual tags from image analyzer
    if visual_tags:
        for tag in visual_tags:
            tag_upper = tag.upper()
            if any(k in tag_upper for k in ["LOCK", "PADLOCK", "CHAIN"]):
                score += 20
                detected_signals.append("Visual evidence: padlocked / chained entrance")
            elif any(k in tag_upper for k in ["WEED", "VEGETATION", "OVERGROWTH"]):
                score += 15
                detected_signals.append("Visual evidence: extensive vegetation overgrowth")
            elif any(k in tag_upper for k in ["RUST", "CORROSION"]):
                score += 10
                detected_signals.append("Visual evidence: structural corrosion")
            elif any(k in tag_upper for k in ["DRY", "LEAK", "SEVERED"]):
                score += 15
                detected_signals.append("Visual evidence: non-functional utility connection")

    # Normalize score 0 - 100
    final_score = min(100.0, max(0.0, score))

    if final_score >= 80:
        status = "ABANDONED" if "school" in text_lower or "building" in text_lower else "DEFUNCT"
    elif final_score >= 50:
        status = "UNDERUTILIZED"
    else:
        status = "OPERATIONAL"

    return {
        "abandonment_score": round(final_score, 1),
        "status": status,
        "confidence": min(98.0, 75.0 + len(detected_signals) * 4.0),
        "signals": detected_signals,
    }
