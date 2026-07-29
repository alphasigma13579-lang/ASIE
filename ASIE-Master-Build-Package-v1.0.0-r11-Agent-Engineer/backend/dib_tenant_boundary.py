from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from backend.contracts import new_id, now_iso
from backend.dib_persistence import (
    DIB_PERSISTENCE_ID,
    DIBPersistenceError,
    DIBPersistenceStore,
    _json_dump,
    _reject_forbidden_payload,
)

DIB_TENANT_BOUNDARY_ID = "SEC-BETA-03-DIB-TENANT-OWNERSHIP-BOUNDARY-v1"
DIB_TENANT_SCHEMA_VERSION = 1
DIB_QUARANTINE_ORGANIZATION_ID = "__dib_quarantine__"
DIB_QUARANTINE_USER_ID = "__unknown__"
DIB_MIGRATION_USER_ID = "__migration__"


class DIBTenantBoundaryError(DIBPersistenceError):
    """Fail-closed tenant ownership violation without exposing object existence."""


@dataclass(frozen=True)
class DIBTenantContext:
    organization_id: str
    user_id: str
    principal_session_id: str

    def __post_init__(self) -> None:
        if not self.organization_id.strip():
            raise DIBTenantBoundaryError("dib_organization_context_required")
        if self.organization_id == DIB_QUARANTINE_ORGANIZATION_ID:
            raise DIBTenantBoundaryError("dib_quarantine_context_forbidden")
        if not self.user_id.strip():
            raise DIBTenantBoundaryError("dib_user_context_required")
        if not self.principal_session_id.strip():
            raise DIBTenantBoundaryError("dib_principal_session_required")


ProjectOrganizationResolver = Callable[[str], str | None]


