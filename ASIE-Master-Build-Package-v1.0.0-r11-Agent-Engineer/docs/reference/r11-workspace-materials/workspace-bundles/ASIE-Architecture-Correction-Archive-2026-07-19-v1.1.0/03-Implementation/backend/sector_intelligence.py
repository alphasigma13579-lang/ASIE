from __future__ import annotations

from typing import Any


COMMON_CRITERIA = [
    ("market_size", "حجم السوق"),
    ("capital_intensity", "كثافة رأس المال"),
    ("labor_dependency", "الاعتماد على العمالة"),
    ("location_sensitivity", "حساسية الموقع"),
    ("competition_intensity", "شدة المنافسة"),
    ("vision_2030_alignment", "التوافق مع رؤية 2030"),
]

TAXONOMY: list[dict[str, Any]] = [
    {
        "sector_id": "SEC-05",
        "sector_name": "Manufacturing",
        "arabic_name": "الصناعة والتصنيع",
        "subsectors": ["Heavy Manufacturing", "Light Manufacturing", "Food Manufacturing", "Pharmaceuticals"],
        "source_candidates": ["GASTAT_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "high",
            "labor_dependency": "medium",
            "location_sensitivity": "medium",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-07",
        "sector_name": "Real Estate",
        "arabic_name": "العقارات",
        "subsectors": ["Real Estate Development", "Commercial Real Estate", "Residential Real Estate", "Industrial Real Estate"],
        "source_candidates": ["GASTAT_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "high",
            "labor_dependency": "medium",
            "location_sensitivity": "high",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-08",
        "sector_name": "Logistics & Supply Chain",
        "arabic_name": "اللوجستيات وسلاسل الإمداد",
        "subsectors": ["Land Transport", "Warehousing", "E-commerce Logistics", "Ports & Airports"],
        "source_candidates": ["GASTAT_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "medium",
            "labor_dependency": "medium",
            "location_sensitivity": "high",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-09",
        "sector_name": "Tourism & Entertainment",
        "arabic_name": "السياحة والترفيه",
        "subsectors": ["Leisure Tourism", "Hotels & Hospitality", "Events & Festivals", "Cinema & Production"],
        "source_candidates": ["GASTAT_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "medium",
            "labor_dependency": "high",
            "location_sensitivity": "high",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-11",
        "sector_name": "Technology & Innovation",
        "arabic_name": "التقنية والابتكار",
        "subsectors": ["AI", "Cloud Computing", "Cybersecurity", "Software", "Data Centers"],
        "source_candidates": ["GASTAT_CANDIDATE", "SAMA_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "medium",
            "labor_dependency": "medium",
            "location_sensitivity": "medium",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-12",
        "sector_name": "Financial Services",
        "arabic_name": "القطاع المالي",
        "subsectors": ["Banks", "Insurance", "Financing", "Capital Markets", "Investment"],
        "source_candidates": ["SAMA_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "medium",
            "labor_dependency": "medium",
            "location_sensitivity": "medium",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-14",
        "sector_name": "Healthcare",
        "arabic_name": "الصحة والطب",
        "subsectors": ["Hospitals", "Clinics", "HealthTech", "Medical Devices", "Pharmaceuticals"],
        "source_candidates": ["GASTAT_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "high",
            "labor_dependency": "high",
            "location_sensitivity": "high",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
    {
        "sector_id": "SEC-17",
        "sector_name": "Agriculture & Food Security",
        "arabic_name": "الأغذية والزراعة والأمن الغذائي",
        "subsectors": ["Agriculture", "Food Security", "AgriTech", "Livestock", "Food Supply Chains"],
        "source_candidates": ["GASTAT_CANDIDATE", "MOF_CANDIDATE", "VISION_2030_REFERENCE"],
        "criteria_profile": {
            "market_size": "needs_evidence",
            "capital_intensity": "medium",
            "labor_dependency": "high",
            "location_sensitivity": "high",
            "competition_intensity": "needs_evidence",
            "vision_2030_alignment": "reference_only",
        },
    },
]


def sector_taxonomy() -> list[dict[str, Any]]:
    return [
        {
            "sector_id": row["sector_id"],
            "sector_name": row["sector_name"],
            "arabic_name": row["arabic_name"],
            "subsectors": row["subsectors"],
            "source_candidates": row["source_candidates"],
        }
        for row in TAXONOMY
    ]


def build_sector_intelligence(
    project: Any,
    evidence_register: dict[str, Any],
    source_records: list[dict[str, Any]],
) -> dict[str, Any]:
    inputs = project.inputs
    sector_id = str(inputs.get("primary_sector_id") or "").strip()
    taxonomy = taxonomy_by_id().get(sector_id)
    if taxonomy is None:
        taxonomy = infer_taxonomy_from_project(project)
    status = "ready" if sector_id and taxonomy else "needs_input"
    selected_subsector = str(inputs.get("subsector_id") or "").strip()
    if taxonomy and selected_subsector not in taxonomy["subsectors"]:
        selected_subsector = taxonomy["subsectors"][0]
    classification = {
        "primary_sector_id": taxonomy["sector_id"] if taxonomy else "",
        "primary_sector": taxonomy["sector_name"] if taxonomy else "",
        "primary_sector_ar": taxonomy["arabic_name"] if taxonomy else "",
        "subsector_id": selected_subsector,
        "activity_classification": str(inputs.get("activity_description") or project.sector or ""),
        "location_scope": str(inputs.get("location_scope") or project.jurisdiction or "Saudi Arabia"),
        "classification_status": status,
    }
    source_candidates = candidate_sources(taxonomy, source_records)
    evidence_map = build_sector_evidence_map(taxonomy, evidence_register, source_candidates)
    criteria = build_sector_criteria(taxonomy, evidence_map)
    signals = build_investment_signal_pack(project.inputs, taxonomy, criteria)
    return {
        "sector_intelligence_id": f"sector-intelligence:{classification['primary_sector_id'] or 'unclassified'}",
        "status": status,
        "taxonomy_record": classification,
        "sector_criteria": criteria,
        "investment_signal_pack": signals,
        "sector_evidence_map": evidence_map,
        "source_candidates": source_candidates,
        "external_fetch_enabled": False,
        "not_ready_reasons": [] if status == "ready" else ["missing_primary_sector_id"],
    }


def taxonomy_by_id() -> dict[str, dict[str, Any]]:
    return {row["sector_id"]: row for row in TAXONOMY}


def infer_taxonomy_from_project(project: Any) -> dict[str, Any] | None:
    text = f"{project.sector} {project.name}".lower()
    for row in TAXONOMY:
        tokens = [row["sector_name"].lower(), row["arabic_name"]]
        tokens.extend(str(item).lower() for item in row["subsectors"])
        if any(token and token in text for token in tokens):
            return row
    return None


def candidate_sources(taxonomy: dict[str, Any] | None, source_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = set((taxonomy or {}).get("source_candidates", ["GASTAT_CANDIDATE", "VISION_2030_REFERENCE"]))
    records = {row["source_id"]: row for row in source_records}
    return [
        {
            "source_id": source_id,
            "state": records.get(source_id, {}).get("state", "candidate"),
            "publisher": records.get(source_id, {}).get("publisher", source_id),
            "route": records.get(source_id, {}).get("route", "official_open_dataset"),
            "can_contribute_data_now": records.get(source_id, {}).get("state") == "enabled",
        }
        for source_id in sorted(wanted)
    ]


def build_sector_evidence_map(
    taxonomy: dict[str, Any] | None,
    evidence_register: dict[str, Any],
    source_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    gates = {row["dataset_id"]: row for row in evidence_register.get("quality_gates", [])}
    transformations = {row["transformation_id"]: row for row in evidence_register.get("transformations", [])}
    approved_links = [
        row
        for row in evidence_register.get("evidence_links", [])
        if row.get("human_review_decision") == "approved"
        and gates.get(row.get("dataset_id"), {}).get("can_use_for_assumptions")
        and (
            not row.get("transformation_id")
            or transformations.get(row.get("transformation_id"), {}).get("review_status") == "approved"
        )
    ]
    enabled_candidate_ids = {row["source_id"] for row in source_candidates if row["can_contribute_data_now"]}
    evidence_gaps = []
    criterion_links = []
    for criterion_id, label in COMMON_CRITERIA:
        criterion_approved_links = [
            row
            for row in approved_links
            if row.get("target_type") == "sector_criterion" and row.get("target_id") == criterion_id
        ]
        if criterion_approved_links and enabled_candidate_ids:
            status = "supported"
        elif criterion_id == "vision_2030_alignment":
            status = "reference_only"
        else:
            status = "needs_evidence"
            evidence_gaps.append(
                {
                    "criterion_id": criterion_id,
                    "label": label,
                    "reason": "no_approved_sector_dataset_link",
                    "required_action": "review exact open dataset/API, then link evidence to this criterion",
                }
            )
        criterion_links.append(
            {
                "criterion_id": criterion_id,
                "label": label,
                "evidence_status": status,
                "candidate_source_ids": [row["source_id"] for row in source_candidates],
                "evidence_refs": [row.get("evidence_ref", "") for row in criterion_approved_links] if status == "supported" else [],
            }
        )
    return {
        "sector_evidence_map_id": f"sector-evidence:{(taxonomy or {}).get('sector_id', 'unclassified')}",
        "criteria": criterion_links,
        "evidence_gaps": evidence_gaps,
        "approved_evidence_link_count": len(approved_links),
        "enabled_sector_source_count": len(enabled_candidate_ids),
    }


def build_sector_criteria(taxonomy: dict[str, Any] | None, evidence_map: dict[str, Any]) -> dict[str, Any]:
    profile = (taxonomy or {}).get("criteria_profile", {})
    evidence_status = {row["criterion_id"]: row["evidence_status"] for row in evidence_map["criteria"]}
    criteria = [
        {
            "criterion_id": criterion_id,
            "label": label,
            "sector_value": profile.get(criterion_id, "needs_evidence"),
            "evidence_status": evidence_status.get(criterion_id, "needs_evidence"),
        }
        for criterion_id, label in COMMON_CRITERIA
    ]
    return {
        "criteria_set_id": f"sector-criteria:{(taxonomy or {}).get('sector_id', 'unclassified')}",
        "status": "needs_evidence" if any(row["evidence_status"] == "needs_evidence" for row in criteria) else "supported",
        "criteria": criteria,
    }


def build_investment_signal_pack(
    inputs: dict[str, Any],
    taxonomy: dict[str, Any] | None,
    criteria_set: dict[str, Any],
) -> dict[str, Any]:
    capex_total = sum_float(inputs, ["capex_equipment", "capex_fitout", "capex_licenses_local"])
    payroll = safe_float(inputs.get("payroll_monthly"))
    rent = safe_float(inputs.get("rent_monthly"))
    capital_signal = "high_capital_intensity" if capex_total >= 200000 else "moderate_capital_intensity"
    labor_signal = "labor_sensitive" if payroll >= rent and payroll > 0 else "labor_not_primary_driver"
    return {
        "signal_pack_id": f"investment-signals:{(taxonomy or {}).get('sector_id', 'unclassified')}",
        "status": "needs_evidence" if criteria_set["status"] == "needs_evidence" else "ready",
        "signals": [
            {
                "signal_id": "capital_intensity_signal",
                "label": "Capital intensity",
                "value": capital_signal,
                "basis": "local_project_capex_inputs",
                "evidence_status": "needs_evidence",
            },
            {
                "signal_id": "labor_dependency_signal",
                "label": "Labor dependency",
                "value": labor_signal,
                "basis": "local_project_opex_inputs",
                "evidence_status": "needs_evidence",
            },
            {
                "signal_id": "sector_context_signal",
                "label": "Sector context",
                "value": (taxonomy or {}).get("sector_name", "unclassified"),
                "basis": "local_sector_taxonomy",
                "evidence_status": "reference_only" if taxonomy else "needs_evidence",
            },
        ],
    }


def sum_float(inputs: dict[str, Any], keys: list[str]) -> float:
    return sum(safe_float(inputs.get(key)) for key in keys)


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
