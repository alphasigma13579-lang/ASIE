"""Offline public-corpus storage primitive. No provider, CLI or runtime wiring.

One service-owned local directory on one host. All callers must use session().
Source admission remains the domain's responsibility, not this persistence layer.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid

from backend.provider_security_control_plane import TrustedProviderScope
from backend.public_corpus_files import StoreFiles, UnsafeStorePath

_WORKLOAD = "public-knowledge-sync"
_VERSION = 2
_REPLAY_CONTRACT = "public-knowledge-lifecycle.v1"
_MAX_BYTES = 16 * 1024 * 1024
_FORBIDDEN = frozenset({
    "organization_id", "tenant_id", "project_id", "session_id", "user_id",
    "organization_ref", "project_ref", "api_key", "secret", "password",
    "prompt", "query", "customer_data",
})
_KINDS = frozenset({"sync", "delete", "restore", "reindex"})


class CorpusStoreError(RuntimeError):
    """Internal stable code only; never a raw database or filesystem exception."""


def _guarded(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (OSError, sqlite3.Error):
            raise CorpusStoreError("corpus_storage_unavailable") from None
    return call


def _token(value, maximum=160):
    if type(value) is not str or not 1 <= len(value) <= maximum:
        raise CorpusStoreError("corpus_request_invalid")
    if not all(c.isascii() and (c.isalnum() or c in "-_.:") for c in value):
        raise CorpusStoreError("corpus_request_invalid")
    return value


def _json(value):
    # Reject executable/custom containers, non-finite values and customer keys.
    def walk(item, depth=0):
        if depth > 32:
            raise CorpusStoreError("corpus_payload_invalid")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str or key.lower() in _FORBIDDEN:
                    raise CorpusStoreError("corpus_payload_invalid")
                walk(child, depth + 1)
        elif type(item) is list:
            for child in item:
                walk(child, depth + 1)
        elif type(item) is float:
            if not math.isfinite(item):
                raise CorpusStoreError("corpus_payload_invalid")
        elif item is not None and type(item) not in (str, int, bool):
            raise CorpusStoreError("corpus_payload_invalid")
    walk(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
        if len(encoded.encode("utf-8")) > _MAX_BYTES:
            raise CorpusStoreError("corpus_payload_invalid")
        return encoded
    except (ValueError, UnicodeError, RecursionError):
        raise CorpusStoreError("corpus_payload_invalid") from None


def _corpus(value):
    encoded = _json(value)
    if (type(value) is not dict or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1 or value.get("source_of_truth") is not True
            or type(value.get("sources")) is not dict
            or type(value.get("audit_events")) is not list):
        raise CorpusStoreError("corpus_payload_invalid")
    return encoded


def _read_json(value):
    try:
        decoded = json.loads(value)
        _json(decoded)
        return decoded
    except (ValueError, TypeError, RecursionError, CorpusStoreError):
        raise CorpusStoreError("corpus_storage_invalid") from None


def _read_corpus(value):
    decoded = _read_json(value)
    try:
        _corpus(decoded)
    except CorpusStoreError:
        raise CorpusStoreError("corpus_storage_invalid") from None
    return decoded


_SCHEMA_V1 = """
BEGIN IMMEDIATE;
CREATE TABLE corpus_state(
 id INTEGER PRIMARY KEY CHECK(id=1),
 revision INTEGER NOT NULL CHECK(revision>=0),
 restore_epoch TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE operations(
 operation_id TEXT PRIMARY KEY,
 restore_epoch TEXT NOT NULL,
 workload TEXT NOT NULL,
 key_hash TEXT NOT NULL,
 intent_digest TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('sync','delete','restore','reindex')),
 base_revision INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('prepared','recovery_required','committed')),
 before_payload TEXT NOT NULL,
 after_payload TEXT NOT NULL,
 result_code TEXT CHECK(result_code IS NULL OR result_code='committed'),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(restore_epoch,workload,key_hash)
);
CREATE UNIQUE INDEX one_unfinished ON operations((1))
 WHERE state IN ('prepared','recovery_required');
