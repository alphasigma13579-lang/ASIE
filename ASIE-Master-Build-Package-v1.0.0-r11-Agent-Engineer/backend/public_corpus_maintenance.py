"""Explicit offline maintenance. No CLI, HTTP, environment or live provider factory.

Paths are operator-provisioned private directories, never browser input.
Artifacts are accepted only after independent read-only verification. Failures
leave their destination for inspection; the original is never replaced/deleted.
"""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from backend.public_corpus_store import (
    CorpusStoreError, PublicCorpusStore, _Session, _SCHEMA_V3,
    _MAINTENANCE_TABLES, _corpus, _json, _MAX_BYTES, _token,
    _INSTALLATION, _BACKUP, _installation_epoch, _check_existing_installation,
)
from backend.public_corpus_files import UnsafeStorePath
from backend.public_knowledge_lifecycle import _authorize, _projection, _record_sets
from backend.public_knowledge import validate_public_knowledge_record, _safe_source_id, _parse_utc, _canonical_url

_DB = "public_knowledge.sqlite3"
_MANIFEST = "public_knowledge.manifest.json"
_LEGACY = "public_knowledge_corpus.json"
_ANOMALY_CODES = frozenset({
    "prompt_injection_suspected", "content_encoding_corrupt",
    "sensitive_secret_pattern", "sensitive_personal_identifier_pattern",
    "public_source_extract_url_mismatch", "public_source_crawl_url_mismatch",
})


def _safe(fn):
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except CorpusStoreError:
            raise
        except UnsafeStorePath:
            raise CorpusStoreError("corpus_path_invalid") from None
        except (OSError, sqlite3.Error, ValueError, TypeError, UnicodeError, RecursionError):
            raise CorpusStoreError("corpus_maintenance_failed") from None
    return call


def _digest(value):
    digest = hashlib.sha256()
    # Payloads are validated before entry. Stream aggregate history rather than
    # applying the per-payload size limit to the entire retained journal.
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for chunk in encoder.iterencode(value):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CorpusStoreError("corpus_import_invalid")
            result[key] = value
        return result
    def constant(_):
        raise CorpusStoreError("corpus_import_invalid")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=constant)
        _json(result)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise CorpusStoreError("corpus_import_invalid") from None


def _read(fd, limit):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks, total = [], 0
    while True:
        chunk = os.read(fd, min(65536, limit + 1 - total))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise CorpusStoreError("corpus_artifact_too_large")


def _file_digest(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def _verify_source(files, fd, fingerprint):
    # A digest of a pinned descriptor alone misses pathname replacement.
    files.validate()
    if _file_digest(fd) != fingerprint:
        raise CorpusStoreError("corpus_source_changed")
    files.validate()


def _write(fd, value):
    payload = _json(value).encode("utf-8")
    while payload:
        written = os.write(fd, payload)
        if written <= 0:
            raise CorpusStoreError("corpus_maintenance_failed")
        payload = payload[written:]
    os.fsync(fd)


def _flush_directory(files):
    # Host power-loss guarantees still require the separate deployment rehearsal.
    if os.name != "nt":
        os.fsync(files._root_fd)


def _different(left, right):
    if os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right)):
        raise CorpusStoreError("corpus_destination_not_new")


