#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${ASIE_COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ASIE_ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
  echo "missing deployment environment: $ENV_FILE" >&2
  exit 1
fi

retention=$(sed -n 's/^ASIE_BACKUP_RETENTION_DAYS=//p' "$ENV_FILE" | tail -n 1)
retention=${retention:-14}

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T api \
  python - "$retention" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import gzip
from pathlib import Path
import shutil
import sqlite3
import sys
import time

retention_days = max(1, int(sys.argv[1]))
root = Path("/var/lib/asie")
backup_dir = root / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

for name in ("asie_local.sqlite3", "dib_local.sqlite3"):
    source = root / name
    if not source.exists():
        print(f"skip missing database: {source}")
        continue
    temp = backup_dir / f".{name}.{stamp}.tmp"
    target = backup_dir / f"{name}.{stamp}.sqlite3.gz"
    with sqlite3.connect(source) as source_db, sqlite3.connect(temp) as target_db:
        source_db.backup(target_db)
        row = target_db.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            raise RuntimeError(f"backup_integrity_check_failed:{name}")
    with temp.open("rb") as raw, gzip.open(target, "wb", compresslevel=9) as compressed:
        shutil.copyfileobj(raw, compressed)
    temp.unlink(missing_ok=True)
    print(f"created: {target}")

cutoff = time.time() - retention_days * 86400
for path in backup_dir.glob("*.sqlite3.gz"):
    if path.stat().st_mtime < cutoff:
        path.unlink()
        print(f"expired: {path}")
PY
