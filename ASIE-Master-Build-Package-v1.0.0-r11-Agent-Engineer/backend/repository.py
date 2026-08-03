
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.contracts import DB_PATH, json_dumps, json_loads, new_id, now_iso
from backend.datasets import normalize_dataset_payload, normalize_evidence_link
from backend.decision_pack import normalize_action_item_patch, normalize_review
from backend.source_registry import normalize_source_review, seed_source_records
from backend.snapshot_assembly import canonical_hash
from backend.transformations import normalize_transformation_payload
from backend.identity import Principal, VALID_ROLES, hash_password, new_session_token, token_hash, verify_password
from backend.intelligence_authorization import authorize_intelligence_action
from backend.intelligence_context import idempotency_fingerprint


LEGACY_ORGANIZATION_ID = "org_local_legacy"


ASSUMPTION_META = {
    "startup_cost": ("تكلفة التأسيس", "SAR"),
    "monthly_fixed_cost": ("التكاليف الشهرية الثابتة", "SAR"),
    "unit_price": ("سعر الوحدة", "SAR"),
    "variable_cost": ("التكلفة المتغيرة للوحدة", "SAR"),
    "monthly_units": ("الوحدات الشهرية", "count"),
    "use_operating_capacity": ("استخدام نموذج الطاقة التشغيلية", "boolean"),
    "capacity_units_per_day": ("الطاقة اليومية", "count/day"),
    "operating_days_per_month": ("أيام التشغيل الشهرية", "days"),
    "utilization_rate": ("نسبة الاستخدام", "percent"),
    "payroll_monthly": ("الرواتب الشهرية", "SAR"),
    "rent_monthly": ("الإيجار الشهري", "SAR"),
    "utilities_monthly": ("المرافق الشهرية", "SAR"),
    "marketing_monthly": ("التسويق الشهري", "SAR"),
    "maintenance_monthly": ("الصيانة الشهرية", "SAR"),
    "capex_equipment": ("CAPEX المعدات", "SAR"),
    "capex_fitout": ("CAPEX التجهيز", "SAR"),
    "capex_licenses_local": ("CAPEX تراخيص محلية", "SAR"),
    "depreciation_years": ("سنوات الإهلاك", "years"),
    "equity_contribution": ("مساهمة رأس المال", "SAR"),
    "loan_grace_months": ("أشهر سماح القرض", "months"),
    "annual_discount_rate": ("معدل الخصم السنوي", "percent"),
    "working_capital_months": ("أشهر رأس المال العامل", "months"),
    "debt_amount": ("مبلغ الدين", "SAR"),
    "annual_interest_rate": ("معدل الفائدة السنوي", "percent"),
    "loan_years": ("مدة القرض", "years"),
}


SYSTEM_CONTEXT_INPUT_KEYS = {
    "primary_sector_id",
    "activity_description",
    "location_scope",
    "location_country",
    "intake_mode",
}