class DIBTenantBoundary:
    """One authoritative tenant binding for every DIB session.

    Child DIB records inherit ownership through their mandatory session foreign
    key. New sessions cannot be inserted unless a tenant binding already exists
    in the same transaction. Pre-existing sessions are assigned only when their
    project ownership can be proven; all other rows are quarantined.
    """

    def __init__(
        self,
        store: DIBPersistenceStore,
        *,
        project_organization_resolver: ProjectOrganizationResolver | None = None,
    ) -> None:
        self.store = store
        self.project_organization_resolver = project_organization_resolver
        self.initialize()

    def _resolve_project_organization(self, project_id: str) -> str | None:
        if self.project_organization_resolver is None:
            return None
        try:
            resolved = self.project_organization_resolver(project_id)
        except Exception:
            return None
        organization_id = str(resolved or "").strip()
        if not organization_id or organization_id == DIB_QUARANTINE_ORGANIZATION_ID:
            return None
        return organization_id

    def initialize(self) -> None:
        connection = self.store._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dib_tenant_migrations (
                    version INTEGER PRIMARY KEY,
                    migration_id TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dib_tenant_bindings (
                    session_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES dib_sessions(session_id)
                        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dib_tenant_org_project
                    ON dib_tenant_bindings(organization_id, project_id, session_id)
                """
            )

            # Remove only package-owned immutability triggers while the idempotent
            # migration reconciles previously quarantined records. They are
            # recreated before the transaction commits.
            for trigger_name in (
                "trg_dib_session_requires_tenant_binding",
                "trg_dib_tenant_binding_immutable",
                "trg_dib_tenant_binding_delete_blocked",
                "trg_dib_session_project_immutable",
            ):
                connection.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")

            rows = connection.execute(
                """
                SELECT session.session_id, session.project_id, session.created_at,
                       binding.organization_id
                FROM dib_sessions session
                LEFT JOIN dib_tenant_bindings binding ON binding.session_id = session.session_id
                WHERE binding.session_id IS NULL
                   OR binding.organization_id = ?
                ORDER BY session.created_at, session.session_id
                """,
                (DIB_QUARANTINE_ORGANIZATION_ID,),
            ).fetchall()
            for row in rows:
                organization_id = self._resolve_project_organization(str(row["project_id"]))
                resolved_organization_id = organization_id or DIB_QUARANTINE_ORGANIZATION_ID
                created_by_user_id = DIB_MIGRATION_USER_ID if organization_id else DIB_QUARANTINE_USER_ID
                if row["organization_id"] is None:
                    connection.execute(
                        """
                        INSERT INTO dib_tenant_bindings (
                            session_id, organization_id, project_id, created_by_user_id, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            row["session_id"],
                            resolved_organization_id,
                            row["project_id"],
                            created_by_user_id,
                            row["created_at"],
                        ),
                    )
                elif organization_id:
                    connection.execute(
                        """
                        UPDATE dib_tenant_bindings
                        SET organization_id = ?, created_by_user_id = ?
                        WHERE session_id = ? AND organization_id = ?
                        """,
                        (
                            organization_id,
                            DIB_MIGRATION_USER_ID,
                            row["session_id"],
                            DIB_QUARANTINE_ORGANIZATION_ID,
                        ),
                    )

            connection.execute(
                """
                CREATE TRIGGER trg_dib_session_requires_tenant_binding
                BEFORE INSERT ON dib_sessions
                FOR EACH ROW
                WHEN NOT EXISTS (
                    SELECT 1 FROM dib_tenant_bindings binding
                    WHERE binding.session_id = NEW.session_id
                      AND binding.project_id = NEW.project_id
                      AND binding.organization_id != '__dib_quarantine__'
                )
                BEGIN
                    SELECT RAISE(ABORT, 'dib_tenant_binding_required');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER trg_dib_tenant_binding_immutable
                BEFORE UPDATE OF session_id, organization_id, project_id ON dib_tenant_bindings
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, 'dib_tenant_binding_immutable');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER trg_dib_tenant_binding_delete_blocked
                BEFORE DELETE ON dib_tenant_bindings
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, 'dib_tenant_binding_delete_blocked');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER trg_dib_session_project_immutable
                BEFORE UPDATE OF project_id ON dib_sessions
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, 'dib_session_project_immutable');
                END
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO dib_tenant_migrations (version, migration_id, applied_at)
                VALUES (?, ?, ?)
                """,
                (
                    DIB_TENANT_SCHEMA_VERSION,
                    "SEC-BETA-03-session-tenant-binding",
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
            schema_version = int(
                connection.execute(
                    "SELECT COALESCE(MAX(version), 0) AS version FROM dib_tenant_migrations"
                ).fetchone()["version"]
            )
            quarantine_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM dib_tenant_bindings
                    WHERE organization_id = ?
                    """,
                    (DIB_QUARANTINE_ORGANIZATION_ID,),
                ).fetchone()["count"]
            )
            migrated_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM dib_tenant_bindings
                    WHERE created_by_user_id = ?
                    """,
                    (DIB_MIGRATION_USER_ID,),
                ).fetchone()["count"]
            )
        return {
            "tenant_boundary_id": DIB_TENANT_BOUNDARY_ID,
            "schema_version": schema_version,
            "ownership_model": "session_binding_inherited_by_foreign_key",
            "organization_scope_required": True,
            "project_ownership_verified": self.project_organization_resolver is not None,
            "migrated_session_count": migrated_count,
            "quarantined_session_count": quarantine_count,
            "legacy_auto_assignment_blocked": True,
            "quarantine_context_forbidden": True,
            "cross_tenant_not_found_response": True,
            "frozen_runtime_files_mutated": False,
        }

    def require_project_access(self, context: DIBTenantContext, project_id: str) -> None:
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            raise DIBTenantBoundaryError("dib_project_not_found")
        if self.project_organization_resolver is None:
            raise DIBTenantBoundaryError("dib_project_ownership_resolver_required")
        owner = self._resolve_project_organization(normalized_project_id)
        if owner != context.organization_id:
            raise DIBTenantBoundaryError("dib_project_not_found")

    def start_session(self, context: DIBTenantContext, project_profile: dict[str, Any]) -> dict[str, Any]:
        _reject_forbidden_payload(project_profile, context="project_profile")
        project_id = str(project_profile.get("project_id") or "").strip()
        self.require_project_access(context, project_id)
        supplied_organization = str(project_profile.get("organization_id") or "").strip()
        if supplied_organization and supplied_organization != context.organization_id:
            raise DIBTenantBoundaryError("dib_project_not_found")

        session_id = new_id("dib_session")
        created_at = now_iso()
        governed_profile = {
            **dict(project_profile),
            "organization_id": context.organization_id,
        }
        with self.store._write_transaction() as connection:
            connection.execute(
                """
                INSERT INTO dib_tenant_bindings (
                    session_id, organization_id, project_id, created_by_user_id, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    context.organization_id,
                    project_id,
                    context.user_id,
                    created_at,
                ),
            )
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
                    _json_dump(governed_profile),
                    created_at,
                    created_at,
                    DIB_PERSISTENCE_ID,
                ),
            )
            self.store._append_event_row(
                connection,
                session_id,
                event_type="session.started",
                entity_type="dib_session",
                entity_id=session_id,
                payload=governed_profile,
            )
        return self.load_session(context, session_id)

    def require_session_access(self, context: DIBTenantContext, session_id: str) -> dict[str, Any]:
        with self.store._read_connection() as connection:
            row = connection.execute(
                """
                SELECT binding.session_id, binding.organization_id, binding.project_id,
                       binding.created_by_user_id, binding.created_at
                FROM dib_tenant_bindings binding
                JOIN dib_sessions session ON session.session_id = binding.session_id
                WHERE binding.session_id = ?
                  AND binding.organization_id = ?
                  AND binding.organization_id != ?
                """,
                (
                    session_id,
                    context.organization_id,
                    DIB_QUARANTINE_ORGANIZATION_ID,
                ),
            ).fetchone()
        if row is None:
            raise DIBTenantBoundaryError("dib_session_not_found")
        return dict(row)

    def load_session(self, context: DIBTenantContext, session_id: str) -> dict[str, Any]:
        binding = self.require_session_access(context, session_id)
        session = self.store.load_session(session_id)
        return {
            **session,
            "organization_id": binding["organization_id"],
            "created_by_user_id": binding["created_by_user_id"],
        }

    def list_session_ids_for_project(
        self,
        context: DIBTenantContext,
        project_id: str,
        *,
        include_closed: bool = False,
        limit: int = 10,
    ) -> list[str]:
        self.require_project_access(context, project_id)
        sql = """
            SELECT session.session_id
            FROM dib_sessions session
            JOIN dib_tenant_bindings binding ON binding.session_id = session.session_id
            WHERE binding.organization_id = ?
              AND binding.organization_id != ?
              AND binding.project_id = ?
        """
        if not include_closed:
            sql += " AND session.status != 'closed'"
        sql += " ORDER BY session.updated_at DESC, session.created_at DESC, session.session_id DESC LIMIT ?"
        with self.store._read_connection() as connection:
            rows = connection.execute(
                sql,
                (
                    context.organization_id,
                    DIB_QUARANTINE_ORGANIZATION_ID,
                    project_id,
                    int(limit),
                ),
            ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def append_event(
        self,
        context: DIBTenantContext,
        session_id: str,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> Any:
        self.require_session_access(context, session_id)
        return self.store._append_event(
            session_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )

    def load_events(self, context: DIBTenantContext, session_id: str) -> list[dict[str, Any]]:
        self.require_session_access(context, session_id)
        return self.store.list_events(session_id)

    def close_session(self, context: DIBTenantContext, session_id: str) -> dict[str, Any]:
        self.require_session_access(context, session_id)
        self.store.close_session(session_id)
        return self.load_session(context, session_id)

    def session_payload(self, context: DIBTenantContext, session_id: str) -> dict[str, Any]:
        return self.load_session(context, session_id)


def project_organization_resolver_from_repository(repository: Any) -> ProjectOrganizationResolver:
    def resolve(project_id: str) -> str | None:
        project = repository.get_project(project_id)
        return None if project is None else str(project.organization_id)

    return resolve