def _readonly(files, *, installing=False, backup=False):
    if os.path.lexists(files.path / _BACKUP) and not backup:
        raise CorpusStoreError("corpus_backup_requires_restore")
    if backup:
        marker = files.file(_BACKUP, readonly=True, create=False)
        if _read(marker, 16) != b"backup-v1":
            raise CorpusStoreError("corpus_backup_invalid")
    installed_epoch = None if installing else _installation_epoch(files)
    if not installing and not backup:
        _check_existing_installation(files, installed_epoch)
    files.file(_DB, readonly=True, create=False)
    for suffix in ("-wal", "-shm", "-journal"):
        if os.path.lexists(files.path / (_DB + suffix)):
            files.file(_DB + suffix, readonly=True, create=False)
    files.validate()
    db = sqlite3.connect((files.path / _DB).as_uri() + "?mode=ro",
                         uri=True, isolation_level=None, timeout=2)
    try:
        if (not installing and not backup and installed_epoch is None
                and db.execute("PRAGMA user_version").fetchone()[0] == 3):
            raise CorpusStoreError("corpus_installation_incomplete")
        if installed_epoch is not None and (
                db.execute("PRAGMA user_version").fetchone()[0] != 3 or db.execute(
                    "SELECT restore_epoch FROM corpus_state WHERE id=1").fetchone() != (installed_epoch,)):
            raise CorpusStoreError("corpus_installation_incomplete")
        return db
    except BaseException:
        db.close()
        raise


def _reject_sidecars(files):
    if any(os.path.lexists(files.path / (_DB + suffix))
           for suffix in ("-wal", "-shm", "-journal")):
        raise CorpusStoreError("corpus_destination_not_new")


def _start_install(files, *, origin, fingerprint):
    _reject_sidecars(files)
    if os.path.lexists(files.path / _DB) or os.path.lexists(files.path / _BACKUP):
        raise CorpusStoreError("corpus_destination_not_new")
    if origin not in ("import", "restore"):
        raise CorpusStoreError("corpus_installation_incomplete")
    fd = files.file(_INSTALLATION, exclusive=True)
    payload = ("pending:" + origin + ":" + fingerprint).encode("ascii")
    while payload:
        written = os.write(fd, payload)
        if written <= 0:
            raise CorpusStoreError("corpus_maintenance_failed")
        payload = payload[written:]
    os.fsync(fd)
    _flush_directory(files)


def _start_backup(files):
    _reject_sidecars(files)
    if os.path.lexists(files.path / _DB) or os.path.lexists(files.path / _INSTALLATION):
        raise CorpusStoreError("corpus_destination_not_new")
    fd = files.file(_BACKUP, exclusive=True)
    payload = b"backup-v1"
    while payload:
        written = os.write(fd, payload)
        if written <= 0:
            raise CorpusStoreError("corpus_maintenance_failed")
        payload = payload[written:]
    os.fsync(fd)
    _flush_directory(files)


def _seal_install(files, epoch):
    fd = files.file(_INSTALLATION, create=False)
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    payload = b"ready:" + _token(epoch).encode("ascii")
    while payload:
        written = os.write(fd, payload)
        if written <= 0:
            raise CorpusStoreError("corpus_maintenance_failed")
        payload = payload[written:]
    os.fsync(fd)
    _flush_directory(files)


def _new_database(files):
    _reject_sidecars(files)
    files.file(_DB, exclusive=True)
    files.validate()
    _reject_sidecars(files)
    db = sqlite3.connect(files.path / _DB, isolation_level=None, timeout=2)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        if (db.execute("PRAGMA synchronous").fetchone()[0] != 2
                or db.execute("PRAGMA foreign_keys").fetchone()[0] != 1):
            raise CorpusStoreError("corpus_durability_unavailable")
        return db
    except BaseException:
        db.close()
        raise


