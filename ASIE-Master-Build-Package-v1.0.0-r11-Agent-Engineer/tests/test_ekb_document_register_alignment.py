"""Keep active AIA-02 agent pointers aligned with the adopted document register."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EKB = DOCS / "EKB"
TICK = chr(96)


def _aia02_errors(map_text: str, inventory_text: str, register: dict) -> list[str]:
    canonical = next(
        item for item in register["canonical_documents"] if item["document_id"] == "AIA-02"
    )
    path = canonical["path"]
    status = canonical["status"]
    map_rows = [line for line in map_text.splitlines() if "docs/AIA-02-" in line]
    inventory_rows = [
        line for line in inventory_text.splitlines() if line.startswith("| DOC-AIA-02 |")
    ]
    errors: list[str] = []
    if len(map_rows) != 1 or f"{TICK}{path}{TICK}" not in map_rows[0]:
        errors.append("ekb_map_aia02_path")
    if len(map_rows) != 1 or f"{TICK}{status}{TICK}" not in map_rows[0]:
        errors.append("ekb_map_aia02_status")
    inventory_path = f"ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/{path}"
    if len(inventory_rows) != 1 or f"{TICK}{inventory_path}{TICK}" not in inventory_rows[0]:
        errors.append("ekb_inventory_aia02_path")
    if len(inventory_rows) != 1 or f"{TICK}{status}{TICK}" not in inventory_rows[0]:
        errors.append("ekb_inventory_aia02_status")
    return errors


def test_active_aia02_references_match_register_and_exist():
    register = json.loads((DOCS / "ASIE-CANONICAL-DOCUMENT-REGISTER-v1.2.0.json").read_text(encoding="utf-8"))
    map_text = (EKB / "EKB-00-Knowledge-Map.md").read_text(encoding="utf-8")
    inventory_text = (EKB / "EKB-01-Verified-Document-Inventory.md").read_text(encoding="utf-8")
    assert _aia02_errors(map_text, inventory_text, register) == []
    path = next(item["path"] for item in register["canonical_documents"] if item["document_id"] == "AIA-02")
    assert (ROOT / path).is_file()


def test_validator_rejects_stale_path_and_adoption_state():
    register = json.loads((DOCS / "ASIE-CANONICAL-DOCUMENT-REGISTER-v1.2.0.json").read_text(encoding="utf-8"))
    map_text = (EKB / "EKB-00-Knowledge-Map.md").read_text(encoding="utf-8")
    inventory_text = (EKB / "EKB-01-Verified-Document-Inventory.md").read_text(encoding="utf-8")
    stale_path = "docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1-Candidate.md"
    adopted_path = "docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md"
    stale_map = map_text.replace(adopted_path, stale_path).replace(
        "FINAL_ADOPTED_CONTROLLED_BASELINE", "CANDIDATE_FOR_FINAL_REVIEW"
    )
    stale_inventory = inventory_text.replace(adopted_path, stale_path).replace(
        "FINAL_ADOPTED_CONTROLLED_BASELINE", "CANDIDATE_FOR_FINAL_REVIEW"
    )
    assert set(_aia02_errors(stale_map, stale_inventory, register)) == {
        "ekb_map_aia02_path",
        "ekb_map_aia02_status",
        "ekb_inventory_aia02_path",
        "ekb_inventory_aia02_status",
    }


def test_entry_links_point_to_saved_plan_and_audit():
    entry = (EKB / "README-AR.md").read_text(encoding="utf-8")
    for name in (
        "ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md",
        "ASIE-AIA-PARALLEL-ROUTING-AUDIT-2026-09-23.md",
    ):
        assert f"../{name}" in entry
        assert (DOCS / name).is_file()
    package_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/ASIE-CANONICAL-DOCUMENT-REGISTER-v1.2.0.json" in package_readme
    assert "docs/ASIE-CANONICAL-DOCUMENT-REGISTER-v1.1.0.json" not in package_readme
