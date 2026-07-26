from __future__ import annotations

from typing import Any

from backend.dib_persistence import DIBPersistenceError, DIBPersistenceStore

DIB_SESSION_CONTINUITY_ID = "DIB-COMPLETION-PACKAGE-A-SESSION-CONTINUITY-v1"
DIB_SESSION_CONTINUITY_STATUS = "post_freeze_session_continuity"
DIB_SESSION_CONTINUITY_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

MAX_DIB_SESSION_QUERY_LIMIT = 25


def _normalize_limit(limit: int | str | None) -> int:
    try:
        numeric = int(limit or 10)
    except (TypeError, ValueError) as exc:
        raise DIBPersistenceError("invalid DIB session query limit") from exc
    return min(MAX_DIB_SESSION_QUERY_LIMIT, max(1, numeric))


def list_dib_sessions_for_project(
    store: DIBPersistenceStore,
    project_id: str,
    *,
    include_closed: bool = False,
    limit: int | str | None = 10,
) -> list[dict[str, Any]]:
    """Return latest persisted DIB sessions for one ASIE project.

    This helper is intentionally read-only. It does not mutate AAS frozen files,
    does not execute Finance, does not assemble Snapshot, and does not fetch any
    external source. Full session records are loaded through DIBPersistenceStore
    so Blueprint / Manifest / Validation Gate state can be restored safely.
    """

    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        raise DIBPersistenceError("DIB session query requires project_id")

    resolved_limit = _normalize_limit(limit)
    if include_closed:
        rows = store.connection.execute(
            """
            SELECT session_id
            FROM dib_sessions
            WHERE project_id = ?
            ORDER BY updated_at DESC, created_at DESC, session_id DESC
            LIMIT ?
            """,
            (normalized_project_id, resolved_limit),
        ).fetchall()
    else:
        rows = store.connection.execute(
            """
            SELECT session_id
            FROM dib_sessions
            WHERE project_id = ? AND status != 'closed'
            ORDER BY updated_at DESC, created_at DESC, session_id DESC
            LIMIT ?
            """,
            (normalized_project_id, resolved_limit),
        ).fetchall()

    sessions = [store.load_session(row["session_id"]) for row in rows]
    for session in sessions:
        if session.get("external_fetch_enabled"):
            raise DIBPersistenceError("DIB session continuity detected external fetch enabled")
        if session.get("ai_provider_enabled"):
            raise DIBPersistenceError("DIB session continuity detected AI provider enabled")
        if session.get("finance_wiring_enabled"):
            raise DIBPersistenceError("DIB session continuity detected Finance wiring enabled")
        if session.get("snapshot_wiring_enabled"):
            raise DIBPersistenceError("DIB session continuity detected Snapshot wiring enabled")
    return sessions


def latest_dib_session_for_project(
    store: DIBPersistenceStore,
    project_id: str,
    *,
    include_closed: bool = False,
) -> dict[str, Any] | None:
    sessions = list_dib_sessions_for_project(store, project_id, include_closed=include_closed, limit=1)
    return sessions[0] if sessions else None
