"""Defined-only Decision Council v2 contracts. Deliberately not registered in AAS."""
from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash

V2_INPUT_CONTRACT = "decision.council.evaluate.v2"
V2_OUTPUT_CONTRACT = "decision.council.v2"
STATUS = "DEFINED_NOT_IMPLEMENTED"


def build_decision_input_manifest(*, context_id: str, context_hash: str, synthesis_pack_id: str, synthesis_pack_hash: str, approval_receipt_id: str, approval_receipt_hash: str, contract_set_version: str = "AIA-contracts-v1") -> dict[str, Any]:
    values = {"decision_contract_version": "v2", "decision_input_contract_id": V2_INPUT_CONTRACT, "decision_output_contract_id": V2_OUTPUT_CONTRACT, "intelligence_context_id": context_id, "intelligence_context_hash": context_hash, "intelligence_synthesis_pack_id": synthesis_pack_id, "intelligence_synthesis_pack_hash": synthesis_pack_hash, "approval_receipt_id": approval_receipt_id, "approval_receipt_hash": approval_receipt_hash, "external_acquisition_policy_version": "deny_all_v1", "user_evidence_intake_policy_version": "local_only_v1", "review_policy_version": "human_review_v1", "contract_set_version": contract_set_version}
    if any(not values[key] for key in ("intelligence_context_id", "intelligence_context_hash", "intelligence_synthesis_pack_id", "intelligence_synthesis_pack_hash", "approval_receipt_id", "approval_receipt_hash")):
        raise ValueError("decision_input_manifest_incomplete")
    return values | {"manifest_hash": canonical_hash(values), "status": STATUS, "registered_in_aas": False}


def validate_v2_envelope(envelope: dict[str, Any], manifest: dict[str, Any]) -> None:
    if envelope.get("contract_id") != V2_INPUT_CONTRACT or manifest.get("status") != STATUS:
        raise ValueError("decision_v2_not_registered_or_contract_mismatch")
    if envelope.get("decision_input_manifest_hash") != manifest.get("manifest_hash"):
        raise ValueError("decision_v2_manifest_hash_mismatch")
