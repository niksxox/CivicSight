"""
CivicSight Recommendation Engine.

Synthesizes public facility condition, abandonment metrics, and demographic census
data to generate actionable recommendations: REPAIR, REPURPOSE, or NEWLY_DEVELOP.
"""

from __future__ import annotations

from typing import Any


def generate_recommendation(
    facility_type: str,
    facility_name: str,
    district: str,
    abandonment_score: float,
    population_catchment: int,
    distance_to_alternative_km: float = 2.0,
    has_structural_integrity: bool = True,
) -> dict[str, Any]:
    """
    Formulate a strategic recommendation based on infrastructure condition and demographic demand.
    """
    facility_type_lower = facility_type.lower()

    # Rule 1: High abandonment + sound structure in a school or warehouse -> REPURPOSE
    if abandonment_score >= 70 and has_structural_integrity and facility_type_lower in ["school", "government", "community"]:
        rec_type = "REPURPOSE"
        urgency = "HIGH"
        if facility_type_lower == "school":
            proposed_use = "Primary Health Sub-Center & Anganwadi Child Nutrition Hub"
            cost_estimate = "₹8.5 Lakhs"
            timeline_days = 45
            rationale = (
                f"{facility_name} exhibits high abandonment signals ({abandonment_score}% risk). "
                f"With a sturdy RCC structure and {population_catchment:,} residents in catchment, "
                "repurposing as a healthcare sub-center solves urgent local healthcare deficits."
            )
        else:
            proposed_use = "Community Digital IT & Micro-Enterprise Innovation Center"
            cost_estimate = "₹6.5 Lakhs"
            timeline_days = 30
            rationale = (
                f"{facility_name} is currently disused. Converting this civic asset into an "
                f"IT & micro-enterprise facility directly benefits {population_catchment:,} youth."
            )

    # Rule 2: Critical utility (water/sanitation) with high damage/abandonment -> REPAIR
    elif facility_type_lower in ["water", "toilet"] or (abandonment_score >= 50 and not has_structural_integrity):
        rec_type = "REPAIR"
        urgency = "CRITICAL" if abandonment_score >= 80 or population_catchment >= 8000 else "HIGH"
        cost_estimate = "₹2.5 Lakhs" if facility_type_lower == "water" else "₹1.8 Lakhs"
        timeline_days = 7 if urgency == "CRITICAL" else 14
        proposed_use = "Immediate electro-mechanical overhaul and community management transfer"
        rationale = (
            f"{facility_name} provides vital basic sanitation/water access to {population_catchment:,} residents. "
            f"Abandonment signals ({abandonment_score}%) stem from maintenance lapses; urgent repair restores service."
        )

    # Rule 3: High population density + distance to nearest facility > 3km -> NEWLY_DEVELOP
    elif distance_to_alternative_km >= 3.0 and population_catchment >= 10000:
        rec_type = "NEWLY_DEVELOP"
        urgency = "CRITICAL"
        proposed_use = f"Construct Modern 24x7 Public {facility_type.title()} Complex"
        cost_estimate = "₹18.0 Lakhs"
        timeline_days = 90
        rationale = (
            f"Catchment population of {population_catchment:,} faces an extreme infrastructure void "
            f"({distance_to_alternative_km} km to nearest alternative). New development is essential."
        )

    # Fallback / Default Maintenance
    else:
        rec_type = "REPAIR"
        urgency = "MEDIUM"
        proposed_use = "Scheduled municipal upkeep and preventive maintenance"
        cost_estimate = "₹75,000"
        timeline_days = 10
        rationale = f"Facility remains functional; routine servicing recommended to preserve service continuity."

    roi_score = round(min(9.9, 7.5 + (population_catchment / 5000.0) * 0.5), 1)

    return {
        "type": rec_type,
        "urgency": urgency,
        "target_facility_name": facility_name,
        "district": district,
        "affected_population": population_catchment,
        "estimated_cost": cost_estimate,
        "timeline_days": timeline_days,
        "roi_score": roi_score,
        "proposed_use": proposed_use,
        "rationale": rationale,
    }
