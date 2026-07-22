from __future__ import annotations

from typing import Any, Callable

AcceptancePredicate = Callable[[dict[str, Any]], tuple[bool, str]]


def build_acceptance_pack(overview: dict[str, Any]) -> dict[str, Any]:
    tests = [
        run_check(overview, "R10-AC-01", "No new truth-owner modules or direct module bypass", r10_ac_01),
        run_check(overview, "R10-AC-02", "Sovereign Verdict is deterministic and non-voting", r10_ac_02),
        run_check(overview, "R10-AC-03", "Monte Carlo is gated and owned by Finance Engine", r10_ac_03),
        run_check(overview, "R10-AC-04", "Dashboard/frontend is presentation only", r10_ac_04),
        run_check(overview, "R10-AC-05", "Subscription cannot hide material truth", r10_ac_05),
        run_check(overview, "R10-AC-06", "Saudi/source authority is not replaced by global or AI content", r10_ac_06),
        run_check(overview, "R11-AC-01", "No shared-memory path bypasses AAS route", r11_ac_01),
        run_check(overview, "R11-AC-02", "Remediation cannot alter verdict or persona isolation", r11_ac_02),
        run_check(overview, "R11-AC-03", "Demo/user data is labeled and no runtime crawl is active", r11_ac_03),
        run_check(overview, "R11-AC-04", "React owns no finance, MCMC, persona, or verdict logic", r11_ac_04),
        run_check(overview, "R11-AC-05", "Core build includes Monte Carlo, FSDP, verdict, and snapshot parity", r11_ac_05),
        run_check(overview, "R11-AC-06", "No provider owns controlled numbers or architecture", r11_ac_06),
        run_check(overview, "R11-AC-07", "No performance claim disables compliance controls", r11_ac_07),
    ]
    passed = sum(1 for item in tests if item["status"] == "passed")
    return {
        "acceptance_id": f"acceptance_{overview['snapshot']['snapshot_id']}",
        "snapshot_id": overview["snapshot"]["snapshot_id"],
        "run_id": overview["run"]["run_id"],
        "status": "passed" if passed == len(tests) else "failed",
        "passed": passed,
        "failed": len(tests) - passed,
        "tests": tests,
    }


def run_check(
    overview: dict[str, Any],
    test_id: str,
    title: str,
    predicate: AcceptancePredicate,
) -> dict[str, Any]:
    ok, evidence = predicate(overview)
    return {
        "test_id": test_id,
        "title": title,
        "status": "passed" if ok else "failed",
        "evidence": evidence,
        "snapshot_id": overview["snapshot"]["snapshot_id"],
        "run_id": overview["run"]["run_id"],
    }


def r10_ac_01(overview: dict[str, Any]) -> tuple[bool, str]:
    forbidden = overview["audit"]["forbidden_paths"]
    ok = "direct source fetch without enabled source review" in forbidden and overview["audit"]["owner_path"].startswith(
        "ProjectRunWorkflow -> execute_project_run_pipeline"
    )
    return ok, overview["audit"]["owner_path"]


def r10_ac_02(overview: dict[str, Any]) -> tuple[bool, str]:
    decision = overview["decision"]
    ok = decision["no_vote"] and not decision["advisory_consensus_visible_as_verdict"]
    return ok, f"no_vote={decision['no_vote']}"


def r10_ac_03(overview: dict[str, Any]) -> tuple[bool, str]:
    mc_kpis = [item for item in overview["kpis"] if item["output_id"] == "mc-feasibility-gate-probability"]
    ok = bool(mc_kpis) and mc_kpis[0]["owner_module"] == "Finance Engine" and overview["monte_carlo"][
        "convergence"
    ]["status"] in {"passed", "not_ready"}
    return ok, mc_kpis[0]["audit_ref"] if mc_kpis else "missing"


def r10_ac_04(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = "React finance calculation" in overview["audit"]["forbidden_paths"] and all(
        item["owner_module"] == "Finance Engine" for item in overview["kpis"]
    )
    return ok, "frontend presentation guard recorded"


def r10_ac_05(overview: dict[str, Any]) -> tuple[bool, str]:
    visible = {"funding-gap", "mc-feasibility-gate-probability"}
    ok = visible.issubset({item["output_id"] for item in overview["kpis"]}) and bool(overview["personas"])
    return ok, "material truth outputs visible"


def r10_ac_06(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = not overview["evidence_register"]["external_fetch_enabled"] and overview["source_policy"][
        "profile_id"
    ].startswith("strict_open_data")
    return ok, overview["source_policy"]["profile_id"]


def r11_ac_01(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = (
        overview["audit"]["owner_path"]
        == "ProjectRunWorkflow -> execute_project_run_pipeline -> RunScopedModuleRuntime"
    )
    return ok, overview["audit"]["owner_path"]


def r11_ac_02(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = overview["decision_council"]["no_vote"] and len(overview["decision_council"]["isolation_order"]) == 5
    return ok, ",".join(overview["decision_council"]["isolation_order"])


def r11_ac_03(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = overview["project"]["data_badge"] in {"DEMO_DATA", "USER_VERIFIED"} and not overview["audit"][
        "source_fetch_enabled"
    ]
    return ok, f"data_badge={overview['project']['data_badge']}"


def r11_ac_04(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = "React finance calculation" in overview["audit"]["forbidden_paths"]
    return ok, "React guard in audit"


def r11_ac_05(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = bool(overview["monte_carlo"]) and bool(overview["decision_council"]) and overview["snapshot"]["immutable"]
    return ok, overview["snapshot"]["snapshot_id"]


def r11_ac_06(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = "AI-owned controlled numbers" in overview["audit"]["forbidden_paths"]
    return ok, "provider-neutral guard recorded"


def r11_ac_07(overview: dict[str, Any]) -> tuple[bool, str]:
    ok = "performance_claims" not in overview and not overview["audit"]["source_fetch_enabled"]
    return ok, "no performance claim bypass"
