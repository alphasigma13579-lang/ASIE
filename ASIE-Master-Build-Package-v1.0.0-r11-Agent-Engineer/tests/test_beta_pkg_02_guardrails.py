from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "aas_kernel.py",
    "aas_registry.py",
    "heart_controller.py",
    "bus_controller.py",
    "system_bus.py",
    "socket_contracts.py",
    "module_runtime.py",
    "project_run_workflow.py",
    "snapshot_assembly.py",
    "runtime_freeze.py",
}


def test_product_interview_package_files_exist():
    assert (ROOT / "backend" / "product_ai_interview.py").is_file()
    assert (ROOT / "src" / "ProductAIInterview.tsx").is_file()
    assert (ROOT / "docs" / "BETA-PKG-02-PRODUCT-AI-INTERVIEW-2026-07-27.md").is_file()


def test_interview_engine_does_not_import_finance_or_provider_clients():
    source = (ROOT / "backend" / "product_ai_interview.py").read_text(encoding="utf-8")
    assert "finance_engine" not in source
    assert "live_provider_clients" not in source
    assert "DeepSeekNarrativeClient" not in source
    assert '"ai_owns_numbers": False' in source
    assert '"controlled_numbers_generated_by_ai": False' in source


def test_interview_package_does_not_modify_frozen_runtime_by_import():
    source = (ROOT / "backend" / "product_ai_interview.py").read_text(encoding="utf-8")
    for filename in FROZEN:
        module_name = filename.removesuffix(".py")
        assert f"backend.{module_name}" not in source


def test_ui_discloses_human_approval_boundary():
    source = (ROOT / "src" / "ProductAIInterview.tsx").read_text(encoding="utf-8")
    assert "لا يعتمد سند أي رقم مالي نيابةً عنك" in source
    assert "Approved Input Manifest" in source