CREATE TABLE operation_steps(
 operation_id TEXT NOT NULL REFERENCES operations(operation_id),
 ordinal INTEGER NOT NULL CHECK(ordinal>=0),
 payload TEXT NOT NULL,
 PRIMARY KEY(operation_id,ordinal)
);
PRAGMA user_version=1;
COMMIT;
"""

_SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE corpus_state(
 id INTEGER PRIMARY KEY CHECK(id=1),
 revision INTEGER NOT NULL CHECK(revision>=0),
 restore_epoch TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE operations(
 operation_id TEXT PRIMARY KEY,
 restore_epoch TEXT NOT NULL,
 workload TEXT NOT NULL,
 key_hash TEXT NOT NULL,
 intent_digest TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('sync','delete','restore','reindex')),
 base_revision INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('prepared','recovery_required','committed','compensated')),
 before_payload TEXT NOT NULL,
 after_payload TEXT NOT NULL,
 result_code TEXT CHECK(result_code IS NULL OR result_code IN ('committed','compensated')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 request_digest TEXT,
 result_payload TEXT,
 UNIQUE(restore_epoch,workload,key_hash)
);
CREATE UNIQUE INDEX one_unfinished ON operations((1))
 WHERE state IN ('prepared','recovery_required');
CREATE TABLE operation_steps(
 operation_id TEXT NOT NULL REFERENCES operations(operation_id),
 ordinal INTEGER NOT NULL CHECK(ordinal>=0),
 payload TEXT NOT NULL,
 PRIMARY KEY(operation_id,ordinal)
);
PRAGMA user_version=2;
COMMIT;
"""


def _schema_signature(schema=_SCHEMA):
    expected = {}
    for statement in schema.split(";"):
        sql = " ".join(statement.split())
        if sql.startswith("CREATE TABLE "):
            expected[("table", sql.split()[2].split("(")[0])] = sql
        elif sql.startswith("CREATE UNIQUE INDEX "):
            expected[("index", sql.split()[3])] = sql
    return expected


def _validate_schema(connection, schema=_SCHEMA):
    actual = {(kind, name): " ".join(sql.split())
              for kind, name, sql in connection.execute(
                  "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL")}
    if actual != _schema_signature(schema):
        raise CorpusStoreError("corpus_schema_unsupported")
    rows = connection.execute(
        "SELECT id,revision,restore_epoch,payload FROM corpus_state").fetchall()
    if len(rows) != 1 or rows[0][0] != 1 or type(rows[0][1]) is not int or rows[0][1] < 0:
        raise CorpusStoreError("corpus_storage_invalid")
    try:
        _token(rows[0][2])
    except CorpusStoreError:
        raise CorpusStoreError("corpus_storage_invalid") from None
    _read_corpus(rows[0][3])




