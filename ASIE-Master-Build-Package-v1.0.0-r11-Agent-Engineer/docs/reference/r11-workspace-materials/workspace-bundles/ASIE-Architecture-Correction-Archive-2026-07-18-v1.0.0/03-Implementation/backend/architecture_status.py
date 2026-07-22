from __future__ import annotations

from typing import Any

from backend.aas_kernel import AASKernel
from backend.ai_integration import AIIntegrationShell
from backend.bus_controller import BusController
from backend.contracts import PROFILE_ID, now_iso
from backend.heart_controller import HeartController
from backend.module_runtime import ModuleRuntime
from backend.system_bus import SystemBus


def build_architecture_runtime_status() -> dict[str, Any]:
    kernel = AASKernel()
    kernel_status = kernel.boot()
    heart_controller = HeartController(kernel)
    heart_status = heart_controller.bootstrap()
    bus_controller = BusController(kernel, heart_controller)
    bus_controller.bootstrap()
    bus = SystemBus(bus_controller)
    bus.bootstrap()
    runtime = ModuleRuntime(kernel, bus)
    runtime.bootstrap()
    runtime.register_default_handlers()
    ai_status = AIIntegrationShell().status()

    registry_snapshot = kernel.registry.snapshot()
    module_by_id = {row["module_id"]: row for row in registry_snapshot["modules"]}
    contract_by_id = {row["contract_id"]: row for row in registry_snapshot["contracts"]}
    contract_ids = {row["contract_id"] for row in registry_snapshot["contracts"]}
    socket_ids = {row["socket_id"] for row in registry_snapshot["sockets"]}
    heart_by_role = {row["role"]: row for row in heart_status["hearts"]}
    runtime_status = runtime.status()
    bus_status = bus.status()
    bus_controller_status = bus_controller.status()
    socket_status = bus_controller_status["guards"]["socket_contract_layer"]

    required_module_handlers = [
        "module.project_run_workflow",
        "module.finance",
        "module.evidence_ledger",
        "module.sector_intelligence",
        "module.decision_council",
        "module.risk_engine",
        "module.execution_engine",
        "module.snapshot_assembly",
        "module.reports",
        "module.decision_pack",
        "module.ai_integration",
    ]
    acceptance_checks = [
        {
            "check_id": "AAS-FINAL-01",
            "label": "Kernel local ports are fixed",
            "passed": kernel_status["ports"] == {"frontend": 5194, "api": 8794},
            "evidence": "frontend=5194 api=8794",
        },
        {
            "check_id": "AAS-FINAL-02",
            "label": "Kernel owns no business logic",
            "passed": kernel_status["kernel"]["business_logic_owner"] == "none",
            "evidence": kernel_status["kernel"]["business_logic_owner"],
        },
        {
            "check_id": "AAS-FINAL-03",
            "label": "Three hearts are controller-managed",
            "passed": (
                heart_by_role.get("primary", {}).get("heart_id") == "M1"
                and heart_by_role.get("assist", {}).get("heart_id") == "M2"
                and heart_by_role.get("reserve", {}).get("heart_id") == "M3"
                and all(row.get("controlled_by") == "heart_controller" for row in heart_status["hearts"])
            ),
            "evidence": "M1 primary, M2 assist, M3 reserve",
        },
        {
            "check_id": "AAS-FINAL-04",
            "label": "Bus and Socket enforce contracts before delivery",
            "passed": (
                bus_status["state"] == "ready"
                and bus_controller_status["state"] == "ready"
                and socket_status["state"] == "enforcing"
                and socket_status["guards"]["socket_first_module_second"] is True
            ),
            "evidence": "Bus ready, Socket Contract Layer enforcing",
        },
        {
            "check_id": "AAS-FINAL-05",
            "label": "Module Runtime has all current module handlers",
            "passed": set(required_module_handlers).issubset(set(runtime_status["registered_handlers"])),
            "evidence": ",".join(required_module_handlers),
        },
        {
            "check_id": "AAS-FINAL-05A",
            "label": "Project Run Workflow is registered behind Bus/Socket",
            "passed": (
                "module.project_run_workflow" in module_by_id
                and "project.run.workflow.v1" in contract_ids
                and "socket.project.run" in socket_ids
            ),
            "evidence": "module.project_run_workflow/socket.project.run/project.run.workflow.v1",
        },
        {
            "check_id": "AAS-FINAL-05E",
            "label": "Bus messages require closed run envelope fields",
            "passed": (
                {"operation_id", "idempotency_key", "input_hash"}.issubset(
                    set(contract_by_id["aas.bus.message.v1"]["required_fields"])
                )
                and bus_controller_status["guards"]["requires_operation_id"] is True
                and bus_controller_status["guards"]["requires_idempotency_key"] is True
                and bus_controller_status["guards"]["requires_input_hash"] is True
            ),
            "evidence": "aas.bus.message.v1 requires operation_id/idempotency_key/input_hash",
        },
        {
            "check_id": "AAS-FINAL-06",
            "label": "Snapshot Assembly is registered behind Bus/Socket",
            "passed": (
                "module.snapshot_assembly" in module_by_id
                and "snapshot.assemble.v1" in contract_ids
                and "socket.snapshot.assemble" in socket_ids
            ),
            "evidence": "module.snapshot_assembly/socket.snapshot.assemble/snapshot.assemble.v1",
        },
        {
            "check_id": "AAS-FINAL-07",
            "label": "AI Integration Shell is governed and providerless",
            "passed": (
                ai_status["state"] == "disabled_governed"
                and ai_status["provider_registry"]["provider_count"] == 0
                and ai_status["provider_registry"]["external_network_enabled"] is False
                and ai_status["ai_provider_enabled"] is False
            ),
            "evidence": "disabled_governed provider_count=0 network=false",
        },
        {
            "check_id": "AAS-FINAL-08",
            "label": "External fetch is disabled across runtime status",
            "passed": (
                kernel_status["guards"]["external_fetch_enabled"] is False
                and registry_snapshot["external_fetch_enabled"] is False
                and bus_status["guards"]["external_fetch_enabled"] is False
                and runtime_status["guards"]["external_fetch_enabled"] is False
                and ai_status["external_fetch_enabled"] is False
            ),
            "evidence": "external_fetch_enabled=false",
        },
    ]

    return {
        "status_id": "architecture-runtime-status-local-v1",
        "profile_id": PROFILE_ID,
        "generated_at": now_iso(),
        "projection_type": "read_only_runtime_projection",
        "mutability": "read_only_projection",
        "allowed_methods": ["GET"],
        "forbidden_methods": ["POST", "PATCH", "PUT", "DELETE"],
        "overall_status": "passed" if all(row["passed"] for row in acceptance_checks) else "failed",
        "ports": kernel_status["ports"],
        "kernel": kernel_status["kernel"],
        "registry": {
            "registry_id": registry_snapshot["registry_id"],
            "counts": kernel.registry.counts(),
            "contracts": registry_snapshot["contracts"],
            "sockets": registry_snapshot["sockets"],
            "modules": registry_snapshot["modules"],
            "external_fetch_enabled": registry_snapshot["external_fetch_enabled"],
        },
        "heart_controller": heart_status,
        "bus_controller": bus_controller_status,
        "system_bus": bus_status,
        "socket_contract_layer": socket_status,
        "module_runtime": runtime_status,
        "snapshot_assembly": {
            "module": module_by_id["module.snapshot_assembly"],
            "contract_id": "snapshot.assemble.v1",
            "socket_id": "socket.snapshot.assemble",
            "status": "registered_runtime_wrapped",
            "recalculates": False,
            "persists": False,
            "external_fetch_enabled": False,
            "ai_enabled": False,
        },
        "ai_integration_shell": ai_status,
        "final_aas_acceptance": {
            "status": "passed" if all(row["passed"] for row in acceptance_checks) else "failed",
            "passed": sum(1 for row in acceptance_checks if row["passed"]),
            "failed": sum(1 for row in acceptance_checks if not row["passed"]),
            "checks": acceptance_checks,
        },
        "guards": {
            "allows_runtime_mutation": False,
            "allows_reboot": False,
            "allows_registry_mutation": False,
            "allows_provider_policy_mutation": False,
            "allows_ai_activation": False,
            "allows_module_registration": False,
            "allows_heart_mutation": False,
            "allows_bus_mutation": False,
            "allows_socket_mutation": False,
            "product_features_added": False,
            "new_engines_added": False,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "allowed_frontend_port": 5194,
            "allowed_api_port": 8794,
        },
    }
