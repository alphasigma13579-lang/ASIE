from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from backend.recovery import backup_status
from backend.repository import Repository


def local_operational_health(repository: Repository) -> dict[str, Any]:
    """Read-only local health projection; no call reaches an external system."""
    try:
        connection = sqlite3.connect(repository.db_path)
        try:
            database_integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error:
        database_integrity = "unavailable"
    configured_backup_directory = os.environ.get("ASIE_BACKUP_DIR")
    return {
        "mode": "local_read_only",
        "external_access_enabled": False,
        "database": {"state": "healthy" if database_integrity == "ok" else "degraded", "integrity_check": database_integrity},
        "run_failures": repository.operational_run_failures(),
        "backup": backup_status(Path(configured_backup_directory) if configured_backup_directory else None),
        "incidents": repository.platform_incidents(),
        "audit_event_count": len(repository.security_audit_events(limit=200)),
    }