def _validate_journal(connection, *, version=1, operation_id=None):
    """Validate the requested journal rows; full scan only for explicit upgrade."""
    try:
        columns = ("operation_id,restore_epoch,workload,key_hash,intent_digest,"
                   "kind,base_revision,state,before_payload,after_payload,result_code,"
                   "created_at,updated_at")
        if version == 2:
            columns += ",request_digest,result_payload"
        where = "" if operation_id is None else " WHERE operation_id=?"
        args = () if operation_id is None else (operation_id,)
        for row in connection.execute("SELECT " + columns + " FROM operations" + where, args):
            for value in row[:5]:
                _token(value)
            if (row[2] != _WORKLOAD or row[5] not in _KINDS
                    or type(row[6]) is not int or row[6] < 0
                    or row[7] not in (("prepared", "recovery_required", "committed", "compensated")
                                     if version == 2 else ("prepared", "recovery_required", "committed"))
                    or row[10] != (row[7] if row[7] in ("committed", "compensated") else None)
                    or any(type(value) is not str or not value for value in row[11:13])):
                raise CorpusStoreError("corpus_storage_invalid")
            if version == 2:
                if row[13] is not None:
                    if (type(row[13]) is not str or len(row[13]) != 64
                            or any(c not in "0123456789abcdef" for c in row[13])):
                        raise CorpusStoreError("corpus_storage_invalid")
                terminal = row[7] in ("committed", "compensated")
                if not terminal and row[14] is not None:
                    raise CorpusStoreError("corpus_storage_invalid")
                if terminal:
                    if row[14] is None:
                        if row[13] is not None or row[7] == "compensated":
                            raise CorpusStoreError("corpus_storage_invalid")
                    else:
                        result = _read_json(row[14])
                        if (type(result) is not dict or type(result.get("status")) is not str
                                or not result["status"]
                                or (row[7] == "compensated") != (result["status"] == "failed_compensated")):
                            raise CorpusStoreError("corpus_storage_invalid")
            _read_corpus(row[8])
            _read_corpus(row[9])
            for expected, (ordinal, payload) in enumerate(connection.execute(
                    "SELECT ordinal,payload FROM operation_steps "
                    "WHERE operation_id=? ORDER BY ordinal", (row[0],))):
                step = _read_json(payload)
                if (type(ordinal) is not int or ordinal != expected
                        or type(step) is not dict or set(step) != {"action", "record_ids"}
                        or step["action"] not in ("upsert", "delete")
                        or type(step["record_ids"]) is not list
                        or not 1 <= len(step["record_ids"]) <= 1000):
                    raise CorpusStoreError("corpus_storage_invalid")
                for identifier in step["record_ids"]:
                    _token(identifier, 512)
    except CorpusStoreError:
        raise CorpusStoreError("corpus_storage_invalid") from None


def _upgrade_v1(connection):
    """Explicit, transactional compatibility conversion; never invoked implicitly."""
    _validate_schema(connection, _SCHEMA_V1)
    if (connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
            or connection.execute("PRAGMA foreign_key_check").fetchall()):
        raise CorpusStoreError("corpus_storage_invalid")
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        _validate_journal(connection)
        connection.execute("ALTER TABLE operation_steps RENAME TO operation_steps_v1")
        connection.execute("ALTER TABLE operations RENAME TO operations_v1")
        connection.execute("DROP INDEX one_unfinished")
        for statement in _SCHEMA.split(";"):
            sql = statement.strip()
            if sql.startswith(("CREATE TABLE operations(", "CREATE TABLE operation_steps(",
                               "CREATE UNIQUE INDEX")):
                connection.execute(sql)
        connection.execute("INSERT INTO operations SELECT *,NULL,NULL FROM operations_v1")
        connection.execute("INSERT INTO operation_steps SELECT * FROM operation_steps_v1")
        connection.execute("DROP TABLE operation_steps_v1")
        connection.execute("DROP TABLE operations_v1")
        connection.execute("PRAGMA user_version=2")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise CorpusStoreError("corpus_storage_invalid")
        _validate_schema(connection)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise CorpusStoreError("corpus_durability_unavailable")

@dataclass(frozen=True)
class Operation:
    operation_id: str
    state: str
    result_code: str | None