def _validate_corpus(value):
    """Validate every retained version, not only the active index projection."""
    try:
        _corpus(value)
        if set(value) != {"schema_version", "source_of_truth", "sources", "audit_events"}:
            raise ValueError
        count = 0
        # Existing shape/identity checks, then full metadata for all histories.
        list(_record_sets(value))
        _projection(value)
        for source_id, source in value["sources"].items():
            if _safe_source_id(source_id) != source_id:
                raise ValueError
            allowed = {"status", "source_url", "content_sha256", "current_version",
                       "records", "versions", "last_checked_at", "last_changed_at",
                       "last_result", "last_anomalies", "deleted_at"}
            required = {"status", "source_url", "records", "versions", "last_checked_at", "last_result"}
            status = source.get("status")
            results = {"active": {"changed_upserted", "unchanged", "restored", "quarantined"},
                       "deleted_tombstone": {"deleted"}, "quarantined": {"quarantined"}}
            if status != "quarantined":
                required |= {"content_sha256", "current_version", "last_changed_at"}
            if (set(source) - allowed or not required <= set(source)
                    or status not in results or source["last_result"] not in results[status]):
                raise ValueError
            if source["last_result"] == "quarantined" and not source.get("last_anomalies"):
                raise ValueError
            if status == "quarantined" and "last_changed_at" in source:
                raise ValueError
            if source["status"] == "quarantined" and (
                    source["records"] or source["versions"]
                    or source.get("current_version") is not None or source.get("content_sha256") is not None):
                raise ValueError
            version_numbers = []
            for current, version in [(False, v) for v in source["versions"]] + [(True, source)]:
                records = version["records"]
                number = version.get("current_version" if current else "version")
                if not records:
                    if not current or source["status"] != "quarantined" or number is not None:
                        raise ValueError
                    continue
                if type(number) is not int or number < 1:
                    raise ValueError
                version_numbers.append(number)
                digest = version.get("content_sha256")
                indices = set()
                for record in records:
                    validate_public_knowledge_record(record)
                    if (record["source_id"] != source_id or record["version"] != number
                            or record["content_sha256"] != digest
                            or record["chunk_count"] != len(records)):
                        raise ValueError
                    indices.add(record["chunk_index"])
                    count += 1
                if indices != set(range(1, len(records) + 1)):
                    raise ValueError
                if not current:
                    if set(version) != {"version", "content_sha256", "records", "retained_at"}:
                        raise ValueError
                    _parse_utc(version["retained_at"], field="retained_at")
            if version_numbers != sorted(set(version_numbers)):
                raise ValueError
            if (source["status"] == "deleted_tombstone") != ("deleted_at" in source):
                raise ValueError
            for key in ("source_url", "last_checked_at", "last_changed_at", "last_result", "deleted_at"):
                if key in source and (type(source[key]) is not str or not source[key]):
                    raise ValueError
            for key in ("last_checked_at", "last_changed_at", "deleted_at"):
                if key in source:
                    _parse_utc(source[key], field=key)
            if "source_url" in source:
                _canonical_url(source["source_url"])
            if "last_result" in source and source["last_result"] not in {
                    "quarantined", "unchanged", "changed_upserted", "deleted", "restored"}:
                raise ValueError
            if "last_anomalies" in source and (type(source["last_anomalies"]) is not list
                    or any(type(v) is not str or v not in _ANOMALY_CODES for v in source["last_anomalies"])):
                raise ValueError
        event_fields = {
            "source_version_activated": {"event", "source_id", "version", "at"},
            "source_quarantined": {"event", "source_id", "anomalies", "at"},
            "source_deleted": {"event", "source_id", "at"},
            "source_restored": {"event", "source_id", "at"},
            "public_namespace_reindexed": {"event", "records", "stale_records_deleted", "at"},
            "empty_public_projection_reconciled": {"event", "records_deleted", "at"},
        }
        for event in value["audit_events"]:
            if (type(event) is not dict or type(event.get("event")) is not str
                    or event["event"] not in event_fields
                    or set(event) != event_fields[event["event"]]):
                raise ValueError
            _parse_utc(event["at"], field="at")
            if "source_id" in event and event["source_id"] not in value["sources"]:
                raise ValueError
            for field in ("version", "records", "stale_records_deleted", "records_deleted"):
                if field in event and (type(event[field]) is not int
                        or event[field] < (1 if field == "version" else 0)):
                    raise ValueError
            if "anomalies" in event and (type(event["anomalies"]) is not list
                    or not event["anomalies"]
                    or any(type(v) is not str or v not in _ANOMALY_CODES for v in event["anomalies"])):
                raise ValueError
        return count
    except Exception:
        raise CorpusStoreError("corpus_import_invalid") from None


