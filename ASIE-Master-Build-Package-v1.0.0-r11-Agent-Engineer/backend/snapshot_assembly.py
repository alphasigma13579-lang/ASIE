from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from backend.contracts import now_iso


class SnapshotAssemblyError(ValueError):
    pass


SEALED_ENVELOPE_CONTRACT_ID = "aas.sealed.module.output.v1"
SNAPSHOT_ASSEMBLY_CONTRACT_ID = "snapshot.assemble.v1"
SNAPSHOT_VERSION = "1.0.0-local-core"
PROJECTION_SUPPORT_CONTRACT_ID = "snapshot.projection.support.v1"

REQUIRED_MODULE_OUTPUTS = {
    "finance_result": ("module.finance", "finance.result.v1"),
    "evidence_ledger": ("module.evidence_ledger", "evidence.ledger.v1"),
    "sector_intelligence": ("module.sector_intelligence", "sector.intelligence.v1"),
    "decision_result": ("module.decision_council", "decision.council.v1"),
    "risk_result": ("module.risk_engine", "risk.register.v1"),
    "execution_result": ("module.execution_engine", "execution.plan.v1"),
}

SEALED_ENVELOPE_FIELDS = frozenset(
    {
        "envelope_id",
        "envelope_contract_id",
        "output_key",
        "producer_module_id",
        "producer_contract_id",
        "producer_contract_version",
        "project_id",
        "run_id",
        "snapshot_id",
        "message_id",
        "correlation_id",
        "audit_ref",
        "produced_at",
        "output",
        "output_hash",
        "sealed",
    }
)

SUPPORTING_OUTPUT_FIELDS = SEALED_ENVELOPE_FIELDS


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SealedModuleOutputEnvelope:
    envelope_id: str
    envelope_contract_id: str
    output_key: str
    producer_module_id: str
    producer_contract_id: str
    producer_contract_version: str
    project_id: str
    run_id: str
    snapshot_id: str
    message_id: str
    correlation_id: str
    audit_ref: str
    produced_at: str
    output: dict[str, Any]
    output_hash: str
    sealed: bool = True

    def to_public(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "envelope_contract_id": self.envelope_contract_id,
            "output_key": self.output_key,
            "producer_module_id": self.producer_module_id,
            "producer_contract_id": self.producer_contract_id,
            "producer_contract_version": self.producer_contract_version,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "snapshot_id": self.snapshot_id,
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "audit_ref": self.audit_ref,
            "produced_at": self.produced_at,
            "output": deepcopy(self.output),
            "output_hash": self.output_hash,
            "sealed": self.sealed,
        }


