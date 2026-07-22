from __future__ import annotations

"""Local backup/restore primitives with explicit encryption admission control.

The package intentionally does not invent cryptography.  Archives are only
created for the local controlled profile and contain a checksum manifest.  A
deployment must provide an approved encrypted archive wrapper before archive
export can be enabled outside that profile.
"""

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


ARCHIVE_FORMAT = "asie-local-backup.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_local_backup(*, database_path: Path, destination: Path) -> dict[str, Any]:
    """Create a consistent SQLite copy and checksum manifest; no secrets are embedded."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="asie-backup-") as temporary:
        copied_database = Path(temporary) / "asie_local.sqlite3"
        source = sqlite3.connect(database_path)
        target = sqlite3.connect(copied_database)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        manifest = {
            "format": ARCHIVE_FORMAT,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {"asie_local.sqlite3": {"sha256": sha256_file(copied_database)}},
            "encryption": {"state": "not_embedded", "required_for_non_local_export": True},
        }
        with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(copied_database, "asie_local.sqlite3")
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return manifest | {"archive_path": str(destination), "archive_sha256": sha256_file(destination)}


def restore_local_backup(*, archive_path: Path, target_database_path: Path) -> dict[str, Any]:
    """Verify archive/database integrity, then replace the target atomically."""
    with TemporaryDirectory(prefix="asie-restore-") as temporary:
        temporary_path = Path(temporary)
        with ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            if names != {"asie_local.sqlite3", "manifest.json"}:
                raise ValueError("backup_archive_contents_invalid")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != ARCHIVE_FORMAT:
                raise ValueError("backup_archive_format_invalid")
            restored = temporary_path / "restored.sqlite3"
            restored.write_bytes(archive.read("asie_local.sqlite3"))
        expected = manifest.get("files", {}).get("asie_local.sqlite3", {}).get("sha256")
        if not expected or sha256_file(restored) != expected:
            raise ValueError("backup_checksum_mismatch")
        connection = sqlite3.connect(restored)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
        if integrity != "ok":
            raise ValueError("backup_sqlite_integrity_failed")
        target_database_path.parent.mkdir(parents=True, exist_ok=True)
        staged_target = target_database_path.with_suffix(target_database_path.suffix + ".restore-staging")
        shutil.copyfile(restored, staged_target)
        staged_target.replace(target_database_path)
    return {"format": ARCHIVE_FORMAT, "database_sha256": expected, "sqlite_integrity": "ok"}


def backup_status(backup_directory: Path | None) -> dict[str, Any]:
    if backup_directory is None or not backup_directory.exists():
        return {"state": "not_configured", "encrypted": False, "external_export_allowed": False}
    archives = sorted(backup_directory.glob("*.asie-backup.zip"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not archives:
        return {"state": "no_archive", "encrypted": False, "external_export_allowed": False}
    newest = archives[0]
    return {
        "state": "available_local_only",
        "latest_archive": newest.name,
        "latest_archive_sha256": sha256_file(newest),
        "encrypted": False,
        "external_export_allowed": False,
    }
