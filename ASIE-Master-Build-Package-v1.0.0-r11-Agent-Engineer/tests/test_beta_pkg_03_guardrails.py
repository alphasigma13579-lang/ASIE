from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "backend" / "live_intelligence_product.py"
UI = ROOT / "src" / "LiveIntelligenceWorkspace.tsx"
DOC = ROOT / "docs" / "BETA-PKG-03-LIVE-INTELLIGENCE-PRODUCT-WIRING-2026-07-27.md"

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


def test_package_files_exist_and_do_not_replace_frozen_runtime():
    assert SERVICE.exists()
    assert UI.exists()
    assert SERVICE.name not in FROZEN


def test_product_wiring_document_uses_public_economic_corpus_contract():
    text = DOC.read_text(encoding="utf-8")
    assert "Governed public-economic corpus retrieval" in text
    assert "fixed shared corpus" in text
    assert "Vision 2030" not in text


def test_service_has_no_direct_finance_or_snapshot_import():
    text = SERVICE.read_text(encoding="utf-8")
    assert "from backend.finance_engine" not in text
    assert "from backend.snapshot_assembly" not in text
    assert "finance_result_set(" not in text
    assert "assemble_snapshot(" not in text


def test_provider_outputs_remain_review_required_and_non_sovereign():
    text = SERVICE.read_text(encoding="utf-8")
    assert '"human_review_required": True' in text
    assert '"eligible_for_controlled_assumptions": False' in text
    assert '"controlled_numbers": []' in text
    assert '"finance_mutated": False' in text
    assert '"snapshot_mutated": False' in text


def test_ui_discloses_review_and_live_status():
    text = UI.read_text(encoding="utf-8")
    assert "تحتاج مراجعة" in text
    assert "الاتصال الخارجي معطّل" in text
    assert "لا تُستخدم تلقائيًا كأرقام مالية" in text
    assert "الأدلة الاقتصادية العامة" in text
    assert "public_evidence_context" in text
    fields = (
        "publisher",
        "source_url",
        "geography",
        "sector",
        "unit",
        "confidence",
        "retrieved_at",
        "fresh_until",
    )
    for field in fields:
        assert field in text
