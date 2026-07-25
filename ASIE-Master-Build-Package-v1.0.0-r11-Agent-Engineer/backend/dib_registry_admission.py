from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.aas_registry import (
    AASRegistry,
    ContractDefinition,
    ModuleDefinition,
    SocketDefinition,
    bootstrap_default_registry,
)
from backend.dib_runtime import DIB_CONTRACTS, DIB_MODULES, DIB_SOCKETS

DIB_REGISTRY_ADMISSION_ID = "DIB-LIVE-002A-FREEZE-SAFE-REGISTRY-ADMISSION-v1"
DIB_REGISTRY_ADMISSION_STATUS = "post_freeze_overlay"
DIB_REGISTRY_ADMISSION_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"
DIB_RUNTIME_OWNER_FILE = "backend/dib_runtime.py"
AAS_RUNTIME_FREEZE_MANIFEST = "docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"

DIB_CONTRACT_SPECS: tuple[ContractDefinition, ...] = (
    ContractDefinition(
        contract_id="template.registry.v1",
        version="1.0.0-dib-live-002a",
        owner="Template Registry Module",
        purpose="Resolve governed project input templates before question generation or file mapping.",
        required_fields=("project_profile", "template_id", "template_items"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="question.registry.v1",
        version="1.0.0-dib-live-002a",
        owner="Question Registry Module",
        purpose="Provide governed interview questions for a selected input template.",
        required_fields=("template_id", "questions"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="product.ai.interview.v1",
        version="1.0.0-dib-live-002a",
        owner="Product AI Interview Module",
        purpose="Run the offline governed product interview without enabling an AI provider.",
        required_fields=("project_profile", "template_id", "proposed_items", "ai_provider_enabled"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="data.intake.v1",
        version="1.0.0-dib-live-002a",
        owner="Data Intake Module",
        purpose="Normalize manual, CSV, XLSX, and PDF-text input rows before DIB mapping.",
        required_fields=("source_type", "normalized_rows"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="dynamic.input.blueprint.v1",
        version="1.0.0-dib-live-002a",
        owner="Dynamic Input Blueprint Module",
        purpose="Assemble project input items, item states, source lineage, and review state before manifest approval.",
        required_fields=("project_profile", "items", "blueprint_id"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="market.query.request.v1",
        version="1.0.0-dib-live-002a",
        owner="Market Intelligence Module",
        purpose="Request local, offline market evidence candidates for one DIB item without network fetch.",
        required_fields=("item_id", "input_key", "geography", "external_fetch_enabled"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="market.evidence.pack.v1",
        version="1.0.0-dib-live-002a",
        owner="Market Intelligence Module",
        purpose="Return bounded evidence bands and weighted median candidates for a DIB item.",
        required_fields=("item_id", "input_key", "p25", "p75", "weighted_median", "evidence_refs"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="customer.item.decision.v1",
        version="1.0.0-dib-live-002a",
        owner="Customer Item Decision Module",
        purpose="Record customer accept, edit, reject, intentional-zero, or not-applicable decisions per DIB item.",
        required_fields=("item_id", "action", "decided_by"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="approved.input.manifest.v1",
        version="1.0.0-dib-live-002a",
        owner="Approved Input Manifest Module",
        purpose="Seal approved normalized project assumptions before any Finance Engine use.",
        required_fields=("manifest_id", "blueprint_id", "normalized_inputs", "status"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="manifest.validation.v1",
        version="1.0.0-dib-live-002a",
        owner="Manifest Validation Gate Module",
        purpose="Block runtime entry when required approved manifest inputs are missing or unreviewed.",
        required_fields=("manifest_id", "status", "blockers"),
        status="post_freeze_admitted",
    ),
    ContractDefinition(
        contract_id="dib.draft.revision.v1",
        version="1.0.0-dib-live-002a",
        owner="DIB Revision Module",
        purpose="Record a draft revision lineage when DIB items change after analysis.",
        required_fields=("blueprint_id", "parent_blueprint_id", "changes", "reason"),
        status="post_freeze_admitted",
    ),
)

DIB_SOCKET_SPECS: tuple[SocketDefinition, ...] = (
    SocketDefinition(
        socket_id="socket.template.registry",
        contract_id="template.registry.v1",
        provider_module_id="module.template_registry",
        consumer_module_ids=("module.product_ai_interview", "module.dynamic_input_blueprint"),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.question.registry",
        contract_id="question.registry.v1",
        provider_module_id="module.question_registry",
        consumer_module_ids=("module.product_ai_interview", "module.dynamic_input_blueprint"),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.product.ai.interview",
        contract_id="product.ai.interview.v1",
        provider_module_id="module.product_ai_interview",
        consumer_module_ids=("module.dynamic_input_blueprint",),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.data.intake",
        contract_id="data.intake.v1",
        provider_module_id="module.data_intake",
        consumer_module_ids=("module.dynamic_input_blueprint",),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.dynamic.input.blueprint",
        contract_id="dynamic.input.blueprint.v1",
        provider_module_id="module.dynamic_input_blueprint",
        consumer_module_ids=("module.market_intelligence", "module.approved_input_manifest", "module.dib_revision"),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.market.query",
        contract_id="market.query.request.v1",
        provider_module_id="module.market_intelligence",
        consumer_module_ids=("module.dynamic_input_blueprint", "module.approved_input_manifest"),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.customer.item.decision",
        contract_id="customer.item.decision.v1",
        provider_module_id="module.dynamic_input_blueprint",
        consumer_module_ids=("module.approved_input_manifest",),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.approved.input.manifest",
        contract_id="approved.input.manifest.v1",
        provider_module_id="module.approved_input_manifest",
        consumer_module_ids=("module.manifest_validation_gate",),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.manifest.validation",
        contract_id="manifest.validation.v1",
        provider_module_id="module.manifest_validation_gate",
        consumer_module_ids=("module.dynamic_input_blueprint",),
        status="post_freeze_admitted",
    ),
    SocketDefinition(
        socket_id="socket.dib.revision",
        contract_id="dib.draft.revision.v1",
        provider_module_id="module.dib_revision",
        consumer_module_ids=("module.dynamic_input_blueprint", "module.approved_input_manifest"),
        status="post_freeze_admitted",
    ),
)

DIB_MODULE_SPECS: tuple[ModuleDefinition, ...] = (
    ModuleDefinition(
        module_id="module.template_registry",
        label="Template Registry",
        module_type="dib_registry",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.template.registry",),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "offline_only"),
    ),
    ModuleDefinition(
        module_id="module.question_registry",
        label="Question Registry",
        module_type="dib_registry",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.question.registry",),
        requires=("socket.template.registry",),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "offline_only"),
    ),
    ModuleDefinition(
        module_id="module.product_ai_interview",
        label="Product AI Interview",
        module_type="dib_interview",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.product.ai.interview",),
        requires=("socket.template.registry", "socket.question.registry"),
        lifecycle_state="post_freeze_admitted",
        external_fetch_enabled=False,
        notes=(DIB_REGISTRY_ADMISSION_ID, "ai_provider_disabled", "network_disabled"),
    ),
    ModuleDefinition(
        module_id="module.data_intake",
        label="Data Intake",
        module_type="dib_intake",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.data.intake",),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "manual_csv_xlsx_pdf_text_only"),
    ),
    ModuleDefinition(
        module_id="module.dynamic_input_blueprint",
        label="Dynamic Input Blueprint",
        module_type="dib_blueprint",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.dynamic.input.blueprint", "socket.customer.item.decision"),
        requires=("socket.template.registry", "socket.question.registry", "socket.product.ai.interview", "socket.data.intake"),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "no_finance_direct_call"),
    ),
    ModuleDefinition(
        module_id="module.market_intelligence",
        label="Market Intelligence",
        module_type="dib_market_evidence",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.market.query",),
        requires=("socket.dynamic.input.blueprint",),
        lifecycle_state="post_freeze_admitted",
        external_fetch_enabled=False,
        notes=(DIB_REGISTRY_ADMISSION_ID, "offline_catalogue_only", "network_disabled"),
    ),
    ModuleDefinition(
        module_id="module.approved_input_manifest",
        label="Approved Input Manifest",
        module_type="dib_manifest",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.approved.input.manifest",),
        requires=("socket.dynamic.input.blueprint", "socket.customer.item.decision", "socket.market.query"),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "finance_requires_manifest_later"),
    ),
    ModuleDefinition(
        module_id="module.manifest_validation_gate",
        label="Manifest Validation Gate",
        module_type="dib_gate",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.manifest.validation",),
        requires=("socket.approved.input.manifest",),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "blocks_incomplete_manifest"),
    ),
    ModuleDefinition(
        module_id="module.dib_revision",
        label="DIB Revision",
        module_type="dib_revision",
        owner_file=DIB_RUNTIME_OWNER_FILE,
        provides=("socket.dib.revision",),
        requires=("socket.dynamic.input.blueprint", "socket.approved.input.manifest"),
        lifecycle_state="post_freeze_admitted",
        notes=(DIB_REGISTRY_ADMISSION_ID, "revision_lineage_only"),
    ),
)


def dib_contract_ids() -> set[str]:
    return {contract.contract_id for contract in DIB_CONTRACT_SPECS}


def dib_socket_ids() -> set[str]:
    return {socket.socket_id for socket in DIB_SOCKET_SPECS}


def dib_module_ids() -> set[str]:
    return {module.module_id for module in DIB_MODULE_SPECS}


def assert_dib_runtime_alignment() -> None:
    if dib_contract_ids() != set(DIB_CONTRACTS):
        raise AssertionError("dib_contract_admission_does_not_match_runtime")
    if dib_socket_ids() != set(DIB_SOCKETS):
        raise AssertionError("dib_socket_admission_does_not_match_runtime")
    if dib_module_ids() != set(DIB_MODULES):
        raise AssertionError("dib_module_admission_does_not_match_runtime")


def build_effective_dib_registry() -> AASRegistry:
    """Return a freeze-safe effective registry view with DIB admitted as an overlay.

    The frozen AAS registry file is not modified. The default frozen registry is
    bootstrapped first, then DIB registrations are applied to the in-memory view
    used by DIB-LIVE-002A tests and later integration phases.
    """
    assert_dib_runtime_alignment()
    registry = bootstrap_default_registry()
    for contract in DIB_CONTRACT_SPECS:
        registry.register_contract(contract)
    for socket in DIB_SOCKET_SPECS:
        registry.register_socket(socket)
    for module in DIB_MODULE_SPECS:
        registry.register_module(module)
    return registry


def effective_dib_registry_snapshot() -> dict[str, Any]:
    registry = build_effective_dib_registry()
    snapshot = registry.snapshot()
    snapshot["admission"] = {
        "admission_id": DIB_REGISTRY_ADMISSION_ID,
        "status": DIB_REGISTRY_ADMISSION_STATUS,
        "source": DIB_REGISTRY_ADMISSION_SOURCE,
        "runtime_owner_file": DIB_RUNTIME_OWNER_FILE,
        "frozen_registry_mutated": False,
        "ai_provider_enabled": False,
        "external_fetch_enabled": False,
        "counts": {
            "contracts": len(DIB_CONTRACT_SPECS),
            "sockets": len(DIB_SOCKET_SPECS),
            "modules": len(DIB_MODULE_SPECS),
        },
    }
    return snapshot


def frozen_file_hashes(package_root: Path) -> dict[str, str]:
    manifest_path = package_root / AAS_RUNTIME_FREEZE_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["frozen_files"]}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_registry_file_unchanged(package_root: Path) -> None:
    expected = frozen_file_hashes(package_root)["backend/aas_registry.py"]
    actual = sha256_file(package_root / "backend/aas_registry.py")
    if actual != expected:
        raise AssertionError("aas_registry_freeze_hash_changed")


def assert_all_frozen_files_unchanged(package_root: Path) -> None:
    for relative_path, expected in frozen_file_hashes(package_root).items():
        actual = sha256_file(package_root / relative_path)
        if actual != expected:
            raise AssertionError(f"frozen_file_hash_changed:{relative_path}")
