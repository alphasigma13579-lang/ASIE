from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REGISTRY_PATH = ROOT / "registry" / "asie-canonical-terminology.v1.json"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from aas_registry import default_contracts, default_modules, default_sockets  # noqa: E402

LOWER_DOTTED_CONTRACT = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\.v[1-9][0-9]*$")
LOWER_DOTTED_SOCKET = re.compile(r"^socket\.[a-z0-9_]+(?:\.[a-z0-9_]+)+$")
MODULE_ID_PATTERN = re.compile(r"^(?:aas|module)\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")


class AuditFailure(AssertionError):
    pass


def _load_register() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AuditFailure("terminology register root must be an object")
    return value


def _assert_unique(values: list[str], label: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise AuditFailure(f"duplicate {label}: {', '.join(duplicates)}")


def run_audit() -> dict[str, int]:
    register = _load_register()

    contracts = list(default_contracts())
    sockets = list(default_sockets())
    modules = list(default_modules())

    live_contract_ids = [item.contract_id for item in contracts]
    live_socket_ids = [item.socket_id for item in sockets]
    live_module_ids = [item.module_id for item in modules]

    declared_contract_ids = register.get("registered_contract_ids", [])
    declared_socket_ids = register.get("registered_socket_ids", [])
    declared_module_ids = register.get("registered_module_ids", [])

    if set(live_contract_ids) != set(declared_contract_ids):
        missing = sorted(set(live_contract_ids) - set(declared_contract_ids))
        stale = sorted(set(declared_contract_ids) - set(live_contract_ids))
        raise AuditFailure(f"contract registry mismatch; missing={missing}; stale={stale}")
    if set(live_socket_ids) != set(declared_socket_ids):
        missing = sorted(set(live_socket_ids) - set(declared_socket_ids))
        stale = sorted(set(declared_socket_ids) - set(live_socket_ids))
        raise AuditFailure(f"socket registry mismatch; missing={missing}; stale={stale}")
    if set(live_module_ids) != set(declared_module_ids):
        missing = sorted(set(live_module_ids) - set(declared_module_ids))
        stale = sorted(set(declared_module_ids) - set(live_module_ids))
        raise AuditFailure(f"module registry mismatch; missing={missing}; stale={stale}")

    _assert_unique(live_contract_ids, "contract ids")
    _assert_unique(live_socket_ids, "socket ids")
    _assert_unique(live_module_ids, "module ids")

    legacy_ids = {
        item["identifier"]
        for item in register.get("legacy_frozen_identifiers", [])
        if item.get("kind") == "contract_id"
    }
    malformed_contracts = sorted(
        contract_id
        for contract_id in live_contract_ids
        if contract_id not in legacy_ids and not LOWER_DOTTED_CONTRACT.fullmatch(contract_id)
    )
    if malformed_contracts:
        raise AuditFailure(f"non-canonical contract ids: {', '.join(malformed_contracts)}")

    malformed_sockets = sorted(
        socket_id for socket_id in live_socket_ids if not LOWER_DOTTED_SOCKET.fullmatch(socket_id)
    )
    if malformed_sockets:
        raise AuditFailure(f"non-canonical socket ids: {', '.join(malformed_sockets)}")

    malformed_modules = sorted(
        module_id for module_id in live_module_ids if not MODULE_ID_PATTERN.fullmatch(module_id)
    )
    if malformed_modules:
        raise AuditFailure(f"non-canonical module ids: {', '.join(malformed_modules)}")

    contract_set = set(live_contract_ids)
    socket_set = set(live_socket_ids)
    module_set = set(live_module_ids)

    for socket in sockets:
        if socket.contract_id not in contract_set:
            raise AuditFailure(f"socket {socket.socket_id} references unknown contract {socket.contract_id}")
        if socket.provider_module_id not in module_set:
            raise AuditFailure(
                f"socket {socket.socket_id} references unknown provider module {socket.provider_module_id}"
            )
        unknown_consumers = sorted(set(socket.consumer_module_ids) - module_set)
        if unknown_consumers:
            raise AuditFailure(
                f"socket {socket.socket_id} references unknown consumer modules {unknown_consumers}"
            )

    for module in modules:
        unknown_sockets = sorted(set(module.provides + module.requires) - socket_set)
        if unknown_sockets:
            raise AuditFailure(f"module {module.module_id} references unknown sockets {unknown_sockets}")

    concepts = register.get("concepts", [])
    concept_ids = [item["concept_id"] for item in concepts]
    canonical_names = [item["canonical_name"] for item in concepts]
    _assert_unique(concept_ids, "concept ids")
    _assert_unique(canonical_names, "canonical names")

    for concept in concepts:
        runtime_module_id = concept.get("runtime_module_id")
        if runtime_module_id and runtime_module_id not in module_set:
            raise AuditFailure(
                f"concept {concept['concept_id']} references unknown module {runtime_module_id}"
            )
        for field_name in ("command_contract", "result_contract", "advisory_contract"):
            contract_id = concept.get(field_name)
            if contract_id and contract_id not in contract_set:
                raise AuditFailure(
                    f"concept {concept['concept_id']} references unknown {field_name} {contract_id}"
                )
        socket_id = concept.get("socket_id")
        if socket_id and socket_id not in socket_set:
            raise AuditFailure(f"concept {concept['concept_id']} references unknown socket {socket_id}")

    return {
        "contracts": len(live_contract_ids),
        "sockets": len(live_socket_ids),
        "modules": len(live_module_ids),
        "concepts": len(concepts),
        "legacy_frozen_identifiers": len(legacy_ids),
    }


def main() -> int:
    try:
        counts = run_audit()
    except (AuditFailure, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"CANONICAL TERMINOLOGY AUDIT: FAIL\n{exc}", file=sys.stderr)
        return 1

    print("CANONICAL TERMINOLOGY AUDIT: PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
