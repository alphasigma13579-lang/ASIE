from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from backend.contracts import new_id, now_iso
from backend.dib_module_adapters import DIB_MODULE_ADAPTERS_ID

DIB_PERSISTENCE_ID = "DIB-LIVE-002C-PERSISTENCE-v1"
DIB_PERSISTENCE_STATUS = "post_freeze_transaction_safe_persistence"
DIB_PERSISTENCE_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"
DIB_SCHEMA_VERSION = 1
DIB_SQLITE_BUSY_TIMEOUT_MS = 30_000

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
    """SQLite persistence with one connection per operation or transaction.

    The store object may be shared by a ThreadingHTTPServer. SQLite connections
    are never shared across threads. The default ``:memory:`` API is preserved
    through a private temporary SQLite file so separate connections see one
    ephemeral database without relying on a cross-thread keeper connection.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.requested_db_path = str(db_path)
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        if self.requested_db_path == ":memory:":
            self._temporary_directory = tempfile.TemporaryDirectory(prefix="asie-dib-")
            self._database_path = str(Path(self._temporary_directory.name) / "dib.sqlite3")
            self.storage_mode = "ephemeral_file"
        else:
            self._database_path = self.requested_db_path
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
            self.storage_mode = "sqlite_file"
        self.db_path = self.requested_db_path
        self._lifecycle_lock = threading.RLock()
        self._closed = False
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        with self._lifecycle_lock:
            if self._closed:
                raise DIBPersistenceError("DIB persistence store is closed")
            database_path = self._database_path
        connection = sqlite3.connect(
            database_path,
            timeout=DIB_SQLITE_BUSY_TIMEOUT_MS / 1000,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(f"PRAGMA busy_timeout={DIB_SQLITE_BUSY_TIMEOUT_MS}")
        return connection

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write_transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dib_schema_migrations (
                    version INTEGER PRIMARY KEY,
                    migration_id TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                );

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

                CREATE INDEX IF NOT EXISTS idx_dib_sessions_project_updated
                    ON dib_sessions(project_id, updated_at DESC, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_dib_events_session_created
                    ON dib_events(session_id, created_at, event_id);
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO dib_schema_migrations (version, migration_id, applied_at)
                VALUES (?, ?, ?)
                """,
                (DIB_SCHEMA_VERSION, "STAB-BETA-02-initial-transaction-safe-registry", now_iso()),
            )
        finally:
            connection.close()

    def close(self) -> None:
        temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            temporary_directory = self._temporary_directory
            self._temporary_directory = None
        if temporary_directory is not None:
            temporary_directory.cleanup()

    def status(self) -> dict[str, Any]:
        with self._read_connection() as connection:
            table_count = connection.execute(
                "SELECT COUNT(*) AS count FROM sqlite_master WHERE type='table' AND name LIKE 'dib_%'"
            ).fetchone()["count"]
            schema_version = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM dib_schema_migrations"
            ).fetchone()["version"]
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
        return {
            "persistence_id": DIB_PERSISTENCE_ID,
            "status": DIB_PERSISTENCE_STATUS,
            "source": DIB_PERSISTENCE_SOURCE,
            "adapter_id": DIB_MODULE_ADAPTERS_ID,
            "db_path": self.db_path,
            "storage_mode": self.storage_mode,
            "connection_scope": "per_operation_or_transaction",
            "schema_version": int(schema_version),
            "table_count": int(table_count),
            "journal_mode": str(journal_mode).lower(),
            "foreign_keys_enabled": bool(foreign_keys),
            "busy_timeout_ms": int(busy_timeout),
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
        with self._write_transaction() as connection:
            connection.execute(
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
            self._append_event_row(
                connection,
                session_id,
                event_type="session.started",
                entity_type="dib_session",
                entity_id=session_id,
                payload=dict(project_profile),
            )
        return self.load_session(session_id)

    def save_blueprint(self, session_id: str, blueprint: dict[str, Any]) -> dict[str, Any]:
        _reject_forbidden_payload(blueprint, context="blueprint")
        contract_id = str(blueprint.get("contract_id") or "")
        if contract_id not in {"dynamic.input.blueprint.v1", "dib.draft.revision.v1"}:
            raise DIBPersistenceError("DIB persistence accepts only blueprint or draft revision contracts")
        blueprint_id = str(blueprint.get("blueprint_id") or "").strip()
        if not blueprint_id:
            raise DIBPersistenceError("DIB blueprint requires blueprint_id")
        created_at = str(blueprint.get("created_at") or now_iso())
        with self._write_transaction() as connection:
            session = self._require_session_row(connection, session_id)
            project_id = str(blueprint.get("project_id") or session["project_id"])
            if project_id != session["project_id"]:
                raise DIBPersistenceError("DIB blueprint project_id does not match session")
            connection.execute(
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
            self._update_session_row(
                connection,
                session_id,
                status="blueprint_saved",
                current_blueprint_id=blueprint_id,
            )
            self._append_event_row(
                connection,
                session_id,
                event_type="blueprint.saved",
                entity_type="dib_blueprint",
                entity_id=blueprint_id,
                payload=blueprint,
            )
        return self.load_blueprint(blueprint_id)

    def save_approved_manifest(self, session_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        _reject_forbidden_payload(manifest, context="approved_manifest")
        if manifest.get("contract_id") != "approved.input.manifest.v1":
            raise DIBPersistenceError("DIB persistence requires approved.input.manifest.v1")
        manifest_id = str(manifest.get("manifest_id") or "").strip()
        blueprint_id = str(manifest.get("blueprint_id") or "").strip()
        if not manifest_id or not blueprint_id:
            raise DIBPersistenceError("Approved Input Manifest requires manifest_id and blueprint_id")
        status = str(manifest.get("status") or "blocked")
        if status not in {"approved", "blocked"}:
            raise DIBPersistenceError(f"unsupported manifest status: {status}")
        created_at = str(manifest.get("created_at") or now_iso())
        with self._write_transaction() as connection:
            session = self._require_session_row(connection, session_id)
            project_id = str(manifest.get("project_id") or session["project_id"])
            if project_id != session["project_id"]:
                raise DIBPersistenceError("Approved Input Manifest project_id does not match session")
            connection.execute(
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
            self._update_session_row(
                connection,
                session_id,
                status="manifest_approved" if status == "approved" else "manifest_blocked",
                approved_manifest_id=manifest_id,
            )
            self._append_event_row(
                connection,
                session_id,
                event_type="manifest.saved",
                entity_type="approved_input_manifest",
                entity_id=manifest_id,
                payload=manifest,
            )
        return self.load_manifest(manifest_id)

    def save_validation_gate(self, session_id: str, gate: dict[str, Any]) -> dict[str, Any]:
        _reject_forbidden_payload(gate, context="validation_gate")
        if gate.get("contract_id") != "manifest.validation.v1":
            raise DIBPersistenceError("DIB persistence requires manifest.validation.v1")
        gate_id = str(gate.get("gate_id") or "").strip()
        if not gate_id:
            raise DIBPersistenceError("Manifest Validation Gate requires gate_id and manifest_id")
        status = str(gate.get("status") or "blocked")
        if status not in {"passed", "blocked"}:
            raise DIBPersistenceError(f"unsupported validation gate status: {status}")
        created_at = str(gate.get("created_at") or now_iso())
        with self._write_transaction() as connection:
            session = self._require_session_row(connection, session_id)
            manifest_id = str(gate.get("manifest_id") or session["approved_manifest_id"] or "").strip()
            if not manifest_id:
                raise DIBPersistenceError("Manifest Validation Gate requires gate_id and manifest_id")
            connection.execute(
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
            self._update_session_row(
                connection,
                session_id,
                status="validation_passed" if status == "passed" else "validation_blocked",
                validation_gate_id=gate_id,
            )
            self._append_event_row(
                connection,
                session_id,
                event_type="validation_gate.saved",
                entity_type="manifest_validation_gate",
                entity_id=gate_id,
                payload=gate,
            )
        return self.load_validation_gate(gate_id)

    def load_session(self, session_id: str) -> dict[str, Any]:
        with self._read_connection() as connection:
            row = self._require_session_row(connection, session_id)
            result = self._session_row_to_public(row)
            if row["current_blueprint_id"]:
                result["current_blueprint"] = self._load_entity_row(
                    connection,
                    "dib_blueprints",
                    "blueprint_id",
                    row["current_blueprint_id"],
                    "unknown DIB blueprint",
                )["payload"]
            if row["approved_manifest_id"]:
                result["approved_manifest"] = self._load_entity_row(
                    connection,
                    "dib_approved_manifests",
                    "manifest_id",
                    row["approved_manifest_id"],
                    "unknown Approved Input Manifest",
                )["payload"]
            if row["validation_gate_id"]:
                result["validation_gate"] = self._load_entity_row(
                    connection,
                    "dib_validation_gates",
                    "gate_id",
                    row["validation_gate_id"],
                    "unknown Manifest Validation Gate",
                )["payload"]
            return result

    def load_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        with self._read_connection() as connection:
            return self._load_entity_row(
                connection,
                "dib_blueprints",
                "blueprint_id",
                blueprint_id,
                "unknown DIB blueprint",
            )

    def load_manifest(self, manifest_id: str) -> dict[str, Any]:
        with self._read_connection() as connection:
            return self._load_entity_row(
                connection,
                "dib_approved_manifests",
                "manifest_id",
                manifest_id,
                "unknown Approved Input Manifest",
            )

    def load_validation_gate(self, gate_id: str) -> dict[str, Any]:
        with self._read_connection() as connection:
            return self._load_entity_row(
                connection,
                "dib_validation_gates",
                "gate_id",
                gate_id,
                "unknown Manifest Validation Gate",
            )

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        with self._read_connection() as connection:
            self._require_session_row(connection, session_id)
            rows = connection.execute(
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

    def list_session_ids_for_project(
        self,
        project_id: str,
        *,
        include_closed: bool = False,
        limit: int = 10,
    ) -> list[str]:
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            raise DIBPersistenceError("DIB session query requires project_id")
        sql = """
            SELECT session_id
            FROM dib_sessions
            WHERE project_id = ?
        """
        if not include_closed:
            sql += " AND status != 'closed'"
        sql += " ORDER BY updated_at DESC, created_at DESC, session_id DESC LIMIT ?"
        with self._read_connection() as connection:
            rows = connection.execute(sql, (normalized_project_id, int(limit))).fetchall()
        return [str(row["session_id"]) for row in rows]

    def close_session(self, session_id: str) -> dict[str, Any]:
        with self._write_transaction() as connection:
            self._require_session_row(connection, session_id)
            self._update_session_row(connection, session_id, status="closed")
            self._append_event_row(
                connection,
                session_id,
                event_type="session.closed",
                entity_type="dib_session",
                entity_id=session_id,
                payload={"session_id": session_id, "status": "closed"},
            )
        return self.load_session(session_id)

    def _require_session(self, session_id: str) -> sqlite3.Row:
        with self._read_connection() as connection:
            return self._require_session_row(connection, session_id)

    @staticmethod
    def _require_session_row(connection: sqlite3.Connection, session_id: str) -> sqlite3.Row:
        row = connection.execute(
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
        if not commit:
            raise DIBPersistenceError("transaction connection required when commit is false")
        with self._write_transaction() as connection:
            self._update_session_row(
                connection,
                session_id,
                status=status,
                current_blueprint_id=current_blueprint_id,
                approved_manifest_id=approved_manifest_id,
                validation_gate_id=validation_gate_id,
            )

    def _update_session_row(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        *,
        status: str,
        current_blueprint_id: str | None = None,
        approved_manifest_id: str | None = None,
        validation_gate_id: str | None = None,
    ) -> None:
        if status not in DIB_SESSION_STATUSES:
            raise DIBPersistenceError(f"unsupported DIB session status: {status}")
        row = self._require_session_row(connection, session_id)
        connection.execute(
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
        if not commit:
            raise DIBPersistenceError("transaction connection required when commit is false")
        with self._write_transaction() as connection:
            self._require_session_row(connection, session_id)
            return self._append_event_row(
                connection,
                session_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
            )

    def _append_event_row(
        self,
        connection: sqlite3.Connection,
        session_id: str,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
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
        connection.execute(
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
        return event

    def _load_entity_row(
        self,
        connection: sqlite3.Connection,
        table: str,
        identity_field: str,
        identity_value: str,
        error_prefix: str,
    ) -> dict[str, Any]:
        allowed_tables = {
            "dib_blueprints": "blueprint_id",
            "dib_approved_manifests": "manifest_id",
            "dib_validation_gates": "gate_id",
        }
        if allowed_tables.get(table) != identity_field:
            raise DIBPersistenceError("unsupported DIB entity table")
        row = connection.execute(
            f"SELECT * FROM {table} WHERE {identity_field} = ?",
            (identity_value,),
        ).fetchone()
        if row is None:
            raise DIBPersistenceError(f"{error_prefix}: {identity_value}")
        return self._entity_row_to_public(row, identity_field)

    @staticmethod
    def _session_row_to_public(row: sqlite3.Row) -> dict[str, Any]:
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

    @staticmethod
    def _entity_row_to_public(row: sqlite3.Row, identity_field: str) -> dict[str, Any]:
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