def seal_module_output(
    *,
    output_key: str,
    producer_module_id: str,
    producer_contract_id: str,
    producer_contract_version: str,
    project_id: str,
    run_id: str,
    snapshot_id: str,
    message_id: str,
    correlation_id: str,
    audit_ref: str,
    produced_at: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    if output_key not in REQUIRED_MODULE_OUTPUTS:
        raise SnapshotAssemblyError(f"unknown sealed output key: {output_key}")
    expected_module, expected_contract = REQUIRED_MODULE_OUTPUTS[output_key]
    if producer_module_id != expected_module or producer_contract_id != expected_contract:
        raise SnapshotAssemblyError(f"producer identity does not match output key: {output_key}")
    for identity_field, expected in (
        ("project_id", project_id),
        ("run_id", run_id),
        ("snapshot_id", snapshot_id),
    ):
        if output.get(identity_field) != expected:
            raise SnapshotAssemblyError(f"module output {identity_field} does not match sealed envelope")
    if output.get("module_id") != producer_module_id or output.get("contract_id") != producer_contract_id:
        raise SnapshotAssemblyError("module output producer or contract identity does not match sealed envelope")
    copied_output = deepcopy(output)
    output_hash = canonical_hash(copied_output)
    envelope = SealedModuleOutputEnvelope(
        envelope_id=f"sealed:{run_id}:{output_key}",
        envelope_contract_id=SEALED_ENVELOPE_CONTRACT_ID,
        output_key=output_key,
        producer_module_id=producer_module_id,
        producer_contract_id=producer_contract_id,
        producer_contract_version=producer_contract_version,
        project_id=project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        message_id=message_id,
        correlation_id=correlation_id,
        audit_ref=audit_ref,
        produced_at=produced_at,
        output=copied_output,
        output_hash=output_hash,
    )
    return envelope.to_public()


def seal_projection_support(
    *,
    project_id: str,
    run_id: str,
    snapshot_id: str,
    correlation_id: str,
    audit_ref: str,
    produced_at: str,
    projection_support: dict[str, Any],
) -> dict[str, Any]:
    output = {
        "module_id": "aas.heart_controller",
        "contract_id": PROJECTION_SUPPORT_CONTRACT_ID,
        "project_id": project_id,
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "projection_support": deepcopy(projection_support),
        "external_fetch_enabled": False,
        "ai_enabled": False,
    }
    return SealedModuleOutputEnvelope(
        envelope_id=f"sealed:{run_id}:projection_support",
        envelope_contract_id=SEALED_ENVELOPE_CONTRACT_ID,
        output_key="projection_support",
        producer_module_id="aas.heart_controller",
        producer_contract_id=PROJECTION_SUPPORT_CONTRACT_ID,
        producer_contract_version=SNAPSHOT_VERSION,
        project_id=project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        message_id=f"context:{run_id}:projection-support",
        correlation_id=correlation_id,
        audit_ref=audit_ref,
        produced_at=produced_at,
        output=output,
        output_hash=canonical_hash(output),
    ).to_public()


def assemble_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_payload_fields = {
        "project_id",
        "run_id",
        "snapshot_id",
        "input_contract_id",
        "sealed_outputs",
        "project_context",
        "readiness_state",
        "blockers",
        "sealed_supporting_outputs",
    }
    required_payload_fields = allowed_payload_fields - {"sealed_supporting_outputs"}
    missing_payload = required_payload_fields - set(payload)
    extra_payload = set(payload) - allowed_payload_fields
    if missing_payload:
        raise SnapshotAssemblyError("snapshot assembly payload missing fields: " + ", ".join(sorted(missing_payload)))
    if extra_payload:
        raise SnapshotAssemblyError("snapshot assembly payload contains forbidden fields: " + ", ".join(sorted(extra_payload)))
    if payload["input_contract_id"] != "SnapshotAssemblyInputEnvelope.v1":
        raise SnapshotAssemblyError("snapshot assembly requires SnapshotAssemblyInputEnvelope.v1")
    if not isinstance(payload["sealed_outputs"], list):
        raise SnapshotAssemblyError("sealed_outputs must be a list")

    validated: dict[str, dict[str, Any]] = {}
    lineage: list[dict[str, Any]] = []
    correlation_map: dict[str, str] = {}
    for envelope in payload["sealed_outputs"]:
        validate_sealed_envelope(envelope, payload)
        output_key = envelope["output_key"]
        if output_key in validated:
            raise SnapshotAssemblyError(f"duplicate sealed output: {output_key}")
        validated[output_key] = deepcopy(envelope)
        correlation_map[output_key] = envelope["correlation_id"]
        lineage.append(
            {
                "output_key": output_key,
                "envelope_id": envelope["envelope_id"],
                "producer_module_id": envelope["producer_module_id"],
                "producer_contract_id": envelope["producer_contract_id"],
                "producer_contract_version": envelope["producer_contract_version"],
                "message_id": envelope["message_id"],
                "correlation_id": envelope["correlation_id"],
                "audit_ref": envelope["audit_ref"],
                "output_hash": envelope["output_hash"],
            }
        )

    missing_outputs = set(REQUIRED_MODULE_OUTPUTS) - set(validated)
    if missing_outputs:
        raise SnapshotAssemblyError("required sealed module outputs missing: " + ", ".join(sorted(missing_outputs)))
    if set(validated) - set(REQUIRED_MODULE_OUTPUTS):
        raise SnapshotAssemblyError("snapshot assembly received unregistered module outputs")

    supporting_outputs: dict[str, dict[str, Any]] = {}
    for envelope in payload.get("sealed_supporting_outputs", []):
        validate_projection_support_envelope(envelope, payload)
        output_key = envelope["output_key"]
        if output_key in supporting_outputs:
            raise SnapshotAssemblyError(f"duplicate sealed supporting output: {output_key}")
        supporting_outputs[output_key] = deepcopy(envelope["output"])
        correlation_map[output_key] = envelope["correlation_id"]
        lineage.append(
            {
                "output_key": output_key,
                "envelope_id": envelope["envelope_id"],
                "producer_module_id": envelope["producer_module_id"],
                "producer_contract_id": envelope["producer_contract_id"],
                "producer_contract_version": envelope["producer_contract_version"],
                "message_id": envelope["message_id"],
                "correlation_id": envelope["correlation_id"],
                "audit_ref": envelope["audit_ref"],
                "output_hash": envelope["output_hash"],
            }
        )

    assembled_at = now_iso()
    module_outputs = {key: validated[key]["output"] for key in REQUIRED_MODULE_OUTPUTS}
    content = {
        "snapshot_id": payload["snapshot_id"],
        "snapshot_version": SNAPSHOT_VERSION,
        "project_id": payload["project_id"],
        "run_id": payload["run_id"],
        "module_outputs": module_outputs,
        "supporting_outputs": supporting_outputs,
        "project_context": deepcopy(payload["project_context"]),
        "readiness_state": deepcopy(payload["readiness_state"]),
        "blockers": deepcopy(payload["blockers"]),
        "lineage": sorted(lineage, key=lambda row: row["output_key"]),
        "correlation_map": correlation_map,
    }
    content_hash = canonical_hash(content)
    integrity_hash = canonical_hash(
        {
            "assembly_contract_id": SNAPSHOT_ASSEMBLY_CONTRACT_ID,
            "assembled_at": assembled_at,
            "content_hash": content_hash,
        }
    )
    return content | {
        "assembly_contract_id": SNAPSHOT_ASSEMBLY_CONTRACT_ID,
        "assembled_at": assembled_at,
        "content_hash": content_hash,
        "integrity_hash": integrity_hash,
        "immutable": True,
        "external_fetch_enabled": False,
        "ai_enabled": False,
    }


def validate_sealed_envelope(envelope: Any, payload: dict[str, Any]) -> None:
    if not isinstance(envelope, dict):
        raise SnapshotAssemblyError("sealed module output must be an object")
    missing = SEALED_ENVELOPE_FIELDS - set(envelope)
    extra = set(envelope) - SEALED_ENVELOPE_FIELDS
    if missing:
        raise SnapshotAssemblyError("sealed module output missing fields: " + ", ".join(sorted(missing)))
    if extra:
        raise SnapshotAssemblyError("sealed module output contains forbidden fields: " + ", ".join(sorted(extra)))
    if envelope["envelope_contract_id"] != SEALED_ENVELOPE_CONTRACT_ID or envelope["sealed"] is not True:
        raise SnapshotAssemblyError("snapshot assembly accepts sealed module output envelopes only")
    output_key = envelope["output_key"]
    if output_key not in REQUIRED_MODULE_OUTPUTS:
        raise SnapshotAssemblyError(f"unregistered sealed output key: {output_key}")
    expected_module, expected_contract = REQUIRED_MODULE_OUTPUTS[output_key]
    if envelope["producer_module_id"] != expected_module or envelope["producer_contract_id"] != expected_contract:
        raise SnapshotAssemblyError(f"sealed output producer mismatch: {output_key}")
    if not envelope["producer_contract_version"]:
        raise SnapshotAssemblyError(f"sealed output contract version missing: {output_key}")
    for identity_field in ("project_id", "run_id", "snapshot_id"):
        if envelope[identity_field] != payload[identity_field]:
            raise SnapshotAssemblyError(f"sealed output {identity_field} mismatch: {output_key}")
    output = envelope["output"]
    if not isinstance(output, dict):
        raise SnapshotAssemblyError(f"sealed output payload must be an object: {output_key}")
    if output.get("module_id") != expected_module or output.get("contract_id") != expected_contract:
        raise SnapshotAssemblyError(f"sealed output internal identity mismatch: {output_key}")
    for identity_field in ("project_id", "run_id", "snapshot_id"):
        if output.get(identity_field) != payload[identity_field]:
            raise SnapshotAssemblyError(f"sealed output internal {identity_field} mismatch: {output_key}")
    if canonical_hash(output) != envelope["output_hash"]:
        raise SnapshotAssemblyError(f"sealed output integrity check failed: {output_key}")


def validate_projection_support_envelope(envelope: Any, payload: dict[str, Any]) -> None:
    if not isinstance(envelope, dict):
        raise SnapshotAssemblyError("sealed supporting output must be an object")
    missing = SUPPORTING_OUTPUT_FIELDS - set(envelope)
    extra = set(envelope) - SUPPORTING_OUTPUT_FIELDS
    if missing or extra:
        raise SnapshotAssemblyError("sealed projection support envelope fields are invalid")
    if envelope["envelope_contract_id"] != SEALED_ENVELOPE_CONTRACT_ID or envelope["sealed"] is not True:
        raise SnapshotAssemblyError("projection support must use a sealed output envelope")
    if envelope["output_key"] != "projection_support":
        raise SnapshotAssemblyError("unregistered supporting output key")
    if envelope["producer_module_id"] != "aas.heart_controller":
        raise SnapshotAssemblyError("projection support producer mismatch")
    if envelope["producer_contract_id"] != PROJECTION_SUPPORT_CONTRACT_ID:
        raise SnapshotAssemblyError("projection support contract mismatch")
    for identity_field in ("project_id", "run_id", "snapshot_id"):
        if envelope[identity_field] != payload[identity_field]:
            raise SnapshotAssemblyError(f"projection support {identity_field} mismatch")
    output = envelope["output"]
    if not isinstance(output, dict):
        raise SnapshotAssemblyError("projection support output must be an object")
    if output.get("module_id") != "aas.heart_controller" or output.get("contract_id") != PROJECTION_SUPPORT_CONTRACT_ID:
        raise SnapshotAssemblyError("projection support internal identity mismatch")
    for identity_field in ("project_id", "run_id", "snapshot_id"):
        if output.get(identity_field) != payload[identity_field]:
            raise SnapshotAssemblyError(f"projection support internal {identity_field} mismatch")
    if not isinstance(output.get("projection_support"), dict):
        raise SnapshotAssemblyError("projection support payload is missing")
    if canonical_hash(output) != envelope["output_hash"]:
        raise SnapshotAssemblyError("projection support integrity check failed")
