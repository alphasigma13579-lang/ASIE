from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_module_adapters import DIB_MODULE_ADAPTERS_ID

DIB_PERSISTENCE_ID = "DIB-LIVE-002C-PERSISTENCE-v1"
DIB_PERSISTENCE_STATUS = "post_freeze_persistence"
DIB_PERSISTENCE_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

ALWAYS_FORBIDDEN_PAYLOAD_FIELDS = frozenset(
    {
        "raw_prompt",
        "api_key",
        "openai_api_key",
        "provider_config",
        "finance",
        "finance_result",
        "finance_inputs",
        "snapshot",
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "finance_wiring_enabled",
        "snapshot_wiring_enabled",
    }
)

DIB_SESSION_STATUSES = frozenset(
    {
        "active",
        "blueprint_saved",
        "manifest_approved",
        "manifest_blocked",
        "validation_passed",
        "validation_blocked",
        "closed",
    }
)


class DIBPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class DIBPersistenceEvent:
    event_id: str
    session_id: str
    event_type: str
    entity_type: str
    entity_id: str
    payload_hash: str
    created_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "payload_hash": self.payload_hash,
            "created_at": self.created_at,
        }


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_load(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dump(payload).encode("utf-8")).hexdigest()


def _reject_forbidden_payload(payload: Any, *, context: str) -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in ALWAYS_FORBIDDEN_PAYLOAD_FIELDS:
                    raise DIBPersistenceError(f"{context} contains forbidden field: {path}.{key_text}")
                if key_text in FORBIDDEN_TRUE_FLAGS and item is True:
                    raise DIBPersistenceError(f"{context} attempted to enable forbidden flag: {path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload, context)


class DIBPersistenceStore:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS dib_sessions (
                session_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                project_profile_json TEXT NOT NULL,
                current_blueprint_id TEXT,
                approved_manifest_id TEXT,
                validation_gate_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                adapter_id TEXT NOT NULL,
                external_fetch_enabled INTEGER NOT NULL DEFAULT 0,
                ai_provider_enabled INTEGER NOT NULL DEFAULT 0,
                finance_wiring_enabled INTEGER NOT NULL DEFAULT 0,
                snapshot_wiring_enabled INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS dib_blueprints (
                blueprint_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                contract_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS dib_approved_manifests (
                manifest_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                blueprint_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS dib_validation_gates (
                gate_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS dib_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def status(self) -> dict[str, Any]:
        table_count = self.connection.execute(
            "SELECT COUNT(*) AS count FROM sqlite_master WHERE type='table' AND name LIKE 'dib_%'"
        ).fetchone()["count"]
        return {
            "persistence_id": DIB_PERSISTENCE_ID,
            "status": DIB_PERSISTENCE_STATUS,
            "source": DIB_PERSISTENCE_SOURCE,
            "adapter_id": DIB_MODULE_ADAPTERS_ID,
            "db_path": self.db_path,
            "table_count": table_count,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_runtime_files_mutated": False,
        }

    def start_session(self, project_profile: dict[str, Any]) -> dict[str, Any]:
        _reject_forbidden_payload(project_profile, context="project_profile")
        project_id = str(project_profile.get("project_id") or "").strip()
        if not project_id:
            raise DIBPersistenceError("DIB session requires project_profile.project_id")
        session_id = new_id("dib_session")
        created_at = now_iso()
        self.connection.execute(
            """
            INSERT INTO dib_sessions (
                session_id, project_id, status, project_profile_json, created_at, updated_at,
                adapter_id, external_fetch_enabled, ai_provider_enabled, finance_wiring_enabled,
                snapshot_wiring_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
            """,
            (
                session_id,
                project_id,
                "active",
                _json_dump(dict(project_profile)),
                created_at,
                created_at,
                DIB_PERSISTENCE_ID,
            ),
        )
        self._append_event(
            session_id,
            event_type="session.started",
            entity_type="dib_session",
            entity_id=session_id,
            payload=dict(project_profile),
            commit=False,
        )
        self.connection.commit()
        return self.load_session(session_id)

    def save_blueprint(self, session_id: str, blueprint: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(session_id)
        _reject_forbidden_payload(blueprint, context="blueprint")
        contract_id = str(blueprint.get("contract_id") or "")
        if contract_id not in {"dynamic.input.blueprint.v1", "dib.draft.revision.v1"}:
            raise DIBPersistenceError("DIB persistence accepts only blueprint or draft revision contracts")
        blueprint_id = str(blueprint.get("blueprint_id") or "").strip()
        if not blueprint_id:
            raise DIBPersistenceError("DIB blueprint requires blueprint_id")
        project_id = str(blueprint.get("project_id") or session["project_id"])
        if project_id != session["project_id"]:
            raise DIBPersistenceError("DIB blueprint project_id does not match session")
        created_at = str(blueprint.get("created_at") or now_iso())
        self.connection.execute(
            """
            INSERT OR REPLACE INTO dib_blueprints (
                blueprint_id, session_id, project_id, revision, contract_id,
                payload_json, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                blueprint_id,
                session_id,
                project_id,
                int(blueprint.get("revision") or 1),
                contract_id,
                _json_dump(blueprint),
                _payload_hash(blueprint),
                created_at,
            ),
        )
        self._update_session(
            session_id,
            status="blueprint_saved",
            current_blueprint_id=blueprint_id,
            commit=False,
        )
        self._append_event(
            session_id,
            event_type="blueprint.saved",
            entity_type="dib_blueprint",
            entity_id=blueprint_id,
            payload=blueprint,
            commit=False,
        )
        self.connection.commit()
        return self.load_blueprint(blueprint_id)

    def save_approved_manifest(self, session_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(session_id)
        _reject_forbidden_payload(manifest, context="approved_manifest")
        if manifest.get("contract_id") != "approved.input.manifest.v1":
            raise DIBPersistenceError("DIB persistence requires approved.input.manifest.v1")
        manifest_id = str(manifest.get("manifest_id") or "").strip()
        blueprint_id = str(manifest.get("blueprint_id") or "").strip()
        if not manifest_id or not blueprint_id:
            raise DIBPersistenceError("Approved Input Manifest requires manifest_id and blueprint_id")
        project_id = str(manifest.get("project_id") or session["project_id"])
        if project_id != session["project_id"]:
            raise DIBPersistenceError("Approved Input Manifest project_id does not match session")
        status = str(manifest.get("status") or "blocked")
        if status not in {"approved", "blocked"}:
            raise DIBPersistenceError(f"unsupported manifest status: {status}")
        created_at = str(manifest.get("created_at") or now_iso())
        self.connection.execute(
            """
            INSERT OR REPLACE INTO dib_approved_manifests (
                manifest_id, session_id, project_id, blueprint_id, revision,
                status, payload_json, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest_id,
                session_id,
                project_id,
                blueprint_id,
                int(manifest.get("revision") or 1),
                status,
                _json_dump(manifest),
                _payload_hash(manifest),
                created_at,
            ),
        )
        self._update_session(
            session_id,
            status="manifest_approved" if status == "approved" else "manifest_blocked",
            approved_manifest_id=manifest_id,
            commit=False,
        )
        self._append_event(
            session_id,
            event_type="manifest.saved",
            entity_type="approved_input_manifest",
            entity_id=manifest_id,
            payload=manifest,
            commit=False,
        )
        self.connection.commit()
        return self.load_manifest(manifest_id)

    def save_validation_gate(self, session_id: str, gate: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(session_id)
        _reject_forbidden_payload(gate, context="validation_gate")
        if gate.get("contract_id") != "manifest.validation.v1":
            raise DIBPersistenceError("DIB persistence requires manifest.validation.v1")
        gate_id = str(gate.get("gate_id") or "").strip()
        manifest_id = str(gate.get("manifest_id") or session.get("approved_manifest_id") or "").strip()
        if not gate_id or not manifest_id:
            raise DIBPersistenceError("Manifest Validation Gate requires gate_id and manifest_id")
        status = str(gate.get("status") or "blocked")
        if status not in {"passed", "blocked"}:
            raise DIBPersistenceError(f"unsupported validation gate status: {status}")
        created_at = str(gate.get("created_at") or now_iso())
        self.connection.execute(
            """
            INSERT OR REPLACE INTO dib_validation_gates (
                gate_id, session_id, manifest_id, status, payload_json, payload_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gate_id,
                session_id,
                manifest_id,
                status,
                _json_dump(gate),
                _payload_hash(gate),
                created_at,
            ),
        )
        self._update_session(
            session_id,
            status="validation_passed" if status == "passed" else "validation_blocked",
            validation_gate_id=gate_id,
            commit=False,
        )
        self._append_event(
            session_id,
            event_type="validation_gate.saved",
            entity_type="manifest_validation_gate",
            entity_id=gate_id,
            payload=gate,
            commit=False,
        )
        self.connection.commit()
        return self.load_validation_gate(gate_id)

    def load_session(self, session_id: str) -> dict[str, Any]:
        row = self._require_session(session_id)
        result = self._session_row_to_public(row)
        if row["current_blueprint_id"]:
            result["current_blueprint"] = self.load_blueprint(row["current_blueprint_id"])["payload"]
        if row["approved_manifest_id"]:
            result["approved_manifest"] = self.load_manifest(row["approved_manifest_id"])["payload"]
        if row["validation_gate_id"]:
            result["validation_gate"] = self.load_validation_gate(row["validation_gate_id"])["payload"]
        return result

    def load_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM dib_blueprints WHERE blueprint_id = ?",
            (blueprint_id,),
        ).fetchone()
        if row is None:
            raise DIBPersistenceError(f"unknown DIB blueprint: {blueprint_id}")
        return self._entity_row_to_public(row, "blueprint_id")

    def load_manifest(self, manifest_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM dib_approved_manifests WHERE manifest_id = ?",
            (manifest_id,),
        ).fetchone()
        if row is None:
            raise DIBPersistenceError(f"unknown Approved Input Manifest: {manifest_id}")
        return self._entity_row_to_public(row, "manifest_id")

    def load_validation_gate(self, gate_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM dib_validation_gates WHERE gate_id = ?",
            (gate_id,),
        ).fetchone()
        if row is None:
            raise DIBPersistenceError(f"unknown Manifest Validation Gate: {gate_id}")
        return self._entity_row_to_public(row, "gate_id")

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        self._require_session(session_id)
        rows = self.connection.execute(
            "SELECT * FROM dib_events WHERE session_id = ? ORDER BY created_at, event_id",
            (session_id,),
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "payload_hash": row["payload_hash"],
                "payload": _json_load(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def close_session(self, session_id: str) -> dict[str, Any]:
        self._require_session(session_id)
        self._update_session(session_id, status="closed", commit=False)
        self._append_event(
            session_id,
            event_type="session.closed",
            entity_type="dib_session",
            entity_id=session_id,
            payload={"session_id": session_id, "status": "closed"},
            commit=False,
        )
        self.connection.commit()
        return self.load_session(session_id)

    def _require_session(self, session_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM dib_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise DIBPersistenceError(f"unknown DIB session: {session_id}")
        return row

    def _update_session(
        self,
        session_id: str,
        *,
        status: str,
        current_blueprint_id: str | None = None,
        approved_manifest_id: str | None = None,
        validation_gate_id: str | None = None,
        commit: bool = True,
    ) -> None:
        if status not in DIB_SESSION_STATUSES:
            raise DIBPersistenceError(f"unsupported DIB session status: {status}")
        row = self._require_session(session_id)
        self.connection.execute(
            """
            UPDATE dib_sessions
            SET status = ?,
                current_blueprint_id = ?,
                approved_manifest_id = ?,
                validation_gate_id = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                status,
                current_blueprint_id if current_blueprint_id is not None else row["current_blueprint_id"],
                approved_manifest_id if approved_manifest_id is not None else row["approved_manifest_id"],
                validation_gate_id if validation_gate_id is not None else row["validation_gate_id"],
                now_iso(),
                session_id,
            ),
        )
        if commit:
            self.connection.commit()

    def _append_event(
        self,
        session_id: str,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        commit: bool = True,
    ) -> DIBPersistenceEvent:
        _reject_forbidden_payload(payload, context=f"event:{event_type}")
        event = DIBPersistenceEvent(
            event_id=new_id("dib_event"),
            session_id=session_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_hash=_payload_hash(payload),
            created_at=now_iso(),
        )
        self.connection.execute(
            """
            INSERT INTO dib_events (
                event_id, session_id, event_type, entity_type, entity_id,
                payload_hash, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                session_id,
                event_type,
                entity_type,
                entity_id,
                event.payload_hash,
                _json_dump(payload),
                event.created_at,
            ),
        )
        if commit:
            self.connection.commit()
        return event

    def _session_row_to_public(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "session_id": row["session_id"],
            "project_id": row["project_id"],
            "status": row["status"],
            "project_profile": _json_load(row["project_profile_json"]),
            "current_blueprint_id": row["current_blueprint_id"],
            "approved_manifest_id": row["approved_manifest_id"],
            "validation_gate_id": row["validation_gate_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "adapter_id": row["adapter_id"],
            "external_fetch_enabled": bool(row["external_fetch_enabled"]),
            "ai_provider_enabled": bool(row["ai_provider_enabled"]),
            "finance_wiring_enabled": bool(row["finance_wiring_enabled"]),
            "snapshot_wiring_enabled": bool(row["snapshot_wiring_enabled"]),
        }

    def _entity_row_to_public(self, row: sqlite3.Row, identity_field: str) -> dict[str, Any]:
        return {
            identity_field: row[identity_field],
            "session_id": row["session_id"],
            "project_id": row["project_id"] if "project_id" in row.keys() else None,
            "status": row["status"] if "status" in row.keys() else None,
            "payload_hash": row["payload_hash"],
            "payload": _json_load(row["payload_json"]),
            "created_at": row["created_at"],
        }


def create_dib_persistence_store(db_path: str | Path = ":memory:") -> DIBPersistenceStore:
    return DIBPersistenceStore(db_path)
