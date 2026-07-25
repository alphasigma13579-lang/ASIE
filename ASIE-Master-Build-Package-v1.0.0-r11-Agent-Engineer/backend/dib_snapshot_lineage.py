from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from backend.contracts import new_id, now_iso

DIB_SNAPSHOT_LINEAGE_ID = "DIB-LIVE-002G-SNAPSHOT-LINEAGE-v1"
DIB_SNAPSHOT_LINEAGE_STATUS = "post_freeze_snapshot_lineage_overlay"
DIB_SNAPSHOT_LINEAGE_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"
DIB_SNAPSHOT_LINEAGE_CONTRACT_ID = "dib.snapshot.lineage.v1"

FORBIDDEN_DIB_SNAPSHOT_LINEAGE_FIELDS = frozenset(
    {
        "raw_prompt",
        "prompt_template",
        "raw_file",
        "file_base64",
        "pdf_text",
        "api_key",
        "openai_api_key",
        "provider_config",
        "ai_provider",
        "finance",
        "finance_result",
        "sealed_outputs",
        "snapshot",
        "assembled_snapshot",
        "decision_pack",
    }
)

FORBIDDEN_DIB_SNAPSHOT_LINEAGE_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "finance_wiring_enabled",
        "snapshot_wiring_enabled",
        "snapshot_mutation_enabled",
    }
)


class DIBSnapshotLineageError(ValueError):
    pass


@dataclass(frozen=True)
class DIBSnapshotLineageRecord:
    lineage_id: str
    project_id: str
    run_id: str
    snapshot_id: str
    manifest_id: str
    manifest_validation_gate_id: str
    project_run_manifest_gate_id: str
    lineage_chain: tuple[dict[str, Any], ...]
    payload_hash: str
    created_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "contract_id": DIB_SNAPSHOT_LINEAGE_CONTRACT_ID,
            "lineage_id": self.lineage_id,
            "lineage_type": DIB_SNAPSHOT_LINEAGE_ID,
            "status": "prepared",
            "project_id": self.project_id,
            "run_id": self.run_id,
            "snapshot_id": self.snapshot_id,
            "source_manifest_id": self.manifest_id,
            "source_manifest_validation_gate_id": self.manifest_validation_gate_id,
            "source_project_run_manifest_gate_id": self.project_run_manifest_gate_id,
            "lineage_chain": [dict(item) for item in self.lineage_chain],
            "payload_hash": self.payload_hash,
            "created_at": self.created_at,
            "ready_for_snapshot_projection_support": True,
            "input_source": "approved_input_manifest_only",
            "snapshot_assembly_mount": "planned",
            "projection_support_mount": "planned",
            "snapshot_mutation": False,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_snapshot_assembly_mutated": False,
        }


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dump(payload).encode("utf-8")).hexdigest()


