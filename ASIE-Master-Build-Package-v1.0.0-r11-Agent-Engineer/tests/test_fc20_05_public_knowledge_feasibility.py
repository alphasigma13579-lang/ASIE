from __future__ import annotations

from types import SimpleNamespace

from backend.public_knowledge import (
    PublicKnowledgeError,
    build_feasibility_evidence_context,
    validate_public_source_registry,
)


def hit_fields(**overrides):
    fields = {
        "chunk_text": "Official evidence about Saudi economic conditions.",
        "source_id": "mof-open-data",
        "publisher": "Ministry of Finance",
        "authority": "saudi_official",
        "source_url": "https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
        "license_id": "saudi-open-data-license-2.0",
        "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
        "attribution": "Ministry of Finance",
        "sector": "all",
        "geography": "saudi_arabia",
        "language": "en",
        "published_at": "unknown",
        "retrieved_at": "2026-08-20T00:00:00Z",
        "content_sha256": "a" * 64,
        "version": 2,
        "freshness_days": 31,
        "fresh_until": "2026-09-20T00:00:00Z",
        "expires_at": "2026-10-20T00:00:00Z",
        "unit": "not_applicable",
        "confidence": 0.95,
        "evidence_ref": "public:mof-open-data:sha256:" + "a" * 64,
        "admission_status": "auto_admitted_official_open",
        "data_classification": "public",
    }
    fields.update(overrides)
    return fields


def test_context_exposes_evidence_and_never_claims_success_or_funding() -> None:
    response = {
        "payload": {
            "result": {
                "hits": [{"_id": "public-mof-0001", "_score": 0.91, "fields": hit_fields()}]
            }
        }
    }
    context = build_feasibility_evidence_context(response, as_of="2026-08-23T00:00:00Z")
    assert context["status"] == "ready"
    assert context["evidence"][0]["source_id"] == "mof-open-data"
    assert context["evidence"][0]["confidence"] == 0.95
    assert "market_size" in context["permitted_uses"]
    assert context["claims_project_success"] is False
    assert context["claims_funding_acceptance"] is False
    assert context["source_of_truth"] is False


def test_missing_unit_or_expired_evidence_abstains() -> None:
    response = {
        "payload": {
            "result": {
                "hits": [
                    {"_id": "missing-unit", "_score": 0.9, "fields": hit_fields(unit="")},
                    {
                        "_id": "expired",
                        "_score": 0.8,
                        "fields": hit_fields(expires_at="2026-08-01T00:00:00Z"),
                    },
                ]
            }
        }
    }
    context = build_feasibility_evidence_context(response, as_of="2026-08-23T00:00:00Z")
    assert context["status"] == "not_ready"
    assert context["evidence"] == []
    assert {gap["reason"] for gap in context["gaps"]} == {"evidence_unit_missing", "evidence_expired"}


def test_malformed_retrieval_metadata_is_a_gap_not_an_exception() -> None:
    response = {
        "payload": {
            "result": {
                "hits": [
                    {
                        "_id": "poisoned-fields",
                        "_score": 0.7,
                        "fields": hit_fields(source_url={"unexpected": "object"}),
                    }
                ]
            }
        }
    }
    context = build_feasibility_evidence_context(response, as_of="2026-08-23T00:00:00Z")
    assert context["status"] == "not_ready"
    assert context["gaps"] == [
        {"record_id": "poisoned-fields", "reason": "evidence_metadata_incomplete"}
    ]


def test_tampered_lineage_or_freshness_is_rejected() -> None:
    response = {
        "payload": {
            "result": {
                "hits": [
                    {
                        "_id": "bad-lineage",
                        "_score": 0.9,
                        "fields": hit_fields(evidence_ref="public:other:sha256:" + "b" * 64),
                    },
                    {
                        "_id": "bad-freshness",
                        "_score": 0.8,
                        "fields": hit_fields(fresh_until="2027-09-20T00:00:00Z"),
                    },
                ]
            }
        }
    }
    context = build_feasibility_evidence_context(response, as_of="2026-08-23T00:00:00Z")
    assert context["status"] == "not_ready"
    assert {gap["reason"] for gap in context["gaps"]} == {
        "evidence_lineage_invalid",
        "evidence_temporal_invalid",
    }


def test_unsafe_license_reference_is_rejected_at_ingress_and_retrieval() -> None:
    source = {
        "source_id": "mof-open-data",
        "publisher": "Ministry of Finance",
        "authority": "saudi_official",
        "url": "https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
        "state": "enabled",
        "admission_mode": "official_open_auto",
        "license_id": "saudi-open-data-license-2.0",
        "license_ref": "javascript:alert(1)",
        "attribution": "Ministry of Finance",
        "classification": "public_open_data",
        "geographies": ["saudi_arabia"],
        "sectors": ["all"],
        "language": "en",
        "freshness_days": 31,
        "expiry_days": 62,
        "unit": "not_applicable",
        "confidence": 0.95,
        "allowed_paths": ["/en/generalservcies/open-data"],
        "allow_query_parameters": False,
    }
    try:
        validate_public_source_registry({"schema_version": 1, "sources": [source]})
    except PublicKnowledgeError as exc:
        assert str(exc) == "public_source_license_ref_invalid"
    else:
        raise AssertionError("unsafe license references must be denied before ingestion")

    response = {
        "payload": {
            "result": {
                "hits": [
                    {
                        "_id": "unsafe-license",
                        "_score": 0.7,
                        "fields": hit_fields(license_ref="javascript:alert(1)"),
                    }
                ]
            }
        }
    }
    context = build_feasibility_evidence_context(response, as_of="2026-08-23T00:00:00Z")
    assert context["status"] == "not_ready"
    assert context["gaps"] == [
        {"record_id": "unsafe-license", "reason": "evidence_metadata_invalid"}
    ]


def test_public_knowledge_module_has_no_frozen_runtime_dependency() -> None:
    import backend.public_knowledge as module

    source = open(module.__file__, encoding="utf-8").read()
    for forbidden in (
        "aas_kernel",
        "ProjectRunWorkflow",
        "SnapshotAssembly",
        "FinanceEngine",
        "DecisionCouncil",
    ):
        assert forbidden not in source
