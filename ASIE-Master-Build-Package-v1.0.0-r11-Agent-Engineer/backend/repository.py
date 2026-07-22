from __future__ import annotations

import sqlite3
import secrets
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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
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
                    source_type TEXT NOT NULL,
                    confidence REAL,
                    review_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, input_key),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL DEFAULT 'org_local_legacy',
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    import_method TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    human_review_decision TEXT,
                    license_snapshot_ref TEXT,
                    terms_hash TEXT,
                    classification TEXT,
                    pdpl_check TEXT,
                    attribution TEXT,
                    row_count INTEGER NOT NULL,
                    columns_json TEXT NOT NULL,
                    preview_json TEXT NOT NULL,
                    notes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence_links (
                    evidence_link_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    target_type TEXT NOT NULL DEFAULT 'assumption',
                    target_id TEXT NOT NULL DEFAULT '',
                    assumption_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    transformation_id TEXT,
                    evidence_ref TEXT NOT NULL,
                    transformation_note TEXT NOT NULL,
                    human_review_decision TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, assumption_id, dataset_id),
                    FOREIGN KEY(project_id) REFERENCES projects(project_id),
                    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
                );

                CREATE TABLE IF NOT EXISTS transformations (
                    transformation_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    operation_label TEXT NOT NULL,
                    input_columns_json TEXT NOT NULL,
                    filters_json TEXT NOT NULL,
                    aggregation_method TEXT NOT NULL,
                    output_value TEXT,
                    output_unit TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    review_notes TEXT NOT NULL DEFAULT '',
                    lineage_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
                );

                CREATE TABLE IF NOT EXISTS snapshot_reviews (
                    review_id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS action_item_states (
                    action_item_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._migrate_columns(conn)
            self._seed_legacy_organization(conn)
            self._seed_sources(conn)
            conn.commit()

    def update_project(self, project_id: str, payload: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        merged_inputs = dict(project.inputs)
        merged_inputs.update(dict(payload.get("inputs") or {}))
        updated = ProjectRecord(
            project_id=project.project_id,
            name=str(payload.get("name", project.name) or project.name),
            sector=str(payload.get("sector", project.sector) or project.sector),
            jurisdiction=str(payload.get("jurisdiction", project.jurisdiction) or project.jurisdiction),
            depth_profile=str(payload.get("depth_profile", project.depth_profile) or project.depth_profile),
            inputs=merged_inputs,
            created_at=project.created_at,
            updated_at=now_iso(),
            organization_id=project.organization_id,
        )
        with closing(self.connect()) as conn:
            conn.execute(
                """
                UPDATE projects
                SET name = ?, sector = ?, jurisdiction = ?, depth_profile = ?, inputs_json = ?, updated_at = ?
                WHERE project_id = ?
                """,
                (
                    updated.name,
                    updated.sector,
                    updated.jurisdiction,
                    updated.depth_profile,
                    json_dumps(updated.inputs),
                    updated.updated_at,
                    updated.project_id,
                ),
            )
            conn.commit()
        self.sync_assumptions(updated)
        return updated

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        for table, columns in {
            "runs": {"audit_json": "TEXT NOT NULL DEFAULT '{}'"},
            "projects": {"organization_id": f"TEXT NOT NULL DEFAULT '{LEGACY_ORGANIZATION_ID}'"},
            "datasets": {"organization_id": f"TEXT NOT NULL DEFAULT '{LEGACY_ORGANIZATION_ID}'"},
            "source_records": {
                "terms_hash": "TEXT",
                "license_snapshot_ref": "TEXT",
                "lawful_purpose": "TEXT",
                "reviewer_decision": "TEXT",
            },
            "evidence_links": {
                "target_type": "TEXT NOT NULL DEFAULT 'assumption'",
                "target_id": "TEXT NOT NULL DEFAULT ''",
                "transformation_id": "TEXT",
            },
            "transformations": {
                "review_notes": "TEXT NOT NULL DEFAULT ''",
            },
        }.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for column, declaration in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def _seed_legacy_organization(self, conn: sqlite3.Connection) -> None:
        now = now_iso()
        conn.execute(
            "INSERT OR IGNORE INTO organizations (organization_id, name, lifecycle_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (LEGACY_ORGANIZATION_ID, "مساحة ASIE المحلية", "active", now, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO organization_entitlements (organization_id, plan_code, lifecycle_status, quota_json, updated_at) VALUES (?, ?, ?, ?, ?)",
            (LEGACY_ORGANIZATION_ID, "local_baseline", "active", json_dumps({"external_payments": False, "external_integrations": False, "ai_provider": False}), now),
        )
        conn.execute("UPDATE projects SET organization_id = ? WHERE organization_id IS NULL OR organization_id = ''", (LEGACY_ORGANIZATION_ID,))
        conn.execute("UPDATE datasets SET organization_id = ? WHERE organization_id IS NULL OR organization_id = ''", (LEGACY_ORGANIZATION_ID,))

    def _seed_sources(self, conn: sqlite3.Connection) -> None:
        for row in seed_source_records():
            conn.execute(
                """
                INSERT OR IGNORE INTO source_records (
                    source_id, publisher, route, state, url, terms_url, terms_hash,
                    license_snapshot_ref, attribution, classification, pdpl_check,
                    nca_check, lawful_purpose, reviewer, reviewer_decision, reviewed_at, notes_json
                ) VALUES (
                    :source_id, :publisher, :route, :state, :url, :terms_url, :terms_hash,
                    :license_snapshot_ref, :attribution, :classification, :pdpl_check,
                    :nca_check, :lawful_purpose, :reviewer, :reviewer_decision, :reviewed_at, :notes_json
                )
                """,
                row,
            )

    def create_project(self, payload: dict[str, Any]) -> ProjectRecord:
        created_at = now_iso()
        project = ProjectRecord(
            project_id=new_id("prj"),
            name=str(payload.get("name") or "مشروع جدوى محلي"),
            sector=str(payload.get("sector") or "خدمات"),
            jurisdiction=str(payload.get("jurisdiction") or "Saudi Arabia"),
            depth_profile=str(payload.get("depth_profile") or "starter"),
            inputs=dict(payload.get("inputs") or {}),
            created_at=created_at,
            updated_at=created_at,
            organization_id=str(payload.get("organization_id") or LEGACY_ORGANIZATION_ID),
        )
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, sector, jurisdiction, depth_profile,
                    inputs_json, created_at, updated_at, organization_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    project.name,
                    project.sector,
                    project.jurisdiction,
                    project.depth_profile,
                    json_dumps(project.inputs),
                    project.created_at,
                    project.updated_at,
                    project.organization_id,
                ),
            )
            conn.commit()
        self.sync_assumptions(project)
        return project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        return ProjectRecord(
            project_id=row["project_id"],
            name=row["name"],
            sector=row["sector"],
            jurisdiction=row["jurisdiction"],
            depth_profile=row["depth_profile"],
            inputs=json_loads(row["inputs_json"], {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            organization_id=row["organization_id"],
        )

    def sync_assumptions(self, project: ProjectRecord) -> None:
        review_manifest = default_assumption_records(project)
        with closing(self.connect()) as conn:
            if review_manifest:
                placeholders = ", ".join("?" for _ in review_manifest)
                conn.execute(
                    f"DELETE FROM assumptions WHERE project_id = ? AND input_key NOT IN ({placeholders})",
                    (project.project_id, *review_manifest.keys()),
                )
            else:
                conn.execute("DELETE FROM assumptions WHERE project_id = ?", (project.project_id,))
            conn.commit()
        for meta in review_manifest.values():
            self.save_assumption(project.project_id, meta)

    def save_assumption(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = now_iso()
        input_key = str(payload.get("input_key") or payload.get("assumption_id") or new_id("assumption"))
        record = {
            "assumption_id": str(payload.get("assumption_id") or f"assumption:{project_id}:{input_key}"),
            "project_id": project_id,
            "input_key": input_key,
            "label": str(payload.get("label") or input_key),
            "value": str(payload.get("value") if payload.get("value") is not None else ""),
            "unit": str(payload.get("unit") or "unit"),
            "owner": str(payload.get("owner") or "Project Wizard"),
            "source_type": str(payload.get("source_type") or "user_input"),
            "confidence": float(payload.get("confidence") if payload.get("confidence") is not None else 0.65),
            "review_status": str(payload.get("review_status") or "draft"),
            "created_at": now,
            "updated_at": now,
        }
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO assumptions (
                    assumption_id, project_id, input_key, label, value, unit, owner,
                    source_type, confidence, review_status, created_at, updated_at
                ) VALUES (
                    :assumption_id, :project_id, :input_key, :label, :value, :unit, :owner,
                    :source_type, :confidence, :review_status, :created_at, :updated_at
                )
                ON CONFLICT(project_id, input_key) DO UPDATE SET
                    label = excluded.label,
                    value = excluded.value,
                    unit = excluded.unit,
                    owner = excluded.owner,
                    source_type = CASE
                        WHEN assumptions.value = excluded.value THEN assumptions.source_type
                        ELSE excluded.source_type
                    END,
                    confidence = CASE
                        WHEN assumptions.value = excluded.value THEN assumptions.confidence
                        ELSE excluded.confidence
                    END,
                    review_status = CASE
                        WHEN assumptions.value = excluded.value THEN assumptions.review_status
                        ELSE excluded.review_status
                    END,
                    updated_at = excluded.updated_at
                """,
                record,
            )
            conn.commit()
        return record

    def project_assumptions(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM assumptions WHERE project_id = ? ORDER BY input_key",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_projects(self, organization_id: str | None = None) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            if organization_id:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE organization_id = ? ORDER BY created_at DESC LIMIT 25",
                    (organization_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT 25").fetchall()
        return [self._project_from_row(row).to_public() for row in rows]

    def _project_from_row(self, row: sqlite3.Row) -> ProjectRecord:
        return ProjectRecord(
            project_id=row["project_id"],
            name=row["name"],
            sector=row["sector"],
            jurisdiction=row["jurisdiction"],
            depth_profile=row["depth_profile"],
            inputs=json_loads(row["inputs_json"], {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            organization_id=row["organization_id"],
        )

    def create_user(self, *, email: str, display_name: str, password: str, platform_role: str | None = None) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        if "@" not in normalized_email or len(normalized_email) > 254:
            raise ValueError("invalid_email")
        if platform_role is not None and platform_role not in {"platform_admin", "platform_support"}:
            raise ValueError("invalid_platform_role")
        now = now_iso()
        user = {
            "user_id": new_id("usr"), "email": normalized_email, "display_name": display_name.strip() or normalized_email,
            "password_hash": hash_password(password), "status": "active", "platform_role": platform_role,
            "created_at": now, "updated_at": now,
        }
        with closing(self.connect()) as conn:
            try:
                conn.execute(
                    "INSERT INTO users (user_id, email, display_name, password_hash, status, platform_role, created_at, updated_at) VALUES (:user_id, :email, :display_name, :password_hash, :status, :platform_role, :created_at, :updated_at)",
                    user,
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("email_already_registered") from exc
            conn.commit()
        return self.public_user(user)

    def user_count(self) -> int:
        with closing(self.connect()) as conn:
            return int(conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"])

    @staticmethod
    def public_user(row: dict[str, Any] | sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in ("user_id", "email", "display_name", "status", "platform_role", "created_at", "updated_at")}

    def create_organization(self, *, name: str, owner_user_id: str) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("organization_name_required")
        now = now_iso()
        organization = {"organization_id": new_id("org"), "name": name.strip(), "lifecycle_status": "active", "created_at": now, "updated_at": now}
        membership = {"membership_id": new_id("mbr"), "user_id": owner_user_id, "organization_id": organization["organization_id"], "role": "organization_owner", "status": "active", "invited_at": now, "accepted_at": now, "created_at": now, "updated_at": now}
        with closing(self.connect()) as conn:
            if conn.execute("SELECT 1 FROM users WHERE user_id = ? AND status = 'active'", (owner_user_id,)).fetchone() is None:
                raise ValueError("user_not_found")
            conn.execute("INSERT INTO organizations (organization_id, name, lifecycle_status, created_at, updated_at) VALUES (:organization_id, :name, :lifecycle_status, :created_at, :updated_at)", organization)
            conn.execute("INSERT INTO memberships (membership_id, user_id, organization_id, role, status, invited_at, accepted_at, created_at, updated_at) VALUES (:membership_id, :user_id, :organization_id, :role, :status, :invited_at, :accepted_at, :created_at, :updated_at)", membership)
            conn.execute("INSERT INTO organization_entitlements (organization_id, plan_code, lifecycle_status, quota_json, updated_at) VALUES (?, ?, ?, ?, ?)", (organization["organization_id"], "local_baseline", "active", json_dumps({"external_payments": False, "external_integrations": False, "ai_provider": False}), now))
            conn.commit()
        return organization

    def add_membership(self, *, organization_id: str, user_id: str, role: str, actor_user_id: str | None = None) -> dict[str, Any]:
        if role not in VALID_ROLES or role.startswith("platform_"):
            raise ValueError("invalid_organization_role")
        now = now_iso()
        row = {"membership_id": new_id("mbr"), "user_id": user_id, "organization_id": organization_id, "role": role, "status": "active", "invited_at": now, "accepted_at": now, "created_at": now, "updated_at": now}
        with closing(self.connect()) as conn:
            if conn.execute("SELECT 1 FROM organizations WHERE organization_id = ? AND lifecycle_status = 'active'", (organization_id,)).fetchone() is None:
                raise ValueError("organization_not_found")
            if conn.execute("SELECT 1 FROM users WHERE user_id = ? AND status = 'active'", (user_id,)).fetchone() is None:
                raise ValueError("user_not_found")
            conn.execute("INSERT INTO memberships (membership_id, user_id, organization_id, role, status, invited_at, accepted_at, created_at, updated_at) VALUES (:membership_id, :user_id, :organization_id, :role, :status, :invited_at, :accepted_at, :created_at, :updated_at) ON CONFLICT(user_id, organization_id) DO UPDATE SET role = excluded.role, status = 'active', accepted_at = excluded.accepted_at, updated_at = excluded.updated_at", row)
            conn.commit()
        self.audit(actor_user_id=actor_user_id, organization_id=organization_id, action="membership.upsert", target_type="membership", target_id=f"{user_id}:{organization_id}", result="allowed")
        return row

    def memberships_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT m.membership_id, m.user_id, m.organization_id, o.name AS organization_name, m.role, m.status, m.created_at, m.updated_at FROM memberships m JOIN organizations o ON o.organization_id = m.organization_id WHERE m.user_id = ? AND m.status = 'active' AND o.lifecycle_status = 'active' ORDER BY m.created_at", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def create_session(self, *, email: str, password: str) -> tuple[str, dict[str, Any]]:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE AND status = 'active'", (email.strip().lower(),)).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            self.audit(actor_user_id=None, organization_id=None, action="session.login", target_type="user", target_id=email.strip().lower(), result="denied", reason="invalid_credentials")
            raise PermissionError("invalid_credentials")
        token, now = new_session_token(), now_iso()
        with closing(self.connect()) as conn:
            conn.execute("INSERT INTO sessions (session_id, user_id, token_hash, created_at, expires_at, revoked_at) VALUES (?, ?, ?, ?, ?, NULL)", (new_id("ses"), row["user_id"], token_hash(token), now, (datetime.fromisoformat(now) + timedelta(hours=8)).isoformat()))
            conn.commit()
        self.audit(actor_user_id=row["user_id"], organization_id=None, action="session.login", target_type="user", target_id=row["user_id"], result="allowed")
        return token, self.public_user(dict(row))

    def principal_for_token(self, token: str, organization_id: str | None = None) -> Principal | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT s.session_id, u.user_id, u.platform_role FROM sessions s JOIN users u ON u.user_id = s.user_id WHERE s.token_hash = ? AND s.revoked_at IS NULL AND s.expires_at > ? AND u.status = 'active'", (token_hash(token), now_iso())).fetchone()
            if row is None:
                return None
            membership = None
            if organization_id:
                membership = conn.execute("SELECT role FROM memberships WHERE user_id = ? AND organization_id = ? AND status = 'active'", (row["user_id"], organization_id)).fetchone()
        return Principal(user_id=row["user_id"], session_id=row["session_id"], organization_id=organization_id, role=membership["role"] if membership else None, platform_role=row["platform_role"])

    def revoke_session(self, token: str) -> bool:
        with closing(self.connect()) as conn:
            cursor = conn.execute("UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL", (now_iso(), token_hash(token)))
            conn.commit()
        return cursor.rowcount == 1

    def reset_local_password(self, *, user_id: str, password: str, actor_user_id: str) -> dict[str, Any]:
        """Local-admin recovery only; it never emits a reset token or external message."""
        password_hash = hash_password(password)
        now = now_iso()
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ? AND status = 'active'", (user_id,)).fetchone()
            if row is None:
                raise ValueError("user_not_found")
            conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?", (password_hash, now, user_id))
            conn.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now, user_id))
            conn.commit()
        self.audit(actor_user_id=actor_user_id, organization_id=None, action="identity.local_password_reset", target_type="user", target_id=user_id, result="allowed", reason="local_admin_recovery")
        return self.public_user(dict(row) | {"updated_at": now})

    def create_password_recovery_request(self, *, email: str) -> dict[str, Any]:
        normalized = email.strip().lower()
        now = datetime.fromisoformat(now_iso())
        token = secrets.token_urlsafe(32)
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT user_id FROM users WHERE email = ? AND status = 'active'", (normalized,)).fetchone()
            if row is not None:
                conn.execute("UPDATE password_recovery_tokens SET consumed_at = ? WHERE user_id = ? AND consumed_at IS NULL", (now.isoformat(), row["user_id"]))
                conn.execute("INSERT INTO password_recovery_tokens (token_id, user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?)", (new_id("prt"), row["user_id"], token_hash(token), now.isoformat(), (now + timedelta(minutes=15)).isoformat()))
                conn.commit()
        if row is not None:
            self.audit(actor_user_id=None, organization_id=None, action="identity.password_recovery_requested", target_type="user", target_id=row["user_id"], result="queued", reason="local_only")
        return {"accepted": True, "recovery_token": token if row is not None else None, "external_delivery_enabled": False}

    def consume_password_recovery_token(self, *, token: str, password: str) -> dict[str, Any]:
        now = now_iso()
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT token_id, user_id FROM password_recovery_tokens WHERE token_hash = ? AND consumed_at IS NULL AND expires_at > ?", (token_hash(token), now)).fetchone()
            if row is None:
                raise ValueError("invalid_or_expired_recovery_token")
            conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?", (hash_password(password), now, row["user_id"]))
            conn.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now, row["user_id"]))
            conn.execute("UPDATE password_recovery_tokens SET consumed_at = ? WHERE token_id = ?", (now, row["token_id"]))
            conn.commit()
        self.audit(actor_user_id=None, organization_id=None, action="identity.password_recovery_completed", target_type="user", target_id=row["user_id"], result="allowed", reason="local_only")
        return {"user_id": row["user_id"], "sessions_revoked": True}

    def audit(self, *, actor_user_id: str | None, organization_id: str | None, action: str, target_type: str, target_id: str, result: str, reason: str | None = None, correlation_id: str | None = None) -> None:
        with closing(self.connect()) as conn:
            conn.execute("INSERT INTO security_audit_events (event_id, actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_id("audit"), actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, now_iso()))
            conn.commit()

    def security_audit_events(self, *, limit: int = 100, organization_id: str | None = None) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with closing(self.connect()) as conn:
            if organization_id:
                rows = conn.execute(
                    "SELECT event_id, actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, created_at FROM security_audit_events WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?",
                    (organization_id, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT event_id, actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, created_at FROM security_audit_events ORDER BY created_at DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def operational_run_failures(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT r.run_id, r.project_id, p.organization_id, r.status, r.created_at FROM runs r JOIN projects p ON p.project_id = r.project_id WHERE r.status != 'completed' ORDER BY r.created_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def platform_incidents(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT incident_id, organization_id, snapshot_id, severity, status, summary, opened_at, resolved_at FROM platform_incidents ORDER BY opened_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_organization_data_request(self, *, organization_id: str, request_type: str, requested_by_user_id: str, legal_basis: str, notes: str = "") -> dict[str, Any]:
        if request_type not in {"export", "delete"}:
            raise ValueError("invalid_data_request_type")
        if not legal_basis.strip():
            raise ValueError("legal_basis_required")
        record = {
            "request_id": new_id("datareq"),
            "organization_id": organization_id,
            "request_type": request_type,
            "status": "queued_for_legal_review",
            "requested_by_user_id": requested_by_user_id,
            "legal_basis": legal_basis.strip(),
            "notes": notes.strip(),
            "created_at": now_iso(),
        }
        with closing(self.connect()) as conn:
            conn.execute(
                "INSERT INTO organization_data_requests (request_id, organization_id, request_type, status, requested_by_user_id, legal_basis, notes, created_at) VALUES (:request_id, :organization_id, :request_type, :status, :requested_by_user_id, :legal_basis, :notes, :created_at)",
                record,
            )
            conn.commit()
        return record

    def control_plane_organizations(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """SELECT o.organization_id, o.name, o.lifecycle_status, o.created_at, o.updated_at,
                          e.plan_code, e.lifecycle_status AS subscription_status, e.quota_json, e.updated_at AS subscription_updated_at,
                          (SELECT COUNT(*) FROM memberships m WHERE m.organization_id = o.organization_id AND m.status = 'active') AS member_count,
                          (SELECT COUNT(*) FROM projects p WHERE p.organization_id = o.organization_id) AS project_count
                   FROM organizations o JOIN organization_entitlements e ON e.organization_id = o.organization_id
                   ORDER BY o.created_at DESC"""
            ).fetchall()
        return [dict(row) | {"quota": json_loads(row["quota_json"], {})} for row in rows]

    def control_plane_users(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT user_id, email, display_name, status, platform_role, created_at, updated_at FROM users ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def subscription_for_organization(self, organization_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT organization_id, plan_code, lifecycle_status, quota_json, updated_at FROM organization_entitlements WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
        return None if row is None else dict(row) | {"quota": json_loads(row["quota_json"], {})}

    def set_subscription(self, *, organization_id: str, plan_code: str, lifecycle_status: str, quota: dict[str, Any], actor_user_id: str, reason: str) -> dict[str, Any]:
        if lifecycle_status not in {"trial", "active", "grace", "suspended", "cancelled"}:
            raise ValueError("invalid_subscription_lifecycle")
        if not plan_code.strip() or not reason.strip():
            raise ValueError("subscription_plan_and_reason_required")
        now = now_iso()
        with closing(self.connect()) as conn:
            previous = conn.execute("SELECT plan_code, lifecycle_status FROM organization_entitlements WHERE organization_id = ?", (organization_id,)).fetchone()
            if previous is None:
                raise ValueError("organization_not_found")
            conn.execute(
                "UPDATE organization_entitlements SET plan_code = ?, lifecycle_status = ?, quota_json = ?, updated_at = ? WHERE organization_id = ?",
                (plan_code.strip(), lifecycle_status, json_dumps(quota), now, organization_id),
            )
            conn.execute(
                "INSERT INTO subscription_change_events (event_id, organization_id, previous_plan_code, previous_lifecycle_status, plan_code, lifecycle_status, reason, actor_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id("subevt"), organization_id, previous["plan_code"], previous["lifecycle_status"], plan_code.strip(), lifecycle_status, reason.strip(), actor_user_id, now),
            )
            conn.commit()
        return self.subscription_for_organization(organization_id) or {}

    def usage_summary(self, organization_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            project_count = int(conn.execute("SELECT COUNT(*) AS count FROM projects WHERE organization_id = ?", (organization_id,)).fetchone()["count"])
            dataset_count = int(conn.execute("SELECT COUNT(*) AS count FROM datasets WHERE organization_id = ?", (organization_id,)).fetchone()["count"])
            run_count = int(conn.execute("SELECT COUNT(*) AS count FROM runs r JOIN projects p ON p.project_id = r.project_id WHERE p.organization_id = ?", (organization_id,)).fetchone()["count"])
        return [
            {"metric_code": "projects.created", "quantity": project_count, "definition": "عدد مشاريع المنظمة المسجلة"},
            {"metric_code": "datasets.registered", "quantity": dataset_count, "definition": "عدد سجلات الأدلة المسجلة"},
            {"metric_code": "runs.completed_or_recorded", "quantity": run_count, "definition": "عدد عمليات التشغيل المسجلة"},
        ]

    def create_local_invoice(self, *, organization_id: str, amount_minor: int, currency: str, actor_user_id: str) -> dict[str, Any]:
        if amount_minor < 0 or len(currency.strip()) != 3:
            raise ValueError("invalid_local_invoice")
        now = now_iso()
        record = {"invoice_id": new_id("inv"), "organization_id": organization_id, "status": "issued_uncollected", "amount_minor": amount_minor, "currency": currency.upper(), "created_at": now, "updated_at": now}
        with closing(self.connect()) as conn:
            if conn.execute("SELECT 1 FROM organizations WHERE organization_id = ?", (organization_id,)).fetchone() is None:
                raise ValueError("organization_not_found")
            conn.execute("INSERT INTO local_invoices (invoice_id, organization_id, status, amount_minor, currency, created_at, updated_at) VALUES (:invoice_id, :organization_id, :status, :amount_minor, :currency, :created_at, :updated_at)", record)
            conn.commit()
        self.audit(actor_user_id=actor_user_id, organization_id=organization_id, action="local_invoice.issue", target_type="invoice", target_id=record["invoice_id"], result="allowed", reason="payment_collection_disabled")
        return record

    def local_invoices(self, organization_id: str | None = None) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT invoice_id, organization_id, status, amount_minor, currency, created_at, updated_at FROM local_invoices" + (" WHERE organization_id = ?" if organization_id else "") + " ORDER BY created_at DESC", (organization_id,) if organization_id else ()).fetchall()
        return [dict(row) for row in rows]

    def create_notification(self, *, organization_id: str, template_id: str, reference_type: str, reference_id: str, recipient_user_id: str | None = None) -> dict[str, Any]:
        if template_id not in {"review_requested", "review_recorded", "subscription_changed", "support_updated"}:
            raise ValueError("unknown_notification_template")
        record = {"notification_id": new_id("ntf"), "organization_id": organization_id, "recipient_user_id": recipient_user_id, "template_id": template_id, "delivery_status": "in_app_pending", "reference_type": reference_type, "reference_id": reference_id, "created_at": now_iso(), "read_at": None}
        with closing(self.connect()) as conn:
            conn.execute("INSERT INTO notifications (notification_id, organization_id, recipient_user_id, template_id, delivery_status, reference_type, reference_id, created_at, read_at) VALUES (:notification_id, :organization_id, :recipient_user_id, :template_id, :delivery_status, :reference_type, :reference_id, :created_at, :read_at)", record)
            conn.commit()
        return record

    def notifications_for_organization(self, organization_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT notification_id, organization_id, recipient_user_id, template_id, delivery_status, reference_type, reference_id, created_at, read_at FROM notifications WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, max(1, min(limit, 200)))).fetchall()
        return [dict(row) for row in rows]

    def project_organization_id(self, project_id: str) -> str | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT organization_id FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return None if row is None else str(row["organization_id"])

    def run_project_id(self, run_id: str) -> str | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT project_id FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return None if row is None else str(row["project_id"])

    def snapshot_project_id(self, snapshot_id: str) -> str | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT project_id FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        return None if row is None else str(row["project_id"])

    def dataset_organization_id(self, dataset_id: str) -> str | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT organization_id FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
        return None if row is None else str(row["organization_id"])

    def save_run_snapshot(self, project_id: str, overview: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
        run_id = overview["run"]["run_id"]
        snapshot_id = overview["snapshot"]["snapshot_id"]
        created_at = overview["run"]["created_at"]
        audit = overview.get("audit", {})
        assembly = overview.get("snapshot_assembly", {})
        if assembly.get("contract_id") != "snapshot.assemble.v1":
            raise ValueError("snapshot persistence requires snapshot.assemble.v1")
        if assembly.get("projection_source") != "immutable_assembled_snapshot":
            raise ValueError("snapshot persistence requires immutable assembled projection")
        if not overview["snapshot"].get("content_hash") or not overview["snapshot"].get("integrity_hash"):
            raise ValueError("snapshot persistence requires assembly integrity hashes")
        overview_projection_hash = assembly.get("overview_projection_hash")
        overview_material = json_loads(json_dumps(overview), {})
        overview_material.get("snapshot_assembly", {}).pop("overview_projection_hash", None)
        if not overview_projection_hash or canonical_hash(overview_material) != overview_projection_hash:
            raise ValueError("snapshot overview projection hash mismatch")
        if report.get("snapshot_id") != snapshot_id or report.get("run_id") != run_id or report.get("project_id") != project_id:
            raise ValueError("snapshot report identity mismatch")
        report_assembly = report.get("snapshot_assembly", {})
        if report_assembly.get("content_hash") != overview["snapshot"]["content_hash"]:
            raise ValueError("snapshot report content hash mismatch")
        if report_assembly.get("integrity_hash") != overview["snapshot"]["integrity_hash"]:
            raise ValueError("snapshot report integrity hash mismatch")
        if report_assembly.get("overview_projection_hash") != overview_projection_hash:
            raise ValueError("snapshot report overview projection hash mismatch")
        report_projection_hash = report_assembly.get("report_projection_hash")
        report_material = json_loads(json_dumps(report), {})
        report_material.get("snapshot_assembly", {}).pop("report_projection_hash", None)
        if not report_projection_hash or canonical_hash(report_material) != report_projection_hash:
            raise ValueError("snapshot report projection hash mismatch")
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, project_id, scenario_id, snapshot_id, status, created_at, audit_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    overview["run"]["scenario_id"],
                    snapshot_id,
                    overview["run"]["status"],
                    created_at,
                    json_dumps(audit),
                ),
            )
            conn.execute(
                """
                INSERT INTO snapshots (snapshot_id, project_id, run_id, created_at, overview_json, report_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, project_id, run_id, created_at, json_dumps(overview), json_dumps(report)),
            )
            conn.commit()
        return {"run_id": run_id, "snapshot_id": snapshot_id}

    def list_project_runs(self, project_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT run_id, project_id, scenario_id, snapshot_id, status, created_at FROM runs WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_project_run(self, project_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                "SELECT run_id, project_id, scenario_id, snapshot_id, status, created_at FROM runs WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
        return None if row is None else dict(row)

    def get_run_overview(self, run_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT overview_json FROM snapshots WHERE run_id = ?", (run_id,)).fetchone()
        return None if row is None else json_loads(row["overview_json"], {})

    def get_snapshot_overview(self, snapshot_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT overview_json FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        return None if row is None else json_loads(row["overview_json"], {})

    def get_run_audit(self, run_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT audit_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return None if row is None else json_loads(row["audit_json"], {})

    def get_snapshot_report(self, snapshot_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT report_json FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        return None if row is None else json_loads(row["report_json"], {})

    def save_snapshot_review(
        self,
        snapshot_id: str,
        run_id: str,
        project_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        review = normalize_review(snapshot_id, run_id, project_id, payload)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO snapshot_reviews (
                    review_id, snapshot_id, run_id, project_id, reviewer, decision, notes, created_at
                ) VALUES (
                    :review_id, :snapshot_id, :run_id, :project_id, :reviewer, :decision, :notes, :created_at
                )
                """,
                review,
            )
            conn.commit()
        return review

    def snapshot_reviews(self, snapshot_id: str) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT review_id, snapshot_id, run_id, project_id, reviewer, decision, notes, created_at
                FROM snapshot_reviews
                WHERE snapshot_id = ?
                ORDER BY created_at DESC
                """,
                (snapshot_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_snapshot_review(self, snapshot_id: str) -> dict[str, Any] | None:
        rows = self.snapshot_reviews(snapshot_id)
        return rows[0] if rows else None

    def save_action_item_state(
        self,
        project_id: str,
        action_item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        row = normalize_action_item_patch(project_id, action_item_id, payload)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO action_item_states (action_item_id, project_id, status, notes, updated_at)
                VALUES (:action_item_id, :project_id, :status, :notes, :updated_at)
                ON CONFLICT(action_item_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                row,
            )
            conn.commit()
        return row

    def project_action_item_states(self, project_id: str) -> dict[str, dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT action_item_id, project_id, status, notes, updated_at
                FROM action_item_states
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchall()
        return {row["action_item_id"]: dict(row) for row in rows}

    def source_records(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM source_records ORDER BY source_id").fetchall()
        return [self._source_from_row(row) for row in rows]

    def get_source_record(self, source_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM source_records WHERE source_id = ?", (source_id,)).fetchone()
        return None if row is None else self._source_from_row(row)

    def _source_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        notes = json_loads(data.pop("notes_json", None), {})
        return data | {"notes": notes}

    def save_source_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = normalize_source_review(payload)
        if not record["source_id"]:
            record["source_id"] = new_id("src")
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO source_records (
                    source_id, publisher, route, state, url, terms_url, terms_hash,
                    license_snapshot_ref, attribution, classification, pdpl_check,
                    nca_check, lawful_purpose, reviewer, reviewer_decision, reviewed_at, notes_json
                ) VALUES (
                    :source_id, :publisher, :route, :state, :url, :terms_url, :terms_hash,
                    :license_snapshot_ref, :attribution, :classification, :pdpl_check,
                    :nca_check, :lawful_purpose, :reviewer, :reviewer_decision, :reviewed_at, :notes_json
                )
                ON CONFLICT(source_id) DO UPDATE SET
                    publisher = excluded.publisher,
                    route = excluded.route,
                    state = excluded.state,
                    url = excluded.url,
                    terms_url = excluded.terms_url,
                    terms_hash = excluded.terms_hash,
                    license_snapshot_ref = excluded.license_snapshot_ref,
                    attribution = excluded.attribution,
                    classification = excluded.classification,
                    pdpl_check = excluded.pdpl_check,
                    nca_check = excluded.nca_check,
                    lawful_purpose = excluded.lawful_purpose,
                    reviewer = excluded.reviewer,
                    reviewer_decision = excluded.reviewer_decision,
                    reviewed_at = excluded.reviewed_at,
                    notes_json = excluded.notes_json
                """,
                record,
            )
            conn.commit()
        return record | {"notes": json_loads(record["notes_json"], {})}

    def _authorize_intelligence(self, *, principal: Principal | None, organization_id: str, project_id: str, permission: str, action: str, target_id: str, correlation_id: str | None = None) -> None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT organization_id FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if row is None or row["organization_id"] != organization_id:
            self.audit(actor_user_id=principal.user_id if principal else None, organization_id=organization_id, action=action, target_type="intelligence_context", target_id=target_id, result="denied", reason="project_tenant_mismatch", correlation_id=correlation_id)
            raise PermissionError("intelligence_project_tenant_mismatch")
        authorize_intelligence_action(principal, organization_id=organization_id, project_id=project_id, permission=permission, action=action, target_id=target_id, audit_sink=self, correlation_id=correlation_id)

    def create_intelligence_context(self, *, payload: dict[str, Any], principal: Principal | None, correlation_id: str | None = None) -> dict[str, Any]:
        organization_id = str(payload.get("organization_id") or "")
        project_id = str(payload.get("project_id") or "")
        context_id = str(payload.get("context_build_id") or new_id("ctx"))
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="project.edit", action="aia.context.create", target_id=context_id, correlation_id=correlation_id)
        if not payload.get("idempotency_key"):
            raise ValueError("idempotency_key_required")
        record = dict(payload) | {"context_build_id": context_id, "state": payload.get("state") or "DRAFT", "version": 1, "created_at": now_iso(), "updated_at": now_iso()}
        fingerprint = idempotency_fingerprint(organization_id, project_id, str(payload["idempotency_key"]))
        with closing(self.connect()) as conn:
            try:
                conn.execute("INSERT INTO intelligence_contexts (context_build_id, organization_id, project_id, context_hash, state, version, idempotency_fingerprint, payload_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (context_id, organization_id, project_id, str(record.get("context_hash") or ""), record["state"], 1, fingerprint, json_dumps(record), record["created_at"], record["updated_at"]))
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("context_idempotency_or_duplicate") from exc
        return record | {"idempotency_fingerprint": fingerprint}

    def get_intelligence_context(self, *, context_build_id: str, organization_id: str, project_id: str, principal: Principal | None) -> dict[str, Any] | None:
        self._authorize_intelligence(principal=principal, organization_id=organization_id, project_id=project_id, permission="snapshot.read", action="aia.context.read", target_id=context_build_id)
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT payload_json, version, context_hash, state FROM intelligence_contexts WHERE context_build_id = ? AND organization_id = ? AND project_id = ?", (context_build_id, organization_id, project_id)).fetchone()
        if row is None:
            return None
        return json_loads(row["payload_json"], {}) | {"version": row["version"], "context_hash": row["context_hash"], "state": row["state"]}

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
