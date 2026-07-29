from __future__ import annotations

from typing import Any, Mapping

FREEZE_SCHEMA = "asie.release.freeze.v1"
CONTROLLED_UNFREEZE_SCHEMA = "asie.controlled.unfreeze.v1"
CONTROLLED_UNFREEZE_PACKAGE = "GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION"
BASELINE_COMMIT = "8978231e190b8ccc2be59ec46acf50d6268cd41f"
ELIGIBILITY_REVIEW_COMMIT = "b459944ba211be32408dd642390122b24d8113ae"
ELIGIBILITY_GATE_RUN_ID = "30451627726"
ELIGIBILITY_REVIEW_RUN_ID = "30451627730"
ELIGIBILITY_REVIEW_ARTIFACT_SHA256 = (
    "134b77dc0d6135aba3eba02eac4c708960ef850e341bdd502067800fb9b5262a"
)

EXPECTED_SCOPE = {
    "public_beta",
    "production_deployment",
    "external_network_exposure",
}
EXPECTED_REASON_CODES = {
    "production_bootstrap_takeover",
    "zero_user_implicit_principal",
    "dib_cross_tenant_access",
    "forged_manifest_gate_finance_execution",
    "dib_thread_unsafe_sqlite",
    "release_gate_without_runtime_evidence",
}
EXPECTED_PROTECTED_BOUNDARIES = {
    "AAS Runtime Freeze v1.0",
    "Finance calculations",
    "Snapshot Assembly",
    "Decision Council",
}
EXPECTED_UNFREEZE_REQUIREMENTS = {
    "SEC-BETA-01 closed with exploit tests",
    "STAB-BETA-02 closed with concurrent HTTP tests",
    "SEC-BETA-03 closed with cross-tenant denial tests",
    "GOV-BETA-04 closed with forged lineage denial tests",
    "ARCH-BETA-05 closed with canonical ProjectRunWorkflow evidence",
    "REL-BETA-07 evidence-backed gate on the release commit",
}


def controlled_unfreeze_record() -> dict[str, Any]:
    return {
        "schema": CONTROLLED_UNFREEZE_SCHEMA,
        "package_id": CONTROLLED_UNFREEZE_PACKAGE,
        "cleared_on": "2026-07-29",
        "eligibility_review_commit": ELIGIBILITY_REVIEW_COMMIT,
        "eligibility_gate_run_id": ELIGIBILITY_GATE_RUN_ID,
        "eligibility_review_run_id": ELIGIBILITY_REVIEW_RUN_ID,
        "eligibility_review_artifact_sha256": ELIGIBILITY_REVIEW_ARTIFACT_SHA256,
        "public_release_authorized": False,
        "external_network_authorized": False,
        "provider_activation_authorized": False,
    }


def _unique_string_set(value: Any) -> tuple[set[str], bool]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return set(), False
    material = set(value)
    return material, len(material) == len(value)


def validate_controlled_unfreeze_marker(marker: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    exact_scalars = {
        "schema": FREEZE_SCHEMA,
        "status": "CLEARED",
        "decision": "PENDING_GATE",
        "baseline_commit": BASELINE_COMMIT,
        "activated_on": "2026-07-29",
        "release_gate_allowed": True,
    }
    for key, expected in exact_scalars.items():
        if marker.get(key) != expected:
            failures.append(f"invalid_{key}")

    for key, expected in (
        ("scope", EXPECTED_SCOPE),
        ("reason_codes", EXPECTED_REASON_CODES),
        ("protected_boundaries", EXPECTED_PROTECTED_BOUNDARIES),
        ("unfreeze_requires", EXPECTED_UNFREEZE_REQUIREMENTS),
    ):
        actual, unique = _unique_string_set(marker.get(key))
        if not unique or actual != expected:
            failures.append(f"invalid_{key}")

    transition = marker.get("controlled_unfreeze")
    expected_transition = controlled_unfreeze_record()
    if not isinstance(transition, Mapping):
        failures.append("controlled_unfreeze_missing")
    else:
        for key, expected in expected_transition.items():
            if transition.get(key) != expected:
                failures.append(f"invalid_controlled_unfreeze_{key}")
        unexpected = sorted(set(transition) - set(expected_transition))
        if unexpected:
            failures.append("unexpected_controlled_unfreeze_fields")

    return {
        "valid": not failures,
        "failures": failures,
        "status": marker.get("status"),
        "baseline_commit": marker.get("baseline_commit"),
        "eligibility_review_commit": (
            transition.get("eligibility_review_commit")
            if isinstance(transition, Mapping)
            else None
        ),
        "public_release_authorized": (
            transition.get("public_release_authorized")
            if isinstance(transition, Mapping)
            else None
        ),
        "external_network_authorized": (
            transition.get("external_network_authorized")
            if isinstance(transition, Mapping)
            else None
        ),
        "provider_activation_authorized": (
            transition.get("provider_activation_authorized")
            if isinstance(transition, Mapping)
            else None
        ),
    }


def evaluate_release_freeze_marker(marker: Mapping[str, Any]) -> dict[str, Any]:
    if marker.get("schema") != FREEZE_SCHEMA:
        return {
            "allowed": False,
            "decision": "NO_GO",
            "reason": "emergency_release_freeze_schema_invalid",
            "validation_failures": ["invalid_schema"],
        }

    if marker.get("status") != "CLEARED":
        return {
            "allowed": False,
            "decision": "NO_GO",
            "reason": "emergency_release_freeze_active",
            "baseline_commit": marker.get("baseline_commit"),
            "reason_codes": marker.get("reason_codes", []),
            "validation_failures": [],
        }

    validation = validate_controlled_unfreeze_marker(marker)
    allowed = validation["valid"] is True
    return {
        "allowed": allowed,
        "decision": "PENDING_GATE" if allowed else "NO_GO",
        "reason": (
            "emergency_release_freeze_cleared"
            if allowed
            else "controlled_unfreeze_metadata_invalid"
        ),
        "baseline_commit": marker.get("baseline_commit"),
        "reason_codes": marker.get("reason_codes", []),
        "validation_failures": validation["failures"],
        "public_release_authorized": validation["public_release_authorized"],
        "external_network_authorized": validation["external_network_authorized"],
        "provider_activation_authorized": validation["provider_activation_authorized"],
    }
