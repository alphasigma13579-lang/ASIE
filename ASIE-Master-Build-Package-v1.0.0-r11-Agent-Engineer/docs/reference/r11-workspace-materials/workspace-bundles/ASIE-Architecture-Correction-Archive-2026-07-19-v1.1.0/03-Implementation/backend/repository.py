from __future__ import annotations

import sqlite3
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


def default_assumption_records(project: "ProjectRecord") -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for key, value in project.inputs.items():
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
    for key, default in {
        "annual_discount_rate": 0.1,
        "working_capital_months": 2,
        "debt_amount": 0,
        "annual_interest_rate": 0.08,
        "loan_years": 5,
        "loan_grace_months": 0,
        "depreciation_years": 5,
        "equity_contribution": 0,
    }.items():
        if key not in rows:
            label, unit = ASSUMPTION_META[key]
            rows[key] = {
                "input_key": key,
                "label": label,
                "value": default,
                "unit": unit,
                "owner": "Finance Engine defaults",
                "source_type": "local_default",
                "confidence": 0.55,
                "review_status": "needs_review",
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
        )
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, sector, jurisdiction, depth_profile,
                    inputs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        )

    def sync_assumptions(self, project: ProjectRecord) -> None:
        for key, meta in default_assumption_records(project).items():
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
                    source_type = excluded.source_type,
                    confidence = excluded.confidence,
                    review_status = excluded.review_status,
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

    def list_projects(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
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
        )

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

    def datasets(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM datasets ORDER BY updated_at DESC").fetchall()
        return [self._dataset_from_row(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
        return None if row is None else self._dataset_from_row(row)

    def save_dataset(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_dataset(str(payload.get("dataset_id") or ""))
        record = normalize_dataset_payload(payload, existing)
        with closing(self.connect()) as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    dataset_id, source_id, title, publisher, import_method, review_status,
                    human_review_decision, license_snapshot_ref, terms_hash, classification,
                    pdpl_check, attribution, row_count, columns_json, preview_json, notes_json,
                    created_at, updated_at
                ) VALUES (
                    :dataset_id, :source_id, :title, :publisher, :import_method, :review_status,
                    :human_review_decision, :license_snapshot_ref, :terms_hash, :classification,
                    :pdpl_check, :attribution, :row_count, :columns_json, :preview_json, :notes_json,
                    :created_at, :updated_at
                )
                ON CONFLICT(dataset_id) DO UPDATE SET
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
