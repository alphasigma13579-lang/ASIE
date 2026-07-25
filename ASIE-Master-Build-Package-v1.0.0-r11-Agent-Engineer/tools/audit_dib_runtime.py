from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.dib_runtime_extension import dib_contracts, dib_modules, dib_sockets  # noqa: E402


class DIBAuditFailure(AssertionError):
    pass


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_audit() -> dict[str, int]:
    register = _load(ROOT / "registry" / "asie-dib-runtime.v1.json")
    contracts = [row.contract_id for row in dib_contracts()]
    sockets = [row.socket_id for row in dib_sockets()]
    modules = [row.module_id for row in dib_modules()]

    if set(contracts) != set(register["contracts"]):
        raise DIBAuditFailure("DIB contract inventory mismatch")
    if set(sockets) != set(register["sockets"]):
        raise DIBAuditFailure("DIB socket inventory mismatch")
    if set(modules) != {row["module_id"] for row in register["modules"]}:
        raise DIBAuditFailure("DIB module inventory mismatch")

    required_files = [
        "backend/dib_registry.py",
        "backend/dib_intake.py",
        "backend/input_manifest.py",
        "backend/dib_finance_gate.py",
        "backend/market_intelligence.py",
        "backend/dib_runtime_extension.py",
        "src/dibRegistry.ts",
        "src/dibApi.ts",
        "src/DIBWorkspace.tsx",
        "src/dib.css",
        "tests/test_input_manifest.py",
        "tests/test_dib_complete_runtime.py",
    ]
    missing = [path for path in required_files if not (ROOT / path).is_file()]
    if missing:
        raise DIBAuditFailure("DIB files missing: " + ", ".join(missing))

    source_checks = {
        "backend/intelligence_prerun_service.py": [
            "market.query.request.v1",
            "socket.market.query",
            "module.market_intelligence",
            "register_dib_runtime",
        ],
        "backend/datasets.py": [
            "application/pdf",
            "extract_pdf_text",
            "mapped_candidates",
        ],
        "backend/input_manifest.py": [
            "DynamicInputBlueprint",
            "ApprovedInputManifest",
            "INTENTIONAL_ZERO",
            "EXPERIMENTAL_ESTIMATE",
            "MARKET_EVIDENCE_PACK_INVALID",
        ],
        "backend/dib_finance_gate.py": [
            "finance_result_from_project_inputs",
            "approved_input_manifest",
        ],
        "src/DIBWorkspace.tsx": [
            "Product AI Interview",
            "Approved Input Manifest",
            "Manifest Validation Gate",
            "CSV / XLSX / PDF",
            "compareSnapshots",
        ],
        "src/main.tsx": ['window.location.hash === "#dib"'],
    }
    for relative, needles in source_checks.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        absent = [needle for needle in needles if needle not in text]
        if absent:
            raise DIBAuditFailure(f"{relative} is missing controls: {absent}")

    freeze = _load(ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json")
    changed = []
    for row in freeze["frozen_files"]:
        actual = hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest()
        if actual != row["sha256"]:
            changed.append(row["path"])
    if changed:
        raise DIBAuditFailure("Frozen AAS files changed: " + ", ".join(changed))

    return {
        "contracts": len(contracts),
        "sockets": len(sockets),
        "modules": len(modules),
        "required_files": len(required_files),
        "frozen_files_verified": len(freeze["frozen_files"]),
    }


def main() -> int:
    try:
        counts = run_audit()
    except (DIBAuditFailure, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"DIB COMPLETE RUNTIME AUDIT: FAIL\n{exc}", file=sys.stderr)
        return 1
    print("DIB COMPLETE RUNTIME AUDIT: PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