def meaningful_assumption_value(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def derive_monthly_fixed_cost(inputs: dict[str, Any]) -> float:
    """Derive fixed monthly costs from the detailed monthly cost components."""
    component_keys = (
        "payroll_monthly",
        "rent_monthly",
        "utilities_monthly",
        "marketing_monthly",
        "maintenance_monthly",
    )
    components = []
    for key in component_keys:
        try:
            components.append(max(0.0, float(inputs.get(key, 0) or 0)))
        except (TypeError, ValueError):
            components.append(0.0)
    other_costs_total = 0.0
    for row in inputs.get("other_monthly_costs", []) or []:
        if isinstance(row, dict):
            try:
                other_costs_total += max(0.0, float(row.get("amount", 0) or 0))
            except (TypeError, ValueError):
                continue
    detailed_total = sum(components) + other_costs_total
    if detailed_total > 0:
        return detailed_total
    try:
        return max(0.0, float(inputs.get("monthly_fixed_cost", 0) or 0))
    except (TypeError, ValueError):
        return 0.0


def default_assumption_records(project: "ProjectRecord") -> dict[str, dict[str, Any]]:
    """Build the human-review manifest from values the user actually supplied.

    Empty, zero, disabled, and system-context fields are intentionally excluded.
    They must never appear as user assumptions merely because the frontend schema
    carries safe defaults for them.
    """
    rows: dict[str, dict[str, Any]] = {}
    for key, value in project.inputs.items():
        if key in SYSTEM_CONTEXT_INPUT_KEYS or not meaningful_assumption_value(value):
            continue
        label, unit = ASSUMPTION_META.get(key, (key, "unit"))
        rows[key] = {
            "input_key": key,
            "label": label,
            "value": value,
            "unit": unit,
            "owner": "Project Wizard",
            "source_type": "user_input",
            "confidence": 0.65,
            "review_status": "draft",
        }
    return rows

@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    sector: str
    jurisdiction: str
    depth_profile: str
    inputs: dict[str, Any]
    created_at: str
    updated_at: str
    organization_id: str = LEGACY_ORGANIZATION_ID

    def to_public(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "sector": self.sector,
            "jurisdiction": self.jurisdiction,
            "depth_profile": self.depth_profile,
            "inputs": self.inputs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organization_id": self.organization_id,
        }


class Repository:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # B2-2: WAL lets readers proceed during a single writer and busy_timeout
        # makes concurrent writers queue instead of failing with
        # "database is locked" under beta load. journal_mode persists on the
        # database file, so setting it on every connection is idempotent.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def init_schema(self) -> None:
        with closing(self.connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    depth_profile TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    platform_role TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS organizations (
                    organization_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memberships (
                    membership_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    invited_at TEXT,
                    accepted_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, organization_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id)
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS password_recovery_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS security_audit_events (
                    event_id TEXT PRIMARY KEY,
                    actor_user_id TEXT,
                    organization_id TEXT,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    result TEXT NOT NULL,
                    reason TEXT,
                    correlation_id TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS platform_incidents (
                    incident_id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    snapshot_id TEXT,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id)
                );
                CREATE TABLE IF NOT EXISTS organization_data_requests (
                    request_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by_user_id TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(requested_by_user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS organization_entitlements (
                    organization_id TEXT PRIMARY KEY,
                    plan_code TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL,
                    quota_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id)
                );
                CREATE TABLE IF NOT EXISTS usage_meters (
                    usage_meter_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    metric_code TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(organization_id, metric_code, period_start, period_end)
                );
                CREATE TABLE IF NOT EXISTS local_invoices (
                    invoice_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS subscription_change_events (
                    event_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    previous_plan_code TEXT NOT NULL,
                    previous_lifecycle_status TEXT NOT NULL,
                    plan_code TEXT NOT NULL,
                    lifecycle_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id)
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    recipient_user_id TEXT,
                    template_id TEXT NOT NULL,
                    delivery_status TEXT NOT NULL,
                    reference_type TEXT NOT NULL,
                    reference_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(recipient_user_id) REFERENCES users(user_id)
                );
                CREATE TABLE IF NOT EXISTS support_threads (
                    support_thread_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    snapshot_id TEXT,
                    status TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(snapshot_id) REFERENCES snapshots(snapshot_id),
                    FOREIGN KEY(created_by_user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    audit_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    overview_json TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS source_records (
                    source_id TEXT PRIMARY KEY,
                    publisher TEXT NOT NULL,
                    route TEXT NOT NULL,
                    state TEXT NOT NULL,
                    url TEXT NOT NULL,
                    terms_url TEXT,
                    terms_hash TEXT,
                    license_snapshot_ref TEXT,
                    attribution TEXT,
                    classification TEXT,
                    pdpl_check TEXT,
                    nca_check TEXT,
                    lawful_purpose TEXT,
                    reviewer TEXT,
                    reviewer_decision TEXT,
                    reviewed_at TEXT,
                    notes_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS intelligence_contexts (
                    context_build_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    idempotency_fingerprint TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE TABLE IF NOT EXISTS intelligence_review_overlays (
                    review_overlay_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    context_build_id TEXT NOT NULL,
                    overlay_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(context_build_id) REFERENCES intelligence_contexts(context_build_id)
                );
                CREATE TABLE IF NOT EXISTS intelligence_approval_receipts (
                    approval_receipt_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    context_build_id TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(context_build_id) REFERENCES intelligence_contexts(context_build_id)
                );
                CREATE INDEX IF NOT EXISTS idx_intelligence_context_tenant
                    ON intelligence_contexts(organization_id, project_id);
                CREATE TABLE IF NOT EXISTS intelligence_market_records (
                    record_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, project_id TEXT NOT NULL,
                    record_type TEXT NOT NULL, record_hash TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id), FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE TABLE IF NOT EXISTS intelligence_synthesis_packs (
                    pack_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, project_id TEXT NOT NULL,
                    context_hash TEXT NOT NULL, pack_hash TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(organization_id) REFERENCES organizations(organization_id), FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS assumptions (
                    assumption_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    input_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    owner TEXT NOT NULL,
            …13788 tokens truncated…["context_hash"], "state": row["state"]}

    def update_intelligence_context(self, *, context_build_id: str, organization_id: str, project_id: str, payload: dict[str, Any], expected_version: int, principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="project.edit", action="aia.context.update", target_id=context_build_id, correlation_id=correlation_id)
        updated = dict(payload) | {"context_build_id": context_build_id, "organization_id": organization_id, "project_id": project_id, "updated_at": now_iso()}
        with closing(self.connect()) as conn:
            result = conn.execute("UPDATE intelligence_contexts SET context_hash = ?, state = ?, version = version + 1, payload_json = ?, updated_at = ? WHERE context_build_id = ? AND organization_id = ? AND project_id = ? AND version = ?", (str(updated.get("context_hash") or ""), str(updated.get("state") or "DRAFT"), json_dumps(updated), updated["updated_at"], context_build_id, organization_id, project_id, expected_version))
            if result.rowcount != 1:
                raise RuntimeError("context_optimistic_version_conflict")
            conn.commit()
        return updated | {"version": expected_version + 1}

    def save_intelligence_review(self, *, organization_id: str, project_id: str, overlay: dict[str, Any], principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        overlay_id = str(overlay.get("review_overlay_id") or new_id("review"))
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="review.write", action="aia.review.save", target_id=overlay_id, correlation_id=correlation_id)
        record = dict(overlay) | {"review_overlay_id": overlay_id, "created_at": now_iso()}
        with closing(self.connect()) as conn:
            context = conn.execute("SELECT context_hash FROM intelligence_contexts WHERE context_build_id = ? AND organization_id = ? AND project_id = ?", (str(record.get("intelligence_context_id") or ""), organization_id, project_id)).fetchone()
            if context is None or str(record.get("intelligence_context_hash") or "") != context["context_hash"]:
                raise ValueError("review_context_hash_mismatch")
            conn.execute("INSERT INTO intelligence_review_overlays (review_overlay_id, organization_id, project_id, context_build_id, overlay_hash, payload_json, created_at) VALUES (?,?,?,?,?,?,?)", (overlay_id, organization_id, project_id, str(record.get("intelligence_context_id") or ""), str(record.get("review_overlay_hash") or ""), json_dumps(record), record["created_at"]))
            conn.commit()
        return record

    def save_intelligence_approval(self, *, organization_id: str, project_id: str, receipt: dict[str, Any], principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        receipt_id = str(receipt.get("approval_receipt_id") or new_id("receipt"))
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="review.write", action="aia.approval.save", target_id=receipt_id, correlation_id=correlation_id)
        record = dict(receipt) | {"approval_receipt_id": receipt_id, "created_at": now_iso()}
        with closing(self.connect()) as conn:
            context = conn.execute("SELECT context_hash FROM intelligence_contexts WHERE context_build_id = ? AND organization_id = ? AND project_id = ?", (str(record.get("intelligence_context_id") or ""), organization_id, project_id)).fetchone()
            overlay = conn.execute("SELECT overlay_hash FROM intelligence_review_overlays WHERE review_overlay_id = ? AND organization_id = ? AND project_id = ?", (str(record.get("review_overlay_id") or ""), organization_id, project_id)).fetchone()
            if context is None or overlay is None or str(record.get("intelligence_context_hash") or "") != context["context_hash"] or str(record.get("review_overlay_hash") or "") != overlay["overlay_hash"]:
                raise ValueError("approval_reference_mismatch")
            conn.execute("INSERT INTO intelligence_approval_receipts (approval_receipt_id, organization_id, project_id, context_build_id, receipt_hash, payload_json, created_at) VALUES (?,?,?,?,?,?,?)", (receipt_id, organization_id, project_id, str(record.get("intelligence_context_id") or ""), str(record.get("approval_receipt_hash") or ""), json_dumps(record), record["created_at"]))
            conn.commit()
        return record

    def save_intelligence_market_record(self, *, organization_id: str, project_id: str, record: dict[str, Any], principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        record_id = str(record.get("record_id") or new_id("market"))
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="project.edit", action="aia.market.save", target_id=record_id, correlation_id=correlation_id)
        payload = dict(record) | {"record_id": record_id, "created_at": now_iso()}
        with closing(self.connect()) as conn:
            conn.execute("INSERT INTO intelligence_market_records (record_id, organization_id, project_id, record_type, record_hash, payload_json, created_at) VALUES (?,?,?,?,?,?,?)", (record_id, organization_id, project_id, str(payload.get("record_type") or "market_context"), str(payload.get("market_context_hash") or payload.get("assumption_hash") or ""), json_dumps(payload), payload["created_at"]))
            conn.commit()
        return payload

    def save_intelligence_synthesis_pack(self, *, organization_id: str, project_id: str, pack: dict[str, Any], principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        pack_id = str(pack.get("pack_id") or new_id("pack"))
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="project.edit", action="aia.synthesis.save", target_id=pack_id, correlation_id=correlation_id)
        if not pack.get("context_hash") or not pack.get("pack_hash"):
            raise ValueError("synthesis_hashes_required")
        payload = dict(pack) | {"pack_id": pack_id, "created_at": now_iso()}
        with closing(self.connect()) as conn:
            conn.execute("INSERT INTO intelligence_synthesis_packs (pack_id, organization_id, project_id, context_hash, pack_hash, payload_json, created_at) VALUES (?,?,?,?,?,?,?)", (pack_id, organization_id, project_id, str(payload["context_hash"]), str(payload["pack_hash"]), json_dumps(payload), payload["created_at"]))
            conn.commit()
        return payload

    def get_intelligence_synthesis_pack(self, *, pack_id: str, organization_id: str, project_id: str, principal: Principal | None) -> dict[str, Any] | None:
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="snapshot.read", action="aia.synthesis.read", target_id=pack_id)
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT payload_json FROM intelligence_synthesis_packs WHERE pack_id = ? AND organization_id = ? AND project_id = ?", (pack_id, organization_id, project_id)).fetchone()
        return None if row is None else json_loads(row["payload_json"], {})

    def consume_intelligence_approval(self, *, receipt_id: str, organization_id: str, project_id: str, context_hash: str, contract_version: str, principal: Principal | None) -> dict[str, Any]:
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="project.run", action="aia.approval.consume", target_id=receipt_id)
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT payload_json FROM intelligence_approval_receipts WHERE approval_receipt_id = ? AND organization_id = ? AND project_id = ?", (receipt_id, organization_id, project_id)).fetchone()
        if row is None:
            raise ValueError("approval_receipt_not_found")
        receipt = json_loads(row["payload_json"], {})
        if receipt.get("intelligence_context_hash") != context_hash or receipt.get("approved_for_contract_version") != contract_version:
            raise ValueError("approval_receipt_contract_or_hash_mismatch")
        return {"approval_receipt_id": receipt_id, "organization_id": organization_id, "project_id": project_id, "context_hash": context_hash, "contract_version": contract_version, "consumable": True, "snapshot_mutation": False}

    def datasets(self, organization_id: str | None = None) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            if organization_id:
                rows = conn.execute("SELECT * FROM datasets WHERE organization_id = ? ORDER BY updated_at DESC", (organization_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM datasets ORDER BY updated_at DESC").fetchall()
        return [self._dataset_from_row(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
        return None if row is None else self._dataset_from_row(row)

    def save_dataset(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_dataset(str(payload.get("dataset_id") or ""))
        record = normalize_dataset_payload(payload, existing)
        record["organization_id"] = str(payload.get("organization_id") or (existing or {}).get("organization_id") or LEGACY_ORGANIZATION_ID)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    dataset_id, organization_id, source_id, title, publisher, import_method, review_status,
                    human_review_decision, license_snapshot_ref, terms_hash, classification,
                    pdpl_check, attribution, row_count, columns_json, preview_json, notes_json,
                    created_at, updated_at
                ) VALUES (
                    :dataset_id, :organization_id, :source_id, :title, :publisher, :import_method, :review_status,
                    :human_review_decision, :license_snapshot_ref, :terms_hash, :classification,
                    :pdpl_check, :attribution, :row_count, :columns_json, :preview_json, :notes_json,
                    :created_at, :updated_at
                )
                ON CONFLICT(dataset_id) DO UPDATE SET
                    organization_id = excluded.organization_id,
                    source_id = excluded.source_id,
                    title = excluded.title,
                    publisher = excluded.publisher,
                    import_method = excluded.import_method,
                    review_status = excluded.review_status,
                    human_review_decision = excluded.human_review_decision,
                    license_snapshot_ref = excluded.license_snapshot_ref,
                    terms_hash = excluded.terms_hash,
                    classification = excluded.classification,
                    pdpl_check = excluded.pdpl_check,
                    attribution = excluded.attribution,
                    row_count = excluded.row_count,
                    columns_json = excluded.columns_json,
                    preview_json = excluded.preview_json,
                    notes_json = excluded.notes_json,
                    updated_at = excluded.updated_at
                """,
                record,
            )
            conn.commit()
        saved = self.get_dataset(record["dataset_id"])
        if saved is None:
            raise RuntimeError("dataset_save_failed")
        return saved

    def review_dataset(self, dataset_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        existing = self.get_dataset(dataset_id)
        if existing is None:
            return None
        payload = payload | {"dataset_id": dataset_id}
        return self.save_dataset(payload)

    def save_transformation(self, dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            raise ValueError("dataset_not_found")
        existing = self.get_transformation(str(payload.get("transformation_id") or ""))
        record = normalize_transformation_payload(dataset, payload | {"dataset_id": dataset_id}, existing)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO transformations (
                    transformation_id, dataset_id, operation_type, operation_label, input_columns_json,
                    filters_json, aggregation_method, output_value, output_unit, review_status,
                    review_notes, lineage_json, created_at, updated_at
                ) VALUES (
                    :transformation_id, :dataset_id, :operation_type, :operation_label, :input_columns_json,
                    :filters_json, :aggregation_method, :output_value, :output_unit, :review_status,
                    :review_notes, :lineage_json, :created_at, :updated_at
                )
                ON CONFLICT(transformation_id) DO UPDATE SET
                    operation_type = excluded.operation_type,
                    operation_label = excluded.operation_label,
                    input_columns_json = excluded.input_columns_json,
                    filters_json = excluded.filters_json,
                    aggregation_method = excluded.aggregation_method,
                    output_value = excluded.output_value,
                    output_unit = excluded.output_unit,
                    review_status = excluded.review_status,
                    review_notes = excluded.review_notes,
                    lineage_json = excluded.lineage_json,
                    updated_at = excluded.updated_at
                """,
                record,
            )
            conn.commit()
        saved = self.get_transformation(record["transformation_id"])
        if saved is None:
            raise RuntimeError("transformation_save_failed")
        return saved

    def get_transformation(self, transformation_id: str) -> dict[str, Any] | None:
        if not transformation_id:
            return None
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT * FROM transformations WHERE transformation_id = ?",
                (transformation_id,),
            ).fetchone()
        return None if row is None else self._transformation_from_row(row)

    def dataset_transformations(self, dataset_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM transformations WHERE dataset_id = ? ORDER BY updated_at DESC",
                (dataset_id,),
            ).fetchall()
        return [self._transformation_from_row(row) for row in rows]

    def project_transformations(self, project_id: str) -> list[dict[str, Any]]:
        links = self.project_evidence_links(project_id)
        linked_ids = {row.get("transformation_id") for row in links if row.get("transformation_id")}
        dataset_ids = {row.get("dataset_id") for row in links if row.get("dataset_id")}
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM transformations ORDER BY updated_at DESC").fetchall()
        transformations = [self._transformation_from_row(row) for row in rows]
        return [
            row
            for row in transformations
            if row["transformation_id"] in linked_ids or row["dataset_id"] in dataset_ids
        ]

    def save_evidence_link(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_evidence_link(
            project_id,
            str(payload.get("target_id") or payload.get("assumption_id") or ""),
            str(payload.get("dataset_id") or ""),
        )
        record = normalize_evidence_link(project_id, payload, existing)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO evidence_links (
                    evidence_link_id, project_id, target_type, target_id, assumption_id, dataset_id, evidence_ref,
                    transformation_id, transformation_note, human_review_decision, created_at, updated_at
                ) VALUES (
                    :evidence_link_id, :project_id, :target_type, :target_id, :assumption_id, :dataset_id, :evidence_ref,
                    :transformation_id, :transformation_note, :human_review_decision, :created_at, :updated_at
                )
                ON CONFLICT(project_id, assumption_id, dataset_id) DO UPDATE SET
                    target_type = excluded.target_type,
                    target_id = excluded.target_id,
                    evidence_ref = excluded.evidence_ref,
                    transformation_id = excluded.transformation_id,
                    transformation_note = excluded.transformation_note,
                    human_review_decision = excluded.human_review_decision,
                    updated_at = excluded.updated_at
                """,
                record,
            )
            conn.commit()
        return self.get_evidence_link(project_id, record["target_id"], record["dataset_id"]) or record

    def get_evidence_link(self, project_id: str, target_id: str, dataset_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                """
                SELECT * FROM evidence_links
                WHERE project_id = ? AND assumption_id = ? AND dataset_id = ?
                """,
                (project_id, target_id, dataset_id),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        if not data.get("target_id"):
            data["target_id"] = data.get("assumption_id", "")
        if not data.get("target_type"):
            data["target_type"] = "assumption"
        if data.get("transformation_id") is None:
            data["transformation_id"] = ""
        return data

    def project_evidence_links(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM evidence_links WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        links = []
        for row in rows:
            data = dict(row)
            if not data.get("target_id"):
                data["target_id"] = data.get("assumption_id", "")
            if not data.get("target_type"):
                data["target_type"] = "assumption"
            if data.get("transformation_id") is None:
                data["transformation_id"] = ""
            links.append(data)
        return links

    def _dataset_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        columns = json_loads(data.pop("columns_json", None), [])
        preview = json_loads(data.pop("preview_json", None), [])
        notes = json_loads(data.pop("notes_json", None), {})
        return data | {"columns": columns, "preview": preview, "notes": notes}

    def _transformation_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        input_columns = json_loads(data.pop("input_columns_json", None), [])
        filters = json_loads(data.pop("filters_json", None), {})
        lineage = json_loads(data.pop("lineage_json", None), {})
        return data | {"input_columns": input_columns, "filters": filters, "lineage": lineage}