class PublicCorpusStore:
    """Constructing a store performs no I/O; directory is provisioned by operator."""

    def __init__(self, directory: Path, *, lock_timeout: float = 2.0):
        if (type(lock_timeout) not in (int, float) or not math.isfinite(lock_timeout)
                or not 0 <= lock_timeout <= 30):
            raise CorpusStoreError("corpus_request_invalid")
        self.directory = Path(directory)
        self.lock_timeout = float(lock_timeout)

    @contextmanager
    def session(self, scope: TrustedProviderScope, *, upgrade_v1=False):
        # Exact type plus proof-bearing native method: no duck-typed authority.
        if type(scope) is not TrustedProviderScope:
            raise CorpusStoreError("corpus_scope_denied")
        try:
            TrustedProviderScope.require_platform_workload(scope, _WORKLOAD)
        except PermissionError:
            raise CorpusStoreError("corpus_scope_denied") from None
        connection = None
        files = None
        descriptor = None
        locked = False
        session = None
        yielded = False
        try:
            files = StoreFiles(self.directory)
            files.open()
            descriptor = files.file("public_knowledge.lock")
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise CorpusStoreError("corpus_busy") from None
                    time.sleep(min(0.02, max(0, deadline - time.monotonic())))
            database = files.database()
            files.validate()
            connection = sqlite3.connect(database, timeout=2, isolation_level=None)
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 1 and upgrade_v1 is not True:
                raise CorpusStoreError("corpus_upgrade_required")
            if version not in (0, 1, _VERSION):
                raise CorpusStoreError("corpus_schema_unsupported")
            if version == 0 and connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
                raise CorpusStoreError("corpus_schema_unsupported")
            if str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower() != "wal":
                raise CorpusStoreError("corpus_durability_unavailable")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            if (connection.execute("PRAGMA synchronous").fetchone()[0] != 2
                    or connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1):
                raise CorpusStoreError("corpus_durability_unavailable")
            if version == 1:
                _upgrade_v1(connection)
            if version == 0:
                # Schema plus initial state in one transaction; no half-initialized DB.
                initial = _corpus({"schema_version": 1, "source_of_truth": True,
                                   "sources": {}, "audit_events": []})
                connection.execute("BEGIN IMMEDIATE")
                for statement in _SCHEMA.split(";"):
                    sql = statement.strip()
                    if sql.startswith("CREATE "):
                        connection.execute(sql)
                connection.execute("INSERT INTO corpus_state VALUES(1,0,?,?)",
                                   (uuid.uuid4().hex, initial))
                connection.execute("PRAGMA user_version=2")
                connection.commit()
            _validate_schema(connection)
            session = _Session(connection)
            yielded = True
            yield session
        except UnsafeStorePath:
            if yielded:
                raise
            raise CorpusStoreError("corpus_path_invalid") from None
        except (OSError, sqlite3.Error):
            if yielded:
                # The caller owns external-effect classification and recovery.
                raise
            raise CorpusStoreError("corpus_storage_unavailable") from None
        finally:
            if session is not None:
                session._active = False
            cleanup_failed = False
            if connection is not None:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    cleanup_failed = True
                try:
                    connection.close()
                except sqlite3.Error:
                    cleanup_failed = True
            if descriptor is not None:
                try:
                    if locked:
                        if os.name == "nt":
                            import msvcrt
                            os.lseek(descriptor, 0, os.SEEK_SET)
                            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError:
                    cleanup_failed = True
            if files is not None:
                try:
                    files.close()
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                raise CorpusStoreError("corpus_storage_unavailable") from None


