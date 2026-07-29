from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_module_adapters import execute_dib_module_adapter
from backend.dib_persistence import (
    DIBPersistenceError,
    DIBPersistenceStore,
    _json_dump,
    _payload_hash,
)

DIB_SERVER_OWNED_MANIFEST_CHAIN_ID = "GOV-BETA-04-SERVER-OWNED-MANIFEST-CHAIN-v1"
DIB_SERVER_OWNED_MANIFEST_CHAIN_SCHEMA_VERSION = 1
SERVER_AUTHORITY = "asie.server.manifest.chain"


class DIBServerOwnedManifestChainError(DIBPersistenceError):
    pass


@dataclass(frozen=True)
class ManifestChainCommand:
    expected_parent_id: str | None = None
    expected_parent_payload_hash: str | None = None
    expected_revision: int | None = None
    approval_note: str = ""


class DIBServerOwnedManifestChain:
    """Server-owned Blueprint -> Manifest -> Validation Gate lineage.

    Clients submit commands and optimistic concurrency expectations only.
    Final Manifest and Gate payloads are generated from persisted parents.
    SQLite triggers reject persistence without a matching one-time server
    authorization bound to the child payload hash and its persisted parent.
    """

    _MANIFEST_COMMAND_FIELDS = frozenset(
        {
            "expected_blueprint_id",
            "expected_blueprint_payload_hash",
            "expected_revision",
            "approval_note",
        }
    )
    _GATE_COMMAND_FIELDS = frozenset(
        {
            "expected_manifest_id",
            "expected_manifest_payload_hash",
            "expected_revision",
        }
    )
    _CLIENT_OWNED_FIELDS = frozenset(
        {
            "manifest",
            "gate",
            "blueprint",
            "manifest_id",
            "gate_id",
            "blueprint_id",
            "contract_id",
            "project_id",
            "revision",
            "status",
            "items",
            "normalized_inputs",
            "blockers",
            "lineage",
            "server_authority",
        }
    )

    def __init__(self, store: DIBPersistenceStore) -> None:
        self.store = store
        self.initialize()

    def initialize(self) -> None:
        connection = self.store._connect()
        try:
            connection.executescript(
                """
                BEGIN IMMEDIATE;

                CREATE TABLE IF NOT EXISTS dib_manifest_chain_migrations (
                    version INTEGER PRIMARY KEY,
                    migration_id TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dib_manifest_chain_authorizations (
                    authorization_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL CHECK (entity_type IN ('manifest', 'gate')),
                    entity_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    parent_entity_id TEXT NOT NULL,
                    parent_payload_hash TEXT NOT NULL,
                    expected_payload_hash TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    consumed_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS dib_manifest_chain_quarantine (
                    quarantine_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    manifest_id TEXT,
                    gate_id TEXT,
                    reason TEXT NOT NULL,
                    quarantined_at TEXT NOT NULL,
                    UNIQUE(session_id, manifest_id, gate_id, reason)
                );

                CREATE INDEX IF NOT EXISTS idx_dib_manifest_chain_auth_session
                    ON dib_manifest_chain_authorizations(session_id, entity_type, created_at);

                CREATE TRIGGER IF NOT EXISTS trg_dib_manifest_requires_server_authority
                BEFORE INSERT ON dib_approved_manifests
                FOR EACH ROW
                WHEN NOT EXISTS (
                    SELECT 1
                    FROM dib_manifest_chain_authorizations authorization
                    WHERE authorization.entity_type = 'manifest'
                      AND authorization.entity_id = NEW.manifest_id
                      AND authorization.session_id = NEW.session_id
                      AND authorization.project_id = NEW.project_id
                      AND authorization.parent_entity_id = NEW.blueprint_id
                      AND authorization.expected_payload_hash = NEW.payload_hash
                      AND authorization.consumed_at IS NULL
                )
                BEGIN
                    SELECT RAISE(ABORT, 'dib_server_manifest_authority_required');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dib_gate_requires_server_authority
                BEFORE INSERT ON dib_validation_gates
                FOR EACH ROW
                WHEN NOT EXISTS (
                    SELECT 1
                    FROM dib_manifest_chain_authorizations authorization
                    WHERE authorization.entity_type = 'gate'
                      AND authorization.entity_id = NEW.gate_id
                      AND authorization.session_id = NEW.session_id
                      AND authorization.parent_entity_id = NEW.manifest_id
                      AND authorization.expected_payload_hash = NEW.payload_hash
                      AND authorization.consumed_at IS NULL
                )
                BEGIN
                    SELECT RAISE(ABORT, 'dib_server_gate_authority_required');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dib_manifest_immutable
                BEFORE UPDATE ON dib_approved_manifests
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, 'dib_manifest_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dib_gate_immutable
                BEFORE UPDATE ON dib_validation_gates
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, 'dib_validation_gate_immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dib_blueprint_change_invalidates_chain
                AFTER UPDATE OF current_blueprint_id ON dib_sessions
                FOR EACH ROW
                WHEN COALESCE(OLD.current_blueprint_id, '') != COALESCE(NEW.current_blueprint_id, '')
                BEGIN
                    UPDATE dib_sessions
                    SET approved_manifest_id = NULL,
                        validation_gate_id = NULL,
                        status = CASE WHEN NEW.current_blueprint_id IS NULL THEN 'active' ELSE 'blueprint_saved' END
                    WHERE session_id = NEW.session_id;
                END;

                CREATE TRIGGER IF NOT EXISTS trg_dib_manifest_change_invalidates_gate
                AFTER UPDATE OF approved_manifest_id ON dib_sessions
                FOR EACH ROW
                WHEN COALESCE(OLD.approved_manifest_id, '') != COALESCE(NEW.approved_manifest_id, '')
                BEGIN
                    UPDATE dib_sessions
                    SET validation_gate_id = NULL
                    WHERE session_id = NEW.session_id;
                END;
                """
            )

            migrated = connection.execute(
                "SELECT 1 FROM dib_manifest_chain_migrations WHERE version = ?",
                (DIB_SERVER_OWNED_MANIFEST_CHAIN_SCHEMA_VERSION,),
            ).fetchone()
            if migrated is None:
                rows = connection.execute(
                    """
                    SELECT session_id, approved_manifest_id, validation_gate_id
                    FROM dib_sessions
                    WHERE approved_manifest_id IS NOT NULL OR validation_gate_id IS NOT NULL
                    """
                ).fetchall()
                for row in rows:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO dib_manifest_chain_quarantine (
                            quarantine_id, session_id, manifest_id, gate_id, reason, quarantined_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_id("dib_chain_quarantine"),
                            row["session_id"],
                            row["approved_manifest_id"],
                            row["validation_gate_id"],
                            "pre_gov_beta_04_unproven_server_authority",
                            now_iso(),
                        ),
                    )
                connection.execute(
                    """
                    UPDATE dib_sessions
                    SET approved_manifest_id = NULL,
                        validation_gate_id = NULL,
                        status = CASE WHEN current_blueprint_id IS NULL THEN 'active' ELSE 'blueprint_saved' END
                    WHERE approved_manifest_id IS NOT NULL OR validation_gate_id IS NOT NULL
                    """
                )
                connection.execute(
                    """
                    INSERT INTO dib_manifest_chain_migrations (version, migration_id, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        DIB_SERVER_OWNED_MANIFEST_CHAIN_SCHEMA_VERSION,
                        "GOV-BETA-04-server-owned-manifest-chain",
                        now_iso(),
                    ),
                )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def status(self) -> dict[str, Any]:
        with self.store._read_connection() as connection:
            quarantine_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dib_manifest_chain_quarantine"
                ).fetchone()["count"]
            )
            authorization_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dib_manifest_chain_authorizations WHERE consumed_at IS NOT NULL"
                ).fetchone()["count"]
            )
        return {
            "manifest_chain_id": DIB_SERVER_OWNED_MANIFEST_CHAIN_ID,
            "schema_version": DIB_SERVER_OWNED_MANIFEST_CHAIN_SCHEMA_VERSION,
            "authority": SERVER_AUTHORITY,
            "client_owned_manifest_rejected": True,
            "client_owned_gate_rejected": True,
            "parent_hash_required": True,
            "one_time_authorization_required": True,
            "legacy_chain_quarantine_count": quarantine_count,
            "consumed_authorization_count": authorization_count,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_runtime_files_mutated": False,
        }

    def build_manifest(
        self,
        session_id: str,
        command_payload: dict[str, Any] | None,
        *,
        actor_user_id: str,
    ) -> dict[str, Any]:
        command = self._parse_manifest_command(command_payload or {})
        session = self.store.load_session(session_id)
        blueprint_id = str(session.get("current_blueprint_id") or "").strip()
        if not blueprint_id:
            raise DIBServerOwnedManifestChainError("approved_manifest_requires_persisted_blueprint")
        blueprint_record = self.store.load_blueprint(blueprint_id)
        blueprint = dict(blueprint_record["payload"])
        self._assert_parent(
            expected_id=command.expected_parent_id,
            expected_hash=command.expected_parent_payload_hash,
            expected_revision=command.expected_revision,
            actual_id=blueprint_id,
            actual_hash=str(blueprint_record["payload_hash"]),
            actual_revision=int(blueprint.get("revision") or 1),
            stale_code="stale_blueprint_lineage",
        )
        if blueprint_record["session_id"] != session_id or blueprint_record["project_id"] != session["project_id"]:
            raise DIBServerOwnedManifestChainError("blueprint_session_lineage_mismatch")

        manifest = execute_dib_module_adapter(
            "module.approved_input_manifest",
            {"blueprint": blueprint},
        )
        manifest = {
            **manifest,
            "project_id": session["project_id"],
            "blueprint_id": blueprint_id,
            "revision": int(blueprint.get("revision") or 1),
            "blueprint_payload_hash": str(blueprint_record["payload_hash"]),
            "approved_by_user_id": actor_user_id,
            "approval_note": command.approval_note,
            "server_authority": SERVER_AUTHORITY,
            "lineage": {
                "session_id": session_id,
                "project_id": session["project_id"],
                "blueprint_id": blueprint_id,
                "blueprint_payload_hash": str(blueprint_record["payload_hash"]),
                "blueprint_revision": int(blueprint.get("revision") or 1),
            },
        }
        self._persist_manifest(session, blueprint_record, manifest, actor_user_id)
        return self.store.load_manifest(str(manifest["manifest_id"]))

    def build_gate(
        self,
        session_id: str,
        command_payload: dict[str, Any] | None,
        *,
        actor_user_id: str,
    ) -> dict[str, Any]:
        command = self._parse_gate_command(command_payload or {})
        session = self.store.load_session(session_id)
        manifest_id = str(session.get("approved_manifest_id") or "").strip()
        if not manifest_id:
            raise DIBServerOwnedManifestChainError("validation_gate_requires_persisted_manifest")
        manifest_record = self.store.load_manifest(manifest_id)
        manifest = dict(manifest_record["payload"])
        self._assert_parent(
            expected_id=command.expected_parent_id,
            expected_hash=command.expected_parent_payload_hash,
            expected_revision=command.expected_revision,
            actual_id=manifest_id,
            actual_hash=str(manifest_record["payload_hash"]),
            actual_revision=int(manifest.get("revision") or 1),
            stale_code="stale_manifest_lineage",
        )
        if manifest_record["session_id"] != session_id or manifest_record["project_id"] != session["project_id"]:
            raise DIBServerOwnedManifestChainError("manifest_session_lineage_mismatch")

        gate = execute_dib_module_adapter(
            "module.manifest_validation_gate",
            {"manifest": manifest},
        )
        gate = {
            **gate,
            "manifest_id": manifest_id,
            "manifest_payload_hash": str(manifest_record["payload_hash"]),
            "blueprint_id": manifest.get("blueprint_id"),
            "blueprint_payload_hash": manifest.get("blueprint_payload_hash"),
            "validated_by_user_id": actor_user_id,
            "server_authority": SERVER_AUTHORITY,
            "lineage": {
                "session_id": session_id,
                "project_id": session["project_id"],
                "manifest_id": manifest_id,
                "manifest_payload_hash": str(manifest_record["payload_hash"]),
                "blueprint_id": manifest.get("blueprint_id"),
                "blueprint_payload_hash": manifest.get("blueprint_payload_hash"),
                "revision": int(manifest.get("revision") or 1),
            },
        }
        self._persist_gate(session, manifest_record, gate, actor_user_id)
        return self.store.load_validation_gate(str(gate["gate_id"]))

    def _persist_manifest(
        self,
        session: dict[str, Any],
        blueprint_record: dict[str, Any],
        manifest: dict[str, Any],
        actor_user_id: str,
    ) -> None:
        manifest_id = str(manifest["manifest_id"])
        manifest_hash = _payload_hash(manifest)
        created_at = str(manifest.get("created_at") or now_iso())
        with self.store._write_transaction() as connection:
            current = self.store._require_session_row(connection, session["session_id"])
            blueprint_row = connection.execute(
                "SELECT * FROM dib_blueprints WHERE blueprint_id = ? AND session_id = ?",
                (manifest["blueprint_id"], session["session_id"]),
            ).fetchone()
            if (
                blueprint_row is None
                or current["current_blueprint_id"] != manifest["blueprint_id"]
                or blueprint_row["payload_hash"] != blueprint_record["payload_hash"]
            ):
                raise DIBServerOwnedManifestChainError("stale_blueprint_lineage")
            authorization_id = self._authorize(
                connection,
                entity_type="manifest",
                entity_id=manifest_id,
                session_id=session["session_id"],
                project_id=session["project_id"],
                parent_entity_id=manifest["blueprint_id"],
                parent_payload_hash=str(blueprint_record["payload_hash"]),
                expected_payload_hash=manifest_hash,
                actor_user_id=actor_user_id,
            )
            connection.execute(
                """
                INSERT INTO dib_approved_manifests (
                    manifest_id, session_id, project_id, blueprint_id, revision,
                    status, payload_json, payload_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest_id,
                    session["session_id"],
                    session["project_id"],
                    manifest["blueprint_id"],
                    int(manifest.get("revision") or 1),
                    manifest["status"],
                    _json_dump(manifest),
                    manifest_hash,
                    created_at,
                ),
            )
            self.store._update_session_row(
                connection,
                session["session_id"],
                status="manifest_approved" if manifest["status"] == "approved" else "manifest_blocked",
                approved_manifest_id=manifest_id,
            )
            self.store._append_event_row(
                connection,
                session["session_id"],
                event_type="manifest.server_generated",
                entity_type="approved_input_manifest",
                entity_id=manifest_id,
                payload=manifest,
            )
            connection.execute(
                "UPDATE dib_manifest_chain_authorizations SET consumed_at = ? WHERE authorization_id = ?",
                (now_iso(), authorization_id),
            )

    def _persist_gate(
        self,
        session: dict[str, Any],
        manifest_record: dict[str, Any],
        gate: dict[str, Any],
        actor_user_id: str,
    ) -> None:
        gate_id = str(gate["gate_id"])
        gate_hash = _payload_hash(gate)
        created_at = str(gate.get("created_at") or now_iso())
        with self.store._write_transaction() as connection:
            current = self.store._require_session_row(connection, session["session_id"])
            manifest_row = connection.execute(
                "SELECT * FROM dib_approved_manifests WHERE manifest_id = ? AND session_id = ?",
                (gate["manifest_id"], session["session_id"]),
            ).fetchone()
            if (
                manifest_row is None
                or current["approved_manifest_id"] != gate["manifest_id"]
                or manifest_row["payload_hash"] != manifest_record["payload_hash"]
            ):
                raise DIBServerOwnedManifestChainError("stale_manifest_lineage")
            authorization_id = self._authorize(
                connection,
                entity_type="gate",
                entity_id=gate_id,
                session_id=session["session_id"],
                project_id=session["project_id"],
                parent_entity_id=gate["manifest_id"],
                parent_payload_hash=str(manifest_record["payload_hash"]),
                expected_payload_hash=gate_hash,
                actor_user_id=actor_user_id,
            )
            connection.execute(
                """
                INSERT INTO dib_validation_gates (
                    gate_id, session_id, manifest_id, status, payload_json, payload_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gate_id,
                    session["session_id"],
                    gate["manifest_id"],
                    gate["status"],
                    _json_dump(gate),
                    gate_hash,
                    created_at,
                ),
            )
            self.store._update_session_row(
                connection,
                session["session_id"],
                status="validation_passed" if gate["status"] == "passed" else "validation_blocked",
                validation_gate_id=gate_id,
            )
            self.store._append_event_row(
                connection,
                session["session_id"],
                event_type="validation_gate.server_generated",
                entity_type="manifest_validation_gate",
                entity_id=gate_id,
                payload=gate,
            )
            connection.execute(
                "UPDATE dib_manifest_chain_authorizations SET consumed_at = ? WHERE authorization_id = ?",
                (now_iso(), authorization_id),
            )

    def _authorize(
        self,
        connection: Any,
        *,
        entity_type: str,
        entity_id: str,
        session_id: str,
        project_id: str,
        parent_entity_id: str,
        parent_payload_hash: str,
        expected_payload_hash: str,
        actor_user_id: str,
    ) -> str:
        authorization_id = new_id("dib_chain_authority")
        connection.execute(
            """
            INSERT INTO dib_manifest_chain_authorizations (
                authorization_id, entity_type, entity_id, session_id, project_id,
                parent_entity_id, parent_payload_hash, expected_payload_hash,
                created_by_user_id, created_at, consumed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                authorization_id,
                entity_type,
                entity_id,
                session_id,
                project_id,
                parent_entity_id,
                parent_payload_hash,
                expected_payload_hash,
                actor_user_id,
                now_iso(),
            ),
        )
        return authorization_id

    def _parse_manifest_command(self, payload: dict[str, Any]) -> ManifestChainCommand:
        self._reject_client_owned_payload(
            payload,
            self._MANIFEST_COMMAND_FIELDS,
            "client_owned_manifest_rejected",
        )
        return ManifestChainCommand(
            expected_parent_id=self._optional_text(payload.get("expected_blueprint_id")),
            expected_parent_payload_hash=self._optional_text(payload.get("expected_blueprint_payload_hash")),
            expected_revision=self._optional_int(payload.get("expected_revision")),
            approval_note=str(payload.get("approval_note") or "").strip(),
        )

    def _parse_gate_command(self, payload: dict[str, Any]) -> ManifestChainCommand:
        self._reject_client_owned_payload(
            payload,
            self._GATE_COMMAND_FIELDS,
            "client_owned_gate_rejected",
        )
        return ManifestChainCommand(
            expected_parent_id=self._optional_text(payload.get("expected_manifest_id")),
            expected_parent_payload_hash=self._optional_text(payload.get("expected_manifest_payload_hash")),
            expected_revision=self._optional_int(payload.get("expected_revision")),
        )

    def _reject_client_owned_payload(
        self,
        payload: dict[str, Any],
        allowed_fields: frozenset[str],
        error_code: str,
    ) -> None:
        keys = set(payload)
        if keys & self._CLIENT_OWNED_FIELDS or keys - allowed_fields:
            raise DIBServerOwnedManifestChainError(error_code)

    @staticmethod
    def _assert_parent(
        *,
        expected_id: str | None,
        expected_hash: str | None,
        expected_revision: int | None,
        actual_id: str,
        actual_hash: str,
        actual_revision: int,
        stale_code: str,
    ) -> None:
        if expected_id is not None and expected_id != actual_id:
            raise DIBServerOwnedManifestChainError(stale_code)
        if expected_hash is not None and expected_hash != actual_hash:
            raise DIBServerOwnedManifestChainError(stale_code)
        if expected_revision is not None and expected_revision != actual_revision:
            raise DIBServerOwnedManifestChainError(stale_code)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise DIBServerOwnedManifestChainError("invalid_expected_revision") from exc
