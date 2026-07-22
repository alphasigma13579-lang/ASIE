from __future__ import annotations

from copy import deepcopy
from typing import Any


AAS_RUNTIME_FREEZE_VERSION = "1.0"
AAS_RUNTIME_FREEZE_STATUS = "frozen"
BUILD_OVERVIEW_REMOVAL_TARGET = "AAS Runtime v1.1"
ARCHITECTURAL_CHANGE_REQUEST_REQUIRED = True
FROZEN_RUNTIME_COMPONENTS = (
    "kernel",
    "registry",
    "heart_controller",
    "hearts.M1.M2.M3",
    "bus_controller",
    "system_bus",
    "socket_contract_layer",
    "module_runtime",
    "project_run_pipeline_contract_sequence",
    "snapshot_assembly_boundary",
)


def runtime_freeze_status() -> dict[str, Any]:
    return deepcopy(
        {
            "name": "AAS Runtime Freeze",
            "version": AAS_RUNTIME_FREEZE_VERSION,
            "status": AAS_RUNTIME_FREEZE_STATUS,
            "effective_date": "2026-07-19",
            "architectural_change_request_required": ARCHITECTURAL_CHANGE_REQUEST_REQUIRED,
            "frozen_components": list(FROZEN_RUNTIME_COMPONENTS),
            "legacy_compatibility": {
                "build_overview_status": "deprecated_parity_tests_only",
                "production_reachable": False,
                "removal_target": BUILD_OVERVIEW_REMOVAL_TARGET,
            },
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
        }
    )