class _Session:
    def __init__(self, connection):
        self._db = connection
        self._active = True
        self._pid = os.getpid()
        self._owned = set()

    def _check(self):
        if not self._active or self._pid != os.getpid():
            raise CorpusStoreError("corpus_session_closed")

    @contextmanager
    def _transaction(self):
        self._check()
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise

    @_guarded
    def verify_integrity(self):
        """Explicit maintenance: O(database history), under the process lock."""
        self._check()
        if self._db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise CorpusStoreError("corpus_storage_invalid")
        if self._db.execute("PRAGMA foreign_key_check").fetchall():
            raise CorpusStoreError("corpus_storage_invalid")
        _validate_schema(self._db)
        return "ok"

    @_guarded
    def snapshot(self):
        self._check()
        row = self._db.execute(
            "SELECT revision,restore_epoch,payload FROM corpus_state WHERE id=1").fetchone()
        if row is None:
            raise CorpusStoreError("corpus_storage_invalid")
        corpus = _read_corpus(row[2])
        blocked = bool(self._db.execute(
            "SELECT 1 FROM operations WHERE state IN ('prepared','recovery_required') LIMIT 1").fetchone())
        # Operations are append-only within an epoch. MAX(rowid) detects a
        # complete prepare/compensate cycle even when corpus revision is unchanged.
        watermark = self._db.execute("SELECT COALESCE(MAX(rowid),0) FROM operations").fetchone()[0]
        return {"revision": row[0], "restore_epoch": row[1],
                "operation_watermark": watermark,
                "corpus": corpus, "recovery_required": blocked}

    @_guarded
    def begin(self, *, key, epoch, kind, intent, expected_revision, after, request=None):
        self._check()
        _token(key)
        _token(epoch)
        if type(kind) is not str or kind not in _KINDS or type(expected_revision) is not int or expected_revision < 0:
            raise CorpusStoreError("corpus_request_invalid")
        if type(intent) is not dict:
            raise CorpusStoreError("corpus_request_invalid")
        after_text = _corpus(after)
        digest = hashlib.sha256(_json({"kind": kind, "intent": intent,
                                      "after": after, "revision": expected_revision,
                                      "contract_version": _VERSION}).encode()).hexdigest()
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        request_digest = hashlib.sha256(_json({"contract": _REPLAY_CONTRACT, "request": request}).encode()).hexdigest() if request is not None else None
        with self._transaction():
            current = self.snapshot()
            if epoch != current["restore_epoch"]:
                raise CorpusStoreError("corpus_epoch_mismatch")
            prior = self._db.execute(
                "SELECT operation_id,state,result_code,intent_digest FROM operations "
                "WHERE restore_epoch=? AND workload=? AND key_hash=?",
                (epoch, _WORKLOAD, key_hash)).fetchone()
            if prior:
                if prior[3] != digest:
                    raise CorpusStoreError("corpus_intent_conflict")
                if prior[1] not in ("committed", "compensated"):
                    raise CorpusStoreError("corpus_recovery_required")
                return Operation(*prior[:3])
            if current["recovery_required"]:
                raise CorpusStoreError("corpus_recovery_required")
            if expected_revision != current["revision"]:
                raise CorpusStoreError("corpus_revision_conflict")
            operation = uuid.uuid4().hex
            self._db.execute(
                "INSERT INTO operations VALUES(?,?,?,?,?,?,?,'prepared',?,?,NULL,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?,NULL)",
                (operation, epoch, _WORKLOAD, key_hash, digest, kind,
                 expected_revision, _corpus(current["corpus"]), after_text, request_digest))
        self._owned.add(operation)
        return Operation(operation, "prepared", None)

    @_guarded
    def record_step(self, operation_id, *, action, record_ids, recovery=False):
        self._check()
        _token(operation_id)
        if action not in ("upsert", "delete") or type(record_ids) is not list:
            raise CorpusStoreError("corpus_request_invalid")
        if not 1 <= len(record_ids) <= 1000:
            raise CorpusStoreError("corpus_request_invalid")
        for identifier in record_ids:
            _token(identifier, 512)
        payload = _json({"action": action, "record_ids": record_ids})
        with self._transaction():
            if recovery is True:
                if not self._db.execute(
                        "SELECT 1 FROM operations WHERE operation_id=? "
                        "AND state IN ('prepared','recovery_required')", (operation_id,)).fetchone():
                    raise CorpusStoreError("corpus_operation_not_prepared")
            else:
                self._prepared(operation_id)
            ordinal = self._db.execute(
                "SELECT COUNT(*) FROM operation_steps WHERE operation_id=?",
                (operation_id,)).fetchone()[0]
            self._db.execute("INSERT INTO operation_steps VALUES(?,?,?)",
                             (operation_id, ordinal, payload))
        return ordinal

    def _prepared(self, operation_id):
        if operation_id not in self._owned:
            raise CorpusStoreError("corpus_recovery_required")
        row = self._db.execute(
            "SELECT base_revision,after_payload,state FROM operations WHERE operation_id=?",
            (operation_id,)).fetchone()
        if row is None or row[2] != "prepared":
            raise CorpusStoreError("corpus_operation_not_prepared")
        return row

    @_guarded
    def commit(self, operation_id, *, result=None):
        self._check()
        _token(operation_id)
        result_text = _json({"status": "committed"} if result is None else result)
        with self._transaction():
            base, payload, _ = self._prepared(operation_id)
            _read_corpus(payload)
            cursor = self._db.execute(
                "UPDATE corpus_state SET revision=revision+1,payload=? WHERE id=1 AND revision=?",
                (payload, base))
            if cursor.rowcount != 1:
                raise CorpusStoreError("corpus_revision_conflict")
            self._db.execute(
                "UPDATE operations SET state='committed',result_code='committed',result_payload=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
                (result_text, operation_id))
        return Operation(operation_id, "committed", "committed")

    @_guarded
    def pending(self):
        self._check()
        rows = self._db.execute(
            "SELECT operation_id,kind,base_revision,state,before_payload,after_payload "
            "FROM operations WHERE state IN ('prepared','recovery_required')").fetchall()
        for row in rows:
            _validate_journal(self._db, version=2, operation_id=row[0])
        return [{"operation_id": r[0], "kind": r[1], "base_revision": r[2],
                 "state": r[3], "before": _read_corpus(r[4]), "after": _read_corpus(r[5]),
                 "steps": [_read_json(s[0]) for s in self._db.execute(
                     "SELECT payload FROM operation_steps WHERE operation_id=? ORDER BY ordinal",
                     (r[0],)).fetchall()]} for r in rows]

    @_guarded
    def mark_recovery_required(self, operation_id):
        self._check()
        _token(operation_id)
        with self._transaction():
            self._prepared(operation_id)
            self._db.execute(
                "UPDATE operations SET state='recovery_required',updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
                (operation_id,))

    @_guarded
    def lookup(self, *, key, epoch, request):
        """Replay before preparing content or reading a new revision for intent."""
        self._check()
        _token(key)
        _token(epoch)
        digest = hashlib.sha256(_json({"contract": _REPLAY_CONTRACT, "request": request}).encode()).hexdigest()
        current_epoch = self._db.execute(
            "SELECT restore_epoch FROM corpus_state WHERE id=1").fetchone()
        if current_epoch is None:
            raise CorpusStoreError("corpus_storage_invalid")
        if epoch != current_epoch[0]:
            raise CorpusStoreError("corpus_epoch_mismatch")
        row = self._db.execute(
            "SELECT state,request_digest,result_payload,operation_id FROM operations "
            "WHERE restore_epoch=? AND workload=? AND key_hash=?",
            (epoch, _WORKLOAD, hashlib.sha256(key.encode()).hexdigest())).fetchone()
        if row:
            _validate_journal(self._db, version=2, operation_id=row[3])
            if row[1] is None:
                raise CorpusStoreError("corpus_legacy_result_unavailable")
            if row[1] != digest:
                raise CorpusStoreError("corpus_intent_conflict")
            if row[0] not in ("committed", "compensated"):
                raise CorpusStoreError("corpus_recovery_required")
            if row[2] is None:
                raise CorpusStoreError("corpus_legacy_result_unavailable")
            return _read_json(row[2])
        if self.snapshot()["recovery_required"]:
            raise CorpusStoreError("corpus_recovery_required")
        return None

    @_guarded
    def finish_compensation(self, operation_id, *, result):
        """Caller must establish settled external effects and projection parity first."""
        self._check()
        _token(operation_id)
        result_text = _json(result)
        with self._transaction():
            row = self._db.execute(
                "SELECT base_revision,before_payload FROM operations "
                "WHERE operation_id=? AND state IN ('prepared','recovery_required')",
                (operation_id,)).fetchone()
            if row is None:
                raise CorpusStoreError("corpus_operation_not_prepared")
            current = self.snapshot()
            if row[0] != current["revision"] or _read_corpus(row[1]) != current["corpus"]:
                raise CorpusStoreError("corpus_revision_conflict")
            self._db.execute(
                "UPDATE operations SET state='compensated',result_code='compensated',"
                "result_payload=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
                (result_text, operation_id))