def _validate_image(image):
    _validate_corpus(image["corpus_state"][3])
    for operation in image["operations"]:
        _validate_corpus(operation[9])
        _validate_corpus(operation[10])


def _event(db, name, payload):
    db.execute("INSERT INTO maintenance_events(event,payload) VALUES(?,?)",
               (name, _json(payload)))


def _install(db, *, origin, fingerprint, baseline, parent_epoch, epoch, count=None):
    """Caller owns one transaction; original corpus/journal remain intact."""
    if db.execute("PRAGMA user_version").fetchone()[0] == 2:
        for statement in _MAINTENANCE_TABLES.split(";"):
            if statement.strip():
                db.execute(statement)
        db.execute("PRAGMA user_version=3")
    db.execute("DELETE FROM maintenance_state")
    db.execute("INSERT INTO maintenance_state VALUES(1,?,?,?,?, 'pending',NULL,NULL)",
               (origin, fingerprint, baseline, parent_epoch))
    db.execute("UPDATE corpus_state SET restore_epoch=? WHERE id=1", (epoch,))
    if origin == "import":
        db.execute("INSERT INTO imports VALUES(?,1,?)", (fingerprint, count))
    _event(db, origin + "_installed", {"input_sha256": fingerprint,
           "baseline_sha256": baseline, "parent_epoch": parent_epoch, "restore_epoch": epoch})