def _reject_forbidden_payload(payload: Any, *, context: str) -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in FORBIDDEN_DIB_SNAPSHOT_LINEAGE_FIELDS:
                    raise DIBSnapshotLineageError(f"{context} contains forbidden field: {path}.{key_text}")
                if key_text in FORBIDDEN_DIB_SNAPSHOT_LINEAGE_TRUE_FLAGS and item is True:
                    raise DIBSnapshotLineageError(f"{context} attempted to enable forbidden flag: {path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload, context)


def _require_text(value: Any, *, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DIBSnapshotLineageError(f"missing required lineage identity: {name}")
    return text


def _stage_hash(stage: str, payload: dict[str, Any]) -> str:
    return _payload_hash({"stage": stage, "payload": payload})


def _validate_lineage_sources(
    manifest: dict[str, Any],
    validation_gate: dict[str, Any],
    project_run_manifest_gate: dict[str, Any],
) -> None:
    _reject_forbidden_payload(manifest, context="approved_manifest")
    _reject_forbidden_payload(validation_gate, context="manifest_validation_gate")
    _reject_forbidden_payload(project_run_manifest_gate, context="project_run_manifest_gate")

    if manifest.get("contract_id") != "approved.input.manifest.v1":
        raise DIBSnapshotLineageError("snapshot lineage requires approved.input.manifest.v1")
    if manifest.get("status") != "approved":
        raise DIBSnapshotLineageError("snapshot lineage requires approved manifest status")
    if validation_gate.get("contract_id") != "manifest.validation.v1":
        raise DIBSnapshotLineageError("snapshot lineage requires manifest.validation.v1")
    if validation_gate.get("status") != "passed":
        raise DIBSnapshotLineageError("snapshot lineage requires passed manifest validation gate")
    if validation_gate.get("manifest_id") != manifest.get("manifest_id"):
        raise DIBSnapshotLineageError("snapshot lineage manifest validation gate mismatch")

    if project_run_manifest_gate.get("contract_id") != "dib.project_run.manifest_gate.v1":
        raise DIBSnapshotLineageError("snapshot lineage requires dib.project_run.manifest_gate.v1")
    if project_run_manifest_gate.get("status") != "passed" or project_run_manifest_gate.get("ready_for_project_run") is not True:
        raise DIBSnapshotLineageError("snapshot lineage requires passed DIB Project Run Manifest Gate")
    if project_run_manifest_gate.get("input_contract_id") != "approved.input.manifest.v1":
        raise DIBSnapshotLineageError("snapshot lineage requires approved manifest input contract")
    if project_run_manifest_gate.get("input_source") != "approved_input_manifest_only":
        raise DIBSnapshotLineageError("snapshot lineage accepts only approved_input_manifest_only")
    if project_run_manifest_gate.get("manifest_id") != manifest.get("manifest_id"):
        raise DIBSnapshotLineageError("snapshot lineage project run manifest gate mismatch")
    if project_run_manifest_gate.get("manifest_validation_gate_id") != validation_gate.get("gate_id"):
        raise DIBSnapshotLineageError("snapshot lineage project run validation gate mismatch")


def build_dib_snapshot_lineage(
    manifest: dict[str, Any],
    validation_gate: dict[str, Any],
    project_run_manifest_gate: dict[str, Any],
    *,
    run_id: str,
    snapshot_id: str,
) -> dict[str, Any]:
    """Prepare DIB lineage metadata for a future Snapshot support envelope.

    This function is a post-freeze overlay. It does not call or mutate
    snapshot_assembly.py and it does not create a Snapshot. It creates a
    deterministic lineage chain proving that a future Snapshot projection can
    trace inputs back to Approved Input Manifest -> Manifest Validation Gate ->
    DIB Project Run Manifest Gate.
    """

    _validate_lineage_sources(manifest, validation_gate, project_run_manifest_gate)

    project_id = _require_text(manifest.get("project_id") or project_run_manifest_gate.get("project_id"), name="project_id")
    run_id = _require_text(run_id, name="run_id")
    snapshot_id = _require_text(snapshot_id, name="snapshot_id")
    manifest_id = _require_text(manifest.get("manifest_id"), name="manifest_id")
    validation_gate_id = _require_text(validation_gate.get("gate_id"), name="manifest_validation_gate_id")
    project_run_gate_id = _require_text(project_run_manifest_gate.get("gate_id"), name="project_run_manifest_gate_id")

    manifest_source = {
        "manifest_id": manifest_id,
        "contract_id": manifest["contract_id"],
        "status": manifest["status"],
        "blueprint_id": manifest.get("blueprint_id"),
        "revision": manifest.get("revision"),
        "normalized_input_keys": sorted((manifest.get("normalized_inputs") or {}).keys()),
    }
    validation_source = {
        "gate_id": validation_gate_id,
        "contract_id": validation_gate["contract_id"],
        "status": validation_gate["status"],
        "manifest_id": validation_gate.get("manifest_id"),
        "blocker_count": len(validation_gate.get("blockers") or []),
    }
    project_run_gate_source = {
        "gate_id": project_run_gate_id,
        "contract_id": project_run_manifest_gate["contract_id"],
        "status": project_run_manifest_gate["status"],
        "manifest_id": project_run_manifest_gate.get("manifest_id"),
        "manifest_validation_gate_id": project_run_manifest_gate.get("manifest_validation_gate_id"),
        "input_hash": project_run_manifest_gate.get("payload_hash"),
        "input_source": project_run_manifest_gate.get("input_source"),
    }
    lineage_chain = (
        {
            "stage": "approved_input_manifest",
            "contract_id": "approved.input.manifest.v1",
            "object_id": manifest_id,
            "status": manifest["status"],
            "object_hash": _stage_hash("approved_input_manifest", manifest_source),
        },
        {
            "stage": "manifest_validation_gate",
            "contract_id": "manifest.validation.v1",
            "object_id": validation_gate_id,
            "status": validation_gate["status"],
            "object_hash": _stage_hash("manifest_validation_gate", validation_source),
        },
        {
            "stage": "project_run_manifest_gate",
            "contract_id": "dib.project_run.manifest_gate.v1",
            "object_id": project_run_gate_id,
            "status": project_run_manifest_gate["status"],
            "object_hash": _stage_hash("project_run_manifest_gate", project_run_gate_source),
        },
    )
    payload = {
        "project_id": project_id,
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "manifest_id": manifest_id,
        "manifest_validation_gate_id": validation_gate_id,
        "project_run_manifest_gate_id": project_run_gate_id,
        "lineage_chain": lineage_chain,
        "input_source": "approved_input_manifest_only",
    }
    record = DIBSnapshotLineageRecord(
        lineage_id=new_id("dib_snapshot_lineage"),
        project_id=project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        manifest_id=manifest_id,
        manifest_validation_gate_id=validation_gate_id,
        project_run_manifest_gate_id=project_run_gate_id,
        lineage_chain=lineage_chain,
        payload_hash=_payload_hash(payload),
        created_at=now_iso(),
    )
    return record.to_public()


def build_dib_projection_support_payload(lineage: dict[str, Any]) -> dict[str, Any]:
    """Return a support payload that a future non-frozen mount can seal later.

    The returned object is intentionally not a sealed envelope and does not call
    Snapshot Assembly. It is safe metadata for a later projection support mount.
    """

    _reject_forbidden_payload(lineage, context="dib_snapshot_lineage")
    if lineage.get("contract_id") != DIB_SNAPSHOT_LINEAGE_CONTRACT_ID:
        raise DIBSnapshotLineageError("projection support requires dib.snapshot.lineage.v1")
    if lineage.get("ready_for_snapshot_projection_support") is not True:
        raise DIBSnapshotLineageError("DIB snapshot lineage is not ready for projection support")
    return {
        "contract_id": "dib.snapshot.projection_support.v1",
        "source_lineage_contract_id": DIB_SNAPSHOT_LINEAGE_CONTRACT_ID,
        "lineage_id": lineage["lineage_id"],
        "project_id": lineage["project_id"],
        "run_id": lineage["run_id"],
        "snapshot_id": lineage["snapshot_id"],
        "source_manifest_id": lineage["source_manifest_id"],
        "source_manifest_validation_gate_id": lineage["source_manifest_validation_gate_id"],
        "source_project_run_manifest_gate_id": lineage["source_project_run_manifest_gate_id"],
        "lineage_payload_hash": lineage["payload_hash"],
        "lineage_chain": list(lineage["lineage_chain"]),
        "snapshot_assembly_mount": "planned",
        "sealed_envelope_created": False,
        "snapshot_mutation": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_snapshot_assembly_mutated": False,
    }


def dib_snapshot_lineage_status() -> dict[str, Any]:
    return {
        "lineage_id": DIB_SNAPSHOT_LINEAGE_ID,
        "status": DIB_SNAPSHOT_LINEAGE_STATUS,
        "source": DIB_SNAPSHOT_LINEAGE_SOURCE,
        "lineage_contract_id": DIB_SNAPSHOT_LINEAGE_CONTRACT_ID,
        "required_chain": [
            "approved.input.manifest.v1",
            "manifest.validation.v1",
            "dib.project_run.manifest_gate.v1",
        ],
        "snapshot_assembly_mount": "planned",
        "projection_support_mount": "planned",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_snapshot_assembly_mutated": False,
    }