class PublicCorpusMaintenance:
    def __init__(self, *, scope):
        _authorize(scope)
        self.scope = scope

    @_safe
    def import_legacy(self, source_directory, destination):
        _authorize(self.scope)
        _different(source_directory, destination.directory)
        source = PublicCorpusStore(source_directory)
        with source.session(self.scope, files_only=True) as incoming:
            fd = incoming.file(_LEGACY, readonly=True, create=False)
            raw = _read(fd, _MAX_BYTES)
            fingerprint = hashlib.sha256(raw).hexdigest()
            corpus = _decode(raw)
            count = _validate_corpus(corpus)
            incoming.validate()
            with destination.session(self.scope, files_only=True) as files:
                if os.path.lexists(files.path / _DB):
                    with closing(_readonly(files, installing=True)) as db:
                        image = _Session(db).verified_image()
                        _validate_image(image)
                        receipt = image.get("imports", [])
                        if [fingerprint, 1, count] not in receipt:
                            raise CorpusStoreError("corpus_destination_not_new")
                        try:
                            sealed_epoch = _installation_epoch(files)
                        except CorpusStoreError as error:
                            if str(error) != "corpus_installation_incomplete":
                                raise
                            sealed_epoch = None
                        _verify_source(incoming, fd, fingerprint)
                        if sealed_epoch != image["corpus_state"][2]:
                            marker = files.file(_INSTALLATION, readonly=True, create=False)
                            if _read(marker, 256) != ("pending:import:" + fingerprint).encode("ascii"):
                                raise CorpusStoreError("corpus_installation_incomplete")
                            state = image["maintenance_state"][0]
                            if state[1] != "import" or state[2] != fingerprint or state[5] != "pending":
                                raise CorpusStoreError("corpus_installation_incomplete")
                            _seal_install(files, image["corpus_state"][2])
                        _verify_source(incoming, fd, fingerprint)
                        return {"status": "already_imported", "records": count}
                _start_install(files, origin="import", fingerprint=fingerprint)
                with closing(_new_database(files)) as db:
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        for statement in _SCHEMA_V3.split(";"):
                            if statement.strip().startswith("CREATE "):
                                db.execute(statement)
                        db.execute("PRAGMA user_version=3")
                        epoch = uuid.uuid4().hex
                        db.execute("INSERT INTO corpus_state VALUES(1,1,?,?)",
                                   (epoch, _corpus(corpus)))
                        _install(db, origin="import", fingerprint=fingerprint,
                                 baseline=_digest(corpus), parent_epoch="initial-import",
                                 epoch=epoch, count=count)
                        db.commit()
                    except BaseException:
                        db.rollback()
                        raise
                    image = _Session(db).verified_image()
                    if image["corpus_state"][3] != corpus:
                        raise CorpusStoreError("corpus_semantic_mismatch")
                with closing(_readonly(files, installing=True)) as db:
                    if _Session(db).verified_image() != image:
                        raise CorpusStoreError("corpus_semantic_mismatch")
                _verify_source(incoming, fd, fingerprint)
                _seal_install(files, epoch)
            _verify_source(incoming, fd, fingerprint)
        return {"status": "imported", "records": count, "rebuild_required": True}

    @_safe
    def backup(self, source, destination_directory):
        _authorize(self.scope)
        _different(source.directory, destination_directory)
        destination = PublicCorpusStore(destination_directory)
        with source.session(self.scope, files_only=True) as incoming, closing(_readonly(incoming)) as original:
            image = _Session(original).verified_image()
            _validate_image(image)
            with destination.session(self.scope, files_only=True) as files:
                _start_backup(files)
                with closing(_new_database(files)) as copied:
                    original.backup(copied)
                    if _Session(copied).verified_image() != image:
                        raise CorpusStoreError("corpus_semantic_mismatch")
                    if copied.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() != "delete":
                        raise CorpusStoreError("corpus_durability_unavailable")
                with closing(_readonly(files, backup=True)) as check:
                    if _Session(check).verified_image() != image:
                        raise CorpusStoreError("corpus_semantic_mismatch")
                fd = files.file(_DB)
                os.fsync(fd)
                manifest = {"format": 1, "database_sha256": _file_digest(fd),
                            "semantic_sha256": _digest(image), "schema_version": image["schema_version"],
                            "revision": image["corpus_state"][1], "restore_epoch": image["corpus_state"][2]}
                _write(files.file(_MANIFEST, exclusive=True), manifest)
                files.validate()
                _flush_directory(files)
        return {"status": "backup_verified", "revision": image["corpus_state"][1]}

    @_safe
    def restore(self, backup_directory, destination):
        _authorize(self.scope)
        _different(backup_directory, destination.directory)
        backup = PublicCorpusStore(backup_directory)
        with backup.session(self.scope, files_only=True) as incoming:
            manifest = _decode(_read(incoming.file(_MANIFEST, readonly=True, create=False), 65536))
            if (type(manifest) is not dict or set(manifest) != {
                    "format", "database_sha256", "semantic_sha256", "schema_version", "revision", "restore_epoch"}
                    or type(manifest["format"]) is not int or manifest["format"] != 1
                    or type(manifest["schema_version"]) is not int
                    or type(manifest["revision"]) is not int
                    or type(manifest["restore_epoch"]) is not str
                    or any(type(manifest[k]) is not str or len(manifest[k]) != 64
                           or any(c not in "0123456789abcdef" for c in manifest[k])
                           for k in ("database_sha256", "semantic_sha256"))):
                raise CorpusStoreError("corpus_manifest_invalid")
            fd = incoming.file(_DB, readonly=True, create=False)
            if _file_digest(fd) != manifest["database_sha256"]:
                raise CorpusStoreError("corpus_backup_digest_mismatch")
            with closing(_readonly(incoming, backup=True)) as source:
                original = _Session(source).verified_image()
                _validate_image(original)
                if (manifest["semantic_sha256"] != _digest(original)
                        or manifest["schema_version"] != original["schema_version"]
                        or manifest["revision"] != original["corpus_state"][1]
                        or manifest["restore_epoch"] != original["corpus_state"][2]):
                    raise CorpusStoreError("corpus_manifest_invalid")
                with destination.session(self.scope, files_only=True) as files:
                    _start_install(files, origin="restore", fingerprint=manifest["database_sha256"])
                    with closing(_new_database(files)) as restored:
                        source.backup(restored)
                        if _Session(restored).verified_image() != original:
                            raise CorpusStoreError("corpus_semantic_mismatch")
                        epoch = uuid.uuid4().hex
                        restored.execute("BEGIN IMMEDIATE")
                        try:
                            _install(restored, origin="restore", fingerprint=manifest["database_sha256"],
                                     baseline=manifest["semantic_sha256"],
                                     parent_epoch=original["corpus_state"][2], epoch=epoch)
                            restored.commit()
                        except BaseException:
                            restored.rollback()
                            raise
                        image = _Session(restored).verified_image()
                        if (image["corpus_state"][3] != original["corpus_state"][3]
                                or image["operations"] != original["operations"]
                                or image["operation_steps"] != original["operation_steps"]):
                            raise CorpusStoreError("corpus_semantic_mismatch")
                    with closing(_readonly(files, installing=True)) as check:
                        if _Session(check).verified_image() != image:
                            raise CorpusStoreError("corpus_semantic_mismatch")
                    files.validate()
                    _verify_source(incoming, fd, manifest["database_sha256"])
                    _seal_install(files, epoch)
            _verify_source(incoming, fd, manifest["database_sha256"])
        return {"status": "restored", "rebuild_required": True}

    @_safe
    def rebuild(self, store, *, epoch, key, adapter, verifier):
        """Explicit injected proof boundary, not a live Pinecone adapter.

        quiescent(epoch=...) must prove all old namespace writers/requests stopped,
        including post-backup requests absent from the restored journal.
        matches_namespace(epoch=..., expected=...) proves the ENTIRE namespace,
        not sampled IDs. Unknown foreign IDs are never deleted to make it pass.
        Missing/uncertain proof leaves the durable gate closed. No automatic retry.
        """
        _authorize(self.scope)
        _token(epoch)
        _token(key)
        with store.session(self.scope) as session:
            image = session.verified_image()
            if epoch != image["corpus_state"][2]:
                raise CorpusStoreError("corpus_epoch_mismatch")
            if image["schema_version"] != 3:
                raise CorpusStoreError("corpus_maintenance_not_required")
            _validate_image(image)
            state = image["maintenance_state"][0]
            if state[5] == "ready":
                return {"status": "already_rebuilt"}
            expected = _projection(image["corpus_state"][3])
            known = set()
            for corpus in [image["corpus_state"][3]] + [
                    op[pos] for op in image["operations"] for pos in (9, 10)]:
                known.update(r["_id"] for _, _, records in _record_sets(corpus) for r in records)
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            if state[7] is not None and state[7] != key_hash:
                raise CorpusStoreError("corpus_intent_conflict")
            blocked = {"status": "recovery_required", "message": "لم يثبت اكتمال استعادة المعرفة بعد."}
            pending = session.pending()
            inherited = bool(pending and state[5] == "pending" and state[1] == "restore")
            if pending and not inherited and (
                    state[5] != "rebuilding" or pending[0]["operation_id"] != state[6]):
                return blocked
            if inherited and pending[0]["before"] != image["corpus_state"][3]:
                return blocked
            if pending and any(identifier not in known for step in pending[0]["steps"]
                               for identifier in step["record_ids"]):
                return blocked
            operation_id = state[6]
            if operation_id:
                if (pending[0]["before"] != image["corpus_state"][3]
                        or pending[0]["after"] != image["corpus_state"][3]):
                    return blocked
                row = session._db.execute("SELECT key_hash FROM operations WHERE operation_id=?",
                                          (operation_id,)).fetchone()
                if row[0] != key_hash:
                    raise CorpusStoreError("corpus_intent_conflict")
            try:
                if verifier.quiescent(epoch=epoch) is not True:
                    return blocked
                if inherited:
                    old_id = pending[0]["operation_id"]
                    if not self._settled(session, old_id, verifier):
                        return blocked
                    with session._transaction():
                        session._db.execute("UPDATE maintenance_state SET request_key_hash=? WHERE id=1",
                                            (key_hash,))
                    self._apply(session, old_id, expected, known, adapter)
                    if (not self._settled(session, old_id, verifier)
                            or verifier.matches_namespace(epoch=epoch, expected=deepcopy(expected)) is not True):
                        return blocked
                    # Preserve the old identity and before-image. Only verified
                    # compensation closes the inherited operation; the separate
                    # maintenance gate stays closed throughout this transaction.
                    with session._transaction():
                        current = session.snapshot()
                        row = session._db.execute(
                            "SELECT base_revision,before_payload,state FROM operations WHERE operation_id=?",
                            (old_id,)).fetchone()
                        if (row[0] != current["revision"] or json.loads(row[1]) != current["corpus"]
                                or row[2] not in ("prepared", "recovery_required")):
                            raise CorpusStoreError("corpus_revision_conflict")
                        session._db.execute(
                            "UPDATE operations SET state='compensated',result_code='compensated',"
                            "result_payload=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
                            (_json({"status": "failed_compensated"}), old_id))
                        _event(session._db, "inherited_operation_compensated",
                               {"restore_epoch": epoch, "operation_id": old_id})
                if operation_id is None:
                    operation_id = uuid.uuid4().hex
                    payload = _corpus(image["corpus_state"][3])
                    digest = _digest({"maintenance": state[2:4], "epoch": epoch})
                    with session._transaction():
                        session._db.execute(
                            "INSERT INTO operations VALUES(?,?,?,?,?,?,?,'prepared',?,?,NULL,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?,NULL)",
                            (operation_id, epoch, "public-knowledge-sync", key_hash, digest, "reindex",
                             image["corpus_state"][1], payload, payload, digest))
                        session._db.execute("UPDATE maintenance_state SET state='rebuilding',operation_id=?,request_key_hash=? WHERE id=1",
                                            (operation_id, key_hash))
                attempts = [{"ordinal": i, **v} for i, v in enumerate(session.pending()[0]["steps"])]
                if verifier.settled(operation_id, attempts=deepcopy(attempts)) is not True:
                    return blocked
                if not inherited:
                    self._apply(session, operation_id, expected, known, adapter)
                attempts = [{"ordinal": i, **v} for i, v in enumerate(session.pending()[0]["steps"])]
                if (verifier.settled(operation_id, attempts=deepcopy(attempts)) is not True
                        or verifier.matches_namespace(epoch=epoch, expected=deepcopy(expected)) is not True):
                    return blocked
                with session._transaction():
                    session._db.execute(
                        "UPDATE operations SET state='committed',result_code='committed',"
                        "result_payload=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?",
                        (_json({"status": "rebuilt"}), operation_id))
                    session._db.execute("UPDATE corpus_state SET revision=revision+1 WHERE id=1")
                    session._db.execute("UPDATE maintenance_state SET state='ready' WHERE id=1")
                    _event(session._db, "index_rebuild_verified", {"restore_epoch": epoch, "operation_id": operation_id})
                return {"status": "rebuilt", "records": len(expected)}
            except Exception:
                return blocked


    @staticmethod
    def _settled(session, operation_id, verifier):
        pending = session.pending()
        if not pending or pending[0]["operation_id"] != operation_id:
            return False
        attempts = [{"ordinal": i, **step} for i, step in enumerate(pending[0]["steps"])]
        return verifier.settled(operation_id, attempts=deepcopy(attempts)) is True

    def _apply(self, session, operation_id, expected, known, adapter):
        for action, values, batch_size in (
                ("upsert", [expected[k] for k in sorted(expected)], 100),
                ("delete", sorted(known - expected.keys()), 1000)):
            for start in range(0, len(values), batch_size):
                batch = deepcopy(values[start:start + batch_size])
                ids = [v["_id"] for v in batch] if action == "upsert" else batch
                ordinal = session.record_step(operation_id, action=action, record_ids=ids, recovery=True)
                adapter.apply_public_knowledge_effect(
                    scope=self.scope, operation_id=operation_id, step_ordinal=ordinal,
                    action=action, values=batch)
