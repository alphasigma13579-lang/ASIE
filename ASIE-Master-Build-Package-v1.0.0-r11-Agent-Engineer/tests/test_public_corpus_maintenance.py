"""Offline maintenance acceptance. All providers and directories are disposable."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
import sqlite3
from types import SimpleNamespace

import pytest

from backend.public_corpus_store import CorpusStoreError, PublicCorpusStore
from backend.public_corpus_maintenance import PublicCorpusMaintenance, _digest, _validate_corpus
from backend.public_knowledge_lifecycle import PublicKnowledgeLifecycle
from test_public_corpus_store import (
    private_test_directory, scope, canonical_record, LifecycleIndex,
    FakeTavily, tenant, tenant_principal, NOW,
)


def directory(tmp_path, name):
    target = tmp_path / name
    # Python 3.13 mkdir(0700) installs an OWNER RIGHTS ACE on Windows.
    # Inherit the fixture's explicit service-user/SYSTEM/Admin ACL instead.
    target.mkdir(mode=0o777 if os.name == "nt" else 0o700)
    return target


def legacy():
    record = canonical_record()
    return {"schema_version": 1, "source_of_truth": True,
            "sources": {"mof-open-data": {
                "status": "active", "records": [record], "versions": [],
                "current_version": 1, "content_sha256": record["content_sha256"],
                "source_url": record["source_url"], "last_result": "changed_upserted",
                "last_changed_at": NOW, "last_checked_at": NOW}},
            "audit_events": [{"event": "source_version_activated", "source_id": "mof-open-data",
                              "version": 1, "at": NOW}]}


def history():
    value = legacy()
    source = value["sources"]["mof-open-data"]
    source["versions"] = [{"version": 1, "content_sha256": source["content_sha256"],
                          "records": deepcopy(source["records"]), "retained_at": NOW}]
    source["current_version"] = 2
    source["content_sha256"] = "b" * 64
    for record in source["records"]:
        record["version"] = 2
        record["content_sha256"] = "b" * 64
        record["evidence_ref"] = "public:mof-open-data:sha256:" + "b" * 64
    return value


def write_legacy(tmp_path, value=None, raw=None):
    path = directory(tmp_path, "legacy") / "public_knowledge_corpus.json"
    path.write_bytes(raw if raw is not None else json.dumps(value or legacy()).encode())
    path.chmod(0o600)
    return path


def install(tmp_path, value=None):
    path = write_legacy(tmp_path, value=value)
    store = PublicCorpusStore(directory(tmp_path, "imported"))
    maintenance = PublicCorpusMaintenance(scope=scope())
    maintenance.import_legacy(path.parent, store)
    return maintenance, store, path


def image(store):
    with store.session(scope()) as session:
        return session.verified_image()


def service(store, index):
    return PublicKnowledgeLifecycle(store=store, scope=scope(),
        tavily=FakeTavily("official facts"), pinecone=index, verifier=index,
        project_organization_resolver=lambda project: project.removeprefix("project-"), now=lambda: NOW)


class Index(LifecycleIndex):
    def __init__(self):
        super().__init__()
        self.quiet = True
        self.complete = True

    def quiescent(self, *, epoch):
        return self.quiet

    def matches_namespace(self, *, epoch, expected):
        return self.complete and self.records == expected


def test_import_preserves_original_history_audit_and_idempotence(tmp_path):
    value = history()
    maintenance, store, path = install(tmp_path, value)
    original = path.read_bytes()
    first = image(store)
    assert first["corpus_state"][3] == value
    assert first["imports"] == [[hashlib.sha256(original).hexdigest(), 1, 2]]
    assert maintenance.import_legacy(path.parent, store)["status"] == "already_imported"
    assert image(store) == first and path.read_bytes() == original
    value["audit_events"].append({"event": "source_restored", "source_id": "mof-open-data", "at": NOW})
    path.write_text(json.dumps(value))
    with pytest.raises(CorpusStoreError, match="^corpus_destination_not_new$"):
        maintenance.import_legacy(path.parent, store)
    assert image(store) == first


@pytest.mark.parametrize("corruption", [
    "duplicate_record", "duplicate_version", "missing_metadata", "wrong_owner",
    "version_mismatch", "chunk_count", "project_context", "bad_tombstone", "active_deleted", "bad_audit",
])
def test_invalid_import_rejected_before_destination_database(tmp_path, corruption):
    value = history()
    source = value["sources"]["mof-open-data"]
    if corruption == "duplicate_record":
        source["records"] *= 2
    elif corruption == "duplicate_version":
        source["versions"] *= 2
    elif corruption == "missing_metadata":
        del source["versions"][0]["records"][0]["license_ref"]
    elif corruption == "wrong_owner":
        source["versions"][0]["records"][0]["source_id"] = "different"
    elif corruption == "version_mismatch":
        source["current_version"] = 1
    elif corruption == "chunk_count":
        source["records"][0]["chunk_count"] = 2
    elif corruption == "project_context":
        source["project_id"] = "PRIVATE_MARKER"
    elif corruption == "bad_tombstone":
        source["status"] = "deleted_tombstone"
    elif corruption == "active_deleted":
        source["deleted_at"] = NOW
    else:
        value["audit_events"][0]["source_id"] = "missing"
    path = write_legacy(tmp_path, value)
    before = path.read_bytes()
    target = PublicCorpusStore(directory(tmp_path, "destination"))
    with pytest.raises(CorpusStoreError) as caught:
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, target)
    assert "PRIVATE_MARKER" not in str(caught.value)
    assert not (target.directory / "public_knowledge.sqlite3").exists()
    assert path.read_bytes() == before


@pytest.mark.parametrize("raw", [
    b'{"sources":{},"sources":{}}', b'{"schema_version":',
    b'{"value":NaN}', b'\xff', b'[' * 10000,
])
def test_invalid_encoded_import_is_safe_and_non_mutating(tmp_path, raw):
    path = write_legacy(tmp_path, raw=raw)
    target = PublicCorpusStore(directory(tmp_path, "destination"))
    with pytest.raises(CorpusStoreError):
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, target)
    assert path.read_bytes() == raw
    assert not (target.directory / "public_knowledge.sqlite3").exists()


def test_import_gate_blocks_normal_writes_reads_and_recovery(tmp_path):
    maintenance, store, _ = install(tmp_path)
    before = image(store)
    index = Index()
    lifecycle = service(store, index)
    epoch = before["corpus_state"][2]
    with pytest.raises(CorpusStoreError, match="^corpus_recovery_required$"):
        lifecycle.reindex(key="normal", epoch=epoch)
    assert lifecycle.recover()["status"] == "recovery_required"
    assert lifecycle.evidence(scope=tenant(), principal=tenant_principal(),
                              query="PRIVATE_MARKER") == lifecycle._unavailable()
    assert not index.calls and image(store) == before
    assert maintenance.rebuild(store, epoch=epoch, key="maintenance",
                               adapter=index, verifier=index)["status"] == "rebuilt"
    assert index.records
    with store.session(scope()) as session:
        assert not session.snapshot()["recovery_required"]
    after = image(store)
    assert maintenance.rebuild(store, epoch=epoch, key="maintenance",
                               adapter=index, verifier=index)["status"] == "already_rebuilt"
    assert image(store) == after


def test_backup_restore_preserves_journal_and_rejects_lost_old_retry(tmp_path):
    maintenance, store, path = install(tmp_path, history())
    index = Index()
    epoch = image(store)["corpus_state"][2]
    maintenance.rebuild(store, epoch=epoch, key="initial-index", adapter=index, verifier=index)
    original = image(store)
    backup = directory(tmp_path, "backup")
    assert maintenance.backup(store, backup)["status"] == "backup_verified"
    original_bytes = path.read_bytes()
    # Completed AFTER the backup; the restored journal cannot contain its result.
    service(store, index).reindex(key="after-backup", epoch=epoch)
    after_live_operation = image(store)
    restored = PublicCorpusStore(directory(tmp_path, "restored"))
    assert maintenance.restore(backup, restored)["rebuild_required"]
    restored_image = image(restored)
    assert restored_image["corpus_state"][2] != epoch
    assert restored_image["corpus_state"][3] == original["corpus_state"][3]
    assert restored_image["operations"] == original["operations"]
    assert restored_image["operation_steps"] == original["operation_steps"]
    calls = deepcopy(index.calls)
    with pytest.raises(CorpusStoreError, match="^corpus_epoch_mismatch$"):
        service(restored, index).reindex(key="after-backup", epoch=epoch)
    with pytest.raises(CorpusStoreError, match="^corpus_epoch_mismatch$"):
        maintenance.rebuild(restored, key="old", epoch=epoch, adapter=index, verifier=index)
    assert image(restored) == restored_image and index.calls == calls
    assert image(store) == after_live_operation and path.read_bytes() == original_bytes


@pytest.mark.parametrize("proof", ["quiescence", "settlement", "namespace", "foreign_id"])
def test_missing_external_proof_never_opens_gate_or_deletes_unknown(tmp_path, proof):
    maintenance, store, _ = install(tmp_path)
    index = Index()
    if proof == "quiescence":
        index.quiet = False
    elif proof == "settlement":
        index.settled = lambda *a, **kw: False
    elif proof == "namespace":
        index.complete = False
    else:
        index.records["foreign"] = {"_id": "foreign"}
    epoch = image(store)["corpus_state"][2]
    assert maintenance.rebuild(store, epoch=epoch, key="rebuild",
                               adapter=index, verifier=index)["status"] == "recovery_required"
    with store.session(scope()) as session:
        assert session.snapshot()["recovery_required"]
    if proof == "foreign_id":
        assert index.records["foreign"] == {"_id": "foreign"}
    if proof in ("quiescence", "settlement"):
        assert not index.calls


def test_interrupted_rebuild_reopens_and_requires_settlement_before_retry(tmp_path):
    from test_public_corpus_store import Interrupted
    maintenance, store, _ = install(tmp_path)
    index = Index()
    index.failure = Interrupted()
    epoch = image(store)["corpus_state"][2]
    with pytest.raises(Interrupted):
        maintenance.rebuild(store, epoch=epoch, key="rebuild", adapter=index, verifier=index)
    reopened = PublicCorpusStore(store.directory)
    before = image(reopened)
    calls = deepcopy(index.calls)
    index.settled = lambda *a, **kw: False
    assert maintenance.rebuild(reopened, epoch=epoch, key="rebuild",
                               adapter=index, verifier=index)["status"] == "recovery_required"
    assert index.calls == calls and image(reopened) == before
    with pytest.raises(CorpusStoreError, match="^corpus_intent_conflict$"):
        maintenance.rebuild(reopened, epoch=epoch, key="different",
                            adapter=index, verifier=index)


@pytest.mark.parametrize("damage", ["bytes", "manifest", "revision", "orphan", "journal"])
def test_corrupt_backup_never_creates_restored_database(tmp_path, damage):
    maintenance, store, _ = install(tmp_path)
    backup = directory(tmp_path, "backup")
    maintenance.backup(store, backup)
    manifest_path = backup / "public_knowledge.manifest.json"
    dbpath = backup / "public_knowledge.sqlite3"
    manifest = json.loads(manifest_path.read_text())
    if damage == "bytes":
        with dbpath.open("r+b") as stream:
            stream.write(b"not sqlite")
    elif damage == "manifest":
        manifest["unexpected"] = True
    elif damage == "revision":
        manifest["revision"] += 1
    elif damage == "orphan":
        with closing(sqlite3.connect(dbpath)) as db:
            db.execute("INSERT INTO operation_steps VALUES('missing',0,?)",
                       (json.dumps({"action": "delete", "record_ids": ["valid"]}),))
            db.commit()
            assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        # Even an updated physical hash must not bypass relational validation.
        manifest["database_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    else:
        with closing(sqlite3.connect(dbpath)) as db:
            db.execute("UPDATE corpus_state SET payload=?", ('{"schema_version":1}',))
            db.commit()
        manifest["database_sha256"] = hashlib.sha256(dbpath.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    before = image(store)
    with pytest.raises(CorpusStoreError):
        maintenance.restore(backup, target)
    assert not (target.directory / "public_knowledge.sqlite3").exists()
    assert image(store) == before


def test_import_and_restore_never_overwrite_existing_destination(tmp_path):
    maintenance, store, _ = install(tmp_path)
    backup = directory(tmp_path, "backup")
    maintenance.backup(store, backup)
    before = image(store)
    with pytest.raises(CorpusStoreError):
        maintenance.restore(backup, store)
    assert image(store) == before
    manifest = (backup / "public_knowledge.manifest.json").read_bytes()
    with pytest.raises(CorpusStoreError):
        maintenance.backup(store, backup)
    assert (backup / "public_knowledge.manifest.json").read_bytes() == manifest


@pytest.mark.parametrize("method", ["import_legacy", "backup", "restore", "rebuild"])
def test_scope_revalidated_before_any_maintenance_io(tmp_path, monkeypatch, method):
    maintenance = PublicCorpusMaintenance(scope=scope())
    maintenance.scope = tenant()
    monkeypatch.setattr(os, "open", lambda *a, **kw: pytest.fail("unauthorized I/O"))
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: pytest.fail("unauthorized DB"))
    store = PublicCorpusStore(tmp_path)
    with pytest.raises(CorpusStoreError, match="^corpus_scope_denied$"):
        if method == "import_legacy":
            maintenance.import_legacy(tmp_path, store)
        elif method == "backup":
            maintenance.backup(store, tmp_path)
        elif method == "restore":
            maintenance.restore(tmp_path, store)
        else:
            maintenance.rebuild(store, epoch="epoch", key="key", adapter=None, verifier=None)


def test_tombstones_and_history_not_reintroduced_during_rebuild(tmp_path):
    value = history()
    value["sources"]["mof-open-data"]["status"] = "deleted_tombstone"
    value["sources"]["mof-open-data"]["deleted_at"] = NOW
    value["sources"]["mof-open-data"]["last_result"] = "deleted"
    maintenance, store, _ = install(tmp_path, value)
    index = Index()
    record = value["sources"]["mof-open-data"]["records"][0]
    index.records[record["_id"]] = deepcopy(record)
    epoch = image(store)["corpus_state"][2]
    assert maintenance.rebuild(store, epoch=epoch, key="rebuild",
                               adapter=index, verifier=index)["status"] == "rebuilt"
    assert not index.records
    assert image(store)["corpus_state"][3] == value


def test_partial_manifest_is_not_an_accepted_backup(tmp_path, monkeypatch):
    import backend.public_corpus_maintenance as module
    maintenance, store, _ = install(tmp_path)
    backup = directory(tmp_path, "backup")
    def interrupted(fd, value):
        os.write(fd, b'{"format":')
        raise OSError("PRIVATE_MARKER")
    monkeypatch.setattr(module, "_write", interrupted)
    with pytest.raises(CorpusStoreError) as caught:
        maintenance.backup(store, backup)
    assert "PRIVATE_MARKER" not in str(caught.value)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    with pytest.raises(CorpusStoreError):
        maintenance.restore(backup, target)
    assert not (target.directory / "public_knowledge.sqlite3").exists()


def test_missing_source_backup_does_not_initialize_empty_database(tmp_path):
    source = PublicCorpusStore(directory(tmp_path, "missing"))
    target = directory(tmp_path, "backup")
    with pytest.raises(CorpusStoreError):
        PublicCorpusMaintenance(scope=scope()).backup(source, target)
    assert not (source.directory / "public_knowledge.sqlite3").exists()
    assert not (target / "public_knowledge.sqlite3").exists()


def test_interrupted_rebuild_can_resume_with_verified_adapter(tmp_path):
    from test_public_corpus_store import Interrupted
    maintenance, store, _ = install(tmp_path)
    index = Index()
    index.failure = Interrupted()
    epoch = image(store)["corpus_state"][2]
    with pytest.raises(Interrupted):
        maintenance.rebuild(store, epoch=epoch, key="rebuild", adapter=index, verifier=index)
    assert maintenance.rebuild(PublicCorpusStore(store.directory), epoch=epoch, key="rebuild",
                               adapter=index, verifier=index)["status"] == "rebuilt"
    with store.session(scope()) as session:
        assert not session.snapshot()["recovery_required"]


def test_unknown_pending_identifier_rejected_before_verifier(tmp_path):
    from test_public_corpus_store import Interrupted
    maintenance, store, _ = install(tmp_path)
    index = Index()
    index.failure = Interrupted()
    epoch = image(store)["corpus_state"][2]
    with pytest.raises(Interrupted):
        maintenance.rebuild(store, epoch=epoch, key="rebuild", adapter=index, verifier=index)
    with store.session(scope()) as session:
        session._db.execute("UPDATE operation_steps SET payload=?",
                            (json.dumps({"action": "delete", "record_ids": ["foreign"]}),))
    index.quiescent = lambda **kw: pytest.fail("corrupt ownership reached verifier")
    calls = deepcopy(index.calls)
    assert maintenance.rebuild(store, epoch=epoch, key="rebuild",
                               adapter=index, verifier=index)["status"] == "recovery_required"
    assert index.calls == calls


def test_backup_and_import_obey_existing_store_lock(tmp_path):
    maintenance, store, path = install(tmp_path)
    locked = PublicCorpusStore(store.directory, lock_timeout=0)
    with store.session(scope()):
        with pytest.raises(CorpusStoreError, match="^corpus_busy$"):
            maintenance.backup(locked, directory(tmp_path, "backup"))
        with pytest.raises(CorpusStoreError, match="^corpus_busy$"):
            maintenance.import_legacy(path.parent, locked)


@pytest.mark.skipif(os.name == "nt", reason="Windows reparse/ACL controls covered by store suite")
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "public_permissions"])
def test_legacy_file_path_controls_preserve_target(tmp_path, kind):
    path = write_legacy(tmp_path)
    before = path.read_bytes()
    other = tmp_path / "original.json"
    if kind != "public_permissions":
        path.rename(other)
        if kind == "symlink":
            path.symlink_to(other)
        else:
            os.link(other, path)
    else:
        path.chmod(0o644)
    store = PublicCorpusStore(directory(tmp_path, "destination"))
    with pytest.raises(CorpusStoreError, match="^corpus_path_invalid$"):
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, store)
    assert path.read_bytes() == before
    assert not (store.directory / "public_knowledge.sqlite3").exists()


def test_restore_interruption_after_copy_cannot_expose_old_writable_epoch(tmp_path, monkeypatch):
    import backend.public_corpus_maintenance as module
    from test_public_corpus_store import Interrupted
    source = v2_store(tmp_path)
    maintenance = PublicCorpusMaintenance(scope=scope())
    backup = directory(tmp_path, "backup")
    maintenance.backup(source, backup)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(module, "_install", interrupt)
    with pytest.raises(Interrupted):
        maintenance.restore(backup, target)
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        with target.session(scope()):
            pytest.fail("interrupted restore became writable")
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        maintenance.backup(target, directory(tmp_path, "partial-backup"))


def test_import_commit_before_seal_is_recoverable_but_not_automatically_readable(tmp_path, monkeypatch):
    import backend.public_corpus_maintenance as module
    from test_public_corpus_store import Interrupted
    path = write_legacy(tmp_path)
    original = path.read_bytes()
    target = PublicCorpusStore(directory(tmp_path, "imported"))
    maintenance = PublicCorpusMaintenance(scope=scope())
    seal = module._seal_install
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(module, "_seal_install", interrupt)
    with pytest.raises(Interrupted):
        maintenance.import_legacy(path.parent, target)
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        with target.session(scope()):
            pytest.fail("unverified import became readable")
    monkeypatch.setattr(module, "_seal_install", seal)
    assert maintenance.import_legacy(path.parent, target)["status"] == "already_imported"
    assert image(target)["corpus_state"][3] == legacy()
    assert path.read_bytes() == original


def v2_store(tmp_path):
    store = PublicCorpusStore(directory(tmp_path, "v2-source"))
    with store.session(scope()) as session:
        snap = session.snapshot()
        op = session.begin(key="v2-write", epoch=snap["restore_epoch"], kind="sync",
                           intent={"purpose": "test"}, expected_revision=0, after=legacy())
        session.commit(op.operation_id)
    return store


def test_v2_backup_restores_as_v3_without_upgrading_original(tmp_path):
    source = v2_store(tmp_path)
    before = image(source)
    assert before["schema_version"] == 2
    maintenance = PublicCorpusMaintenance(scope=scope())
    backup = directory(tmp_path, "backup")
    maintenance.backup(source, backup)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    maintenance.restore(backup, target)
    after = image(target)
    assert after["schema_version"] == 3
    assert after["corpus_state"][3] == before["corpus_state"][3]
    assert after["operations"] == before["operations"]
    assert after["operation_steps"] == before["operation_steps"]
    assert after["corpus_state"][2] != before["corpus_state"][2]
    assert image(source) == before


def test_restored_unfinished_old_operation_is_preserved_not_falsely_settled(tmp_path):
    source = v2_store(tmp_path)
    with source.session(scope()) as session:
        snap = session.snapshot()
        session.begin(key="unfinished", epoch=snap["restore_epoch"], kind="reindex",
                      intent={}, expected_revision=snap["revision"], after=snap["corpus"])
    maintenance = PublicCorpusMaintenance(scope=scope())
    backup = directory(tmp_path, "backup")
    maintenance.backup(source, backup)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    maintenance.restore(backup, target)
    before = image(target)
    index = Index()
    index.settled = lambda *a, **kw: False
    assert maintenance.rebuild(target, key="new", epoch=before["corpus_state"][2],
                               adapter=index, verifier=index)["status"] == "recovery_required"
    assert image(target) == before and not index.calls
    index.settled = LifecycleIndex.settled.__get__(index, Index)
    assert maintenance.rebuild(target, key="new", epoch=before["corpus_state"][2],
                               adapter=index, verifier=index)["status"] == "rebuilt"
    with target.session(scope()) as session:
        assert not session.snapshot()["recovery_required"]
        assert session._db.execute(
            "SELECT state FROM operations WHERE operation_id=?",
            (before["operations"][-1][1],)).fetchone() == ("compensated",)
    assert image(source)["operations"][-1][8] == "prepared"


def test_provider_exception_does_not_leak_to_result_or_journal(tmp_path):
    maintenance, store, _ = install(tmp_path)
    index = Index()
    index.failure = RuntimeError("SECRET_CREDENTIAL_MARKER")
    epoch = image(store)["corpus_state"][2]
    result = maintenance.rebuild(store, key="rebuild", epoch=epoch, adapter=index, verifier=index)
    assert result["status"] == "recovery_required"
    assert "SECRET_CREDENTIAL_MARKER" not in json.dumps(result) + json.dumps(image(store))


def test_inherited_recovery_key_is_durable_before_any_compensation_effect(tmp_path):
    from test_public_corpus_store import Interrupted
    source = v2_store(tmp_path)
    with source.session(scope()) as session:
        snap = session.snapshot()
        session.begin(key="old", epoch=snap["restore_epoch"], kind="delete",
                      intent={}, expected_revision=snap["revision"], after=snap["corpus"])
    maintenance = PublicCorpusMaintenance(scope=scope())
    backup = directory(tmp_path, "backup")
    maintenance.backup(source, backup)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    maintenance.restore(backup, target)
    index = Index()
    index.failure = Interrupted()
    epoch = image(target)["corpus_state"][2]
    with pytest.raises(Interrupted):
        maintenance.rebuild(target, key="recovery-key", epoch=epoch, adapter=index, verifier=index)
    calls = deepcopy(index.calls)
    with pytest.raises(CorpusStoreError, match="^corpus_intent_conflict$"):
        maintenance.rebuild(target, key="different-key", epoch=epoch, adapter=index, verifier=index)
    assert index.calls == calls
    assert maintenance.rebuild(target, key="recovery-key", epoch=epoch,
                               adapter=index, verifier=index)["status"] == "rebuilt"


@pytest.mark.parametrize("repeat", [False, True])
@pytest.mark.parametrize("mutation", ["atomic_replace", "in_place"])
def test_concurrent_legacy_change_cannot_be_accepted_as_current(tmp_path, monkeypatch, repeat, mutation):
    from concurrent.futures import ThreadPoolExecutor
    import backend.public_corpus_maintenance as module
    path = write_legacy(tmp_path)
    original = path.read_bytes()
    store = PublicCorpusStore(directory(tmp_path, "imported"))
    maintenance = PublicCorpusMaintenance(scope=scope())
    before = None
    if repeat:
        maintenance.import_legacy(path.parent, store)
        before = image(store)
    changed = history()
    replacement = json.dumps(changed).encode()
    outcomes = []
    verified = module._Session.verified_image

    def mutate():
        try:
            if mutation == "atomic_replace":
                temporary = path.with_suffix(".replacement")
                temporary.write_bytes(replacement)
                temporary.chmod(0o600)
                temporary.replace(path)
            else:
                path.write_bytes(replacement)
            return "changed"
        except PermissionError:
            # Windows pinned handles can prevent the attempted write/replacement.
            assert os.name == "nt"
            return "prevented"

    def after_initial_validation(session):
        result = verified(session)
        if not outcomes:
            with ThreadPoolExecutor(max_workers=1) as pool:
                outcomes.append(pool.submit(mutate).result(timeout=10))
        return result

    monkeypatch.setattr(module._Session, "verified_image", after_initial_validation)
    failure = None
    try:
        result = maintenance.import_legacy(path.parent, store)
    except CorpusStoreError as error:
        failure = error
    assert len(outcomes) == 1
    monkeypatch.setattr(module._Session, "verified_image", verified)
    if outcomes == ["prevented"]:
        assert failure is None
        assert result["status"] == ("already_imported" if repeat else "imported")
        assert path.read_bytes() == original
    else:
        assert str(failure) in ("corpus_path_invalid", "corpus_source_changed")
        assert path.read_bytes() == replacement
        if repeat:
            assert image(store) == before
        else:
            with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
                with store.session(scope()):
                    pytest.fail("changed source produced a sealed import")


@pytest.mark.parametrize("interrupted", [False, True])
def test_backup_artifact_cannot_run_before_explicit_restore(tmp_path, monkeypatch, interrupted):
    import backend.public_corpus_maintenance as module
    from test_public_corpus_store import Interrupted
    source = v2_store(tmp_path)
    original = image(source)
    maintenance = PublicCorpusMaintenance(scope=scope())
    backup = directory(tmp_path, "backup")
    write = module._write
    if interrupted:
        def interrupt_manifest(fd, value):
            raise Interrupted()
        monkeypatch.setattr(module, "_write", interrupt_manifest)
        with pytest.raises(Interrupted):
            maintenance.backup(source, backup)
        monkeypatch.setattr(module, "_write", write)
    else:
        assert maintenance.backup(source, backup)["status"] == "backup_verified"
    assert (backup / "public_knowledge.backup").read_bytes() == b"backup-v1"
    database = backup / "public_knowledge.sqlite3"
    saved = database.read_bytes()
    with monkeypatch.context() as guarded:
        guarded.setattr(sqlite3, "connect", lambda *a, **kw: pytest.fail("backup opened as live database"))
        with pytest.raises(CorpusStoreError, match="^corpus_backup_requires_restore$"):
            with PublicCorpusStore(backup).session(scope()):
                pytest.fail("backup became runnable")
    assert database.read_bytes() == saved
    assert not (backup / "public_knowledge.sqlite3-wal").exists()
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    if interrupted:
        with pytest.raises(CorpusStoreError):
            maintenance.restore(backup, target)
        assert not (target.directory / "public_knowledge.sqlite3").exists()
    else:
        assert maintenance.restore(backup, target)["status"] == "restored"
        restored = image(target)
        assert restored["corpus_state"][2] != original["corpus_state"][2]
        assert restored["corpus_state"][3] == original["corpus_state"][3]
        with target.session(scope()) as session:
            assert session.snapshot()["recovery_required"]
    assert image(source) == original


@pytest.mark.parametrize("field", ["project_id", "organization_id", "query", "owner_notes", "payload"])
def test_import_rejects_private_or_unknown_audit_fields(tmp_path, field):
    value = legacy()
    value["audit_events"][0][field] = "PRIVATE_AUDIT_MARKER"
    path = write_legacy(tmp_path, value)
    original = path.read_bytes()
    target = PublicCorpusStore(directory(tmp_path, "destination"))
    with pytest.raises(CorpusStoreError) as caught:
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, target)
    assert "PRIVATE_AUDIT_MARKER" not in str(caught.value)
    assert path.read_bytes() == original
    assert not (target.directory / "public_knowledge.sqlite3").exists()


def test_canonical_audit_event_schemas_preserve_all_supported_events():
    value = legacy()
    value["audit_events"].extend([
        {"event": "source_quarantined", "source_id": "mof-open-data",
         "anomalies": ["prompt_injection_suspected"], "at": NOW},
        {"event": "source_deleted", "source_id": "mof-open-data", "at": NOW},
        {"event": "source_restored", "source_id": "mof-open-data", "at": NOW},
        {"event": "public_namespace_reindexed", "records": 1, "stale_records_deleted": 0, "at": NOW},
        {"event": "empty_public_projection_reconciled", "records_deleted": 1, "at": NOW},
    ])
    before = deepcopy(value)
    assert _validate_corpus(value) == 1
    assert value == before
    for event in [
        {"event": "unknown", "at": NOW},
        {"event": "source_version_activated", "source_id": "mof-open-data", "version": True, "at": NOW},
        {"event": "source_quarantined", "source_id": "mof-open-data", "anomalies": ["PRIVATE_AUDIT_MARKER"], "at": NOW},
        {"event": "public_namespace_reindexed", "records": "PRIVATE_AUDIT_MARKER", "stale_records_deleted": 0, "at": NOW},
    ]:
        invalid = deepcopy(value)
        invalid["audit_events"].append(event)
        with pytest.raises(CorpusStoreError, match="^corpus_import_invalid$"):
            _validate_corpus(invalid)


def test_interrupted_restore_cannot_be_resealed_by_legacy_import(tmp_path, monkeypatch):
    import backend.public_corpus_maintenance as module
    from test_public_corpus_store import Interrupted
    maintenance, original, path = install(tmp_path)
    backup = directory(tmp_path, "backup")
    maintenance.backup(original, backup)
    target = PublicCorpusStore(directory(tmp_path, "restored"))
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(module, "_install", interrupt)
    with pytest.raises(Interrupted):
        maintenance.restore(backup, target)
    marker = target.directory / "public_knowledge.installation"
    before = marker.read_bytes()
    assert before.startswith(b"pending:restore:")
    database = target.directory / "public_knowledge.sqlite3"
    saved = database.read_bytes()
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        maintenance.import_legacy(path.parent, target)
    assert marker.read_bytes() == before
    assert database.read_bytes() == saved
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        with target.session(scope()):
            pytest.fail("old epoch exposed after cross-operation retry")


def test_ready_v3_without_installation_marker_cannot_run_or_be_backed_up(tmp_path):
    maintenance, store, path = install(tmp_path)
    index = Index()
    epoch = image(store)["corpus_state"][2]
    assert maintenance.rebuild(store, epoch=epoch, key="ready", adapter=index, verifier=index)["status"] == "rebuilt"
    before = image(store)
    assert before["maintenance_state"][0][5] == "ready"
    marker = store.directory / "public_knowledge.installation"
    marker.unlink()  # Disposable artifact only: simulate copying DB without seal.
    calls = deepcopy(index.calls)
    artifacts = [store.directory / ("public_knowledge.sqlite3" + suffix)
                 for suffix in ("", "-wal", "-shm", "-journal")]
    saved = {p.name: p.read_bytes() if p.exists() else None for p in artifacts}
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        with store.session(scope()):
            pytest.fail("markerless v3 admitted")
    assert {p.name: p.read_bytes() if p.exists() else None for p in artifacts} == saved
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        maintenance.rebuild(store, epoch=epoch, key="retry", adapter=index, verifier=index)
    target = directory(tmp_path, "backup")
    with pytest.raises(CorpusStoreError, match="^corpus_installation_incomplete$"):
        maintenance.backup(store, target)
    with pytest.raises(CorpusStoreError):
        maintenance.import_legacy(path.parent, store)
    assert index.calls == calls
    assert not marker.exists()
    assert not (target / "public_knowledge.sqlite3").exists()


@pytest.mark.parametrize("method", ["import", "backup", "restore"])
@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_new_destination_rejects_existing_sidecars(tmp_path, monkeypatch, method, suffix):
    import backend.public_corpus_maintenance as module
    maintenance = PublicCorpusMaintenance(scope=scope())
    path = write_legacy(tmp_path)
    source = v2_store(tmp_path)
    backup = directory(tmp_path, "source-backup")
    if method == "restore":
        maintenance.backup(source, backup)
    target = PublicCorpusStore(directory(tmp_path, "target"))
    sidecar = target.directory / ("public_knowledge.sqlite3" + suffix)
    sidecar.write_bytes(b"UNRELATED_SIDECAR")
    sidecar.chmod(0o600)
    real_connect = sqlite3.connect
    def guarded_connect(database, *args, **kwargs):
        assert str(target.directory).replace("\\", "/") not in str(database).replace("\\", "/")
        return real_connect(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    with pytest.raises(CorpusStoreError, match="^corpus_destination_not_new$"):
        if method == "import":
            maintenance.import_legacy(path.parent, target)
        elif method == "backup":
            maintenance.backup(source, target.directory)
        else:
            maintenance.restore(backup, target)
    assert sidecar.read_bytes() == b"UNRELATED_SIDECAR"
    assert not (target.directory / "public_knowledge.installation").exists()
    assert not (target.directory / "public_knowledge.backup").exists()
    assert not (target.directory / "public_knowledge.sqlite3").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX links; Windows rejects all existing sidecars above")
@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_new_destination_rejects_linked_sidecar_without_touching_target(tmp_path, kind):
    path = write_legacy(tmp_path)
    target = PublicCorpusStore(directory(tmp_path, "target"))
    original = tmp_path / "unrelated"
    original.write_bytes(b"DO_NOT_MODIFY")
    sidecar = target.directory / "public_knowledge.sqlite3-wal"
    if kind == "symlink":
        sidecar.symlink_to(original)
    else:
        os.link(original, sidecar)
    with pytest.raises(CorpusStoreError, match="^corpus_destination_not_new$"):
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, target)
    assert original.read_bytes() == b"DO_NOT_MODIFY"
    assert not (target.directory / "public_knowledge.installation").exists()
    assert not (target.directory / "public_knowledge.backup").exists()
    assert not (target.directory / "public_knowledge.sqlite3").exists()


@pytest.mark.parametrize("damage", ["records", "history", "anomalies", "result"])
def test_reject_noncanonical_quarantine_or_diagnostic_metadata(damage):
    value = history()
    source = value["sources"]["mof-open-data"]
    if damage in ("records", "history"):
        source["status"] = "quarantined"
        if damage == "history":
            source["records"] = []
            source.pop("current_version")
            source.pop("content_sha256")
    elif damage == "anomalies":
        source["last_anomalies"] = ["PRIVATE_METADATA_MARKER"]
    else:
        source["last_result"] = "PRIVATE_METADATA_MARKER"
    with pytest.raises(CorpusStoreError, match="^corpus_import_invalid$"):
        _validate_corpus(value)


def test_canonical_empty_quarantine_and_active_anomaly_are_preserved():
    value = legacy()
    source = value["sources"]["mof-open-data"]
    source["last_result"] = "quarantined"
    source["last_anomalies"] = ["prompt_injection_suspected"]
    assert _validate_corpus(value) == 1  # Previous approved records remain active.
    source["status"] = "quarantined"
    source["records"] = []
    source["versions"] = []
    source.pop("current_version")
    source.pop("content_sha256")
    source.pop("last_changed_at")
    value["audit_events"] = [{"event": "source_quarantined", "source_id": "mof-open-data",
                              "anomalies": ["prompt_injection_suspected"], "at": NOW}]
    assert _validate_corpus(value) == 0


def test_existing_v2_session_uses_one_sqlite_connection(tmp_path, monkeypatch):
    store = v2_store(tmp_path)
    original = image(store)
    connect = sqlite3.connect
    calls = []
    def counted_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return connect(*args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", counted_connect)
    assert image(store) == original
    assert len(calls) == 1


@pytest.mark.parametrize("event,payload", [
    ("unknown_event", {"owner_notes": "PRIVATE_MAINTENANCE_MARKER"}),
    ("import_installed", {"input_sha256": "a" * 64, "baseline_sha256": "b" * 64,
                          "parent_epoch": "parent", "restore_epoch": "old",
                          "owner_notes": "PRIVATE_MAINTENANCE_MARKER"}),
    ("restore_installed", {"input_sha256": "invalid", "baseline_sha256": "b" * 64,
                           "parent_epoch": "parent", "restore_epoch": "old"}),
    ("inherited_operation_compensated", {"restore_epoch": "old", "operation_id": []}),
    ("index_rebuild_verified", {"restore_epoch": "old", "operation_id": "op",
                                "owner_notes": "PRIVATE_MAINTENANCE_MARKER"}),
    ("index_rebuild_verified", {"restore_epoch": "old"}),
])
def test_invalid_historical_maintenance_event_blocks_image_and_backup(tmp_path, event, payload):
    maintenance, store, _ = install(tmp_path)
    # Keep the authoritative latest install untouched: reject bad history too.
    with closing(sqlite3.connect(store.directory / "public_knowledge.sqlite3")) as db:
        db.execute("UPDATE maintenance_events SET sequence=2 WHERE sequence=1")
        db.execute("INSERT INTO maintenance_events VALUES(1,?,?)", (event, json.dumps(payload)))
        db.commit()
    target = directory(tmp_path, "backup")
    for action in (lambda: image(store), lambda: maintenance.backup(store, target)):
        with pytest.raises(CorpusStoreError) as caught:
            action()
        assert "PRIVATE_MAINTENANCE_MARKER" not in str(caught.value)
    assert not (target / "public_knowledge.sqlite3").exists()
    assert not (target / "public_knowledge.backup").exists()


@pytest.mark.parametrize("field", ["source_url", "last_checked_at", "last_changed_at", "last_result"])
def test_import_requires_canonical_active_metadata(tmp_path, field):
    value = legacy()
    del value["sources"]["mof-open-data"][field]
    path = write_legacy(tmp_path, value)
    target = PublicCorpusStore(directory(tmp_path, "destination"))
    with pytest.raises(CorpusStoreError, match="^corpus_import_invalid$"):
        PublicCorpusMaintenance(scope=scope()).import_legacy(path.parent, target)
    assert not (target.directory / "public_knowledge.sqlite3").exists()


@pytest.mark.parametrize("status,result", [
    ("active", "deleted"), ("deleted_tombstone", "restored"),
    ("deleted_tombstone", "unchanged"), ("quarantined", "changed_upserted"),
])
def test_source_status_and_result_cannot_contradict(status, result):
    value = legacy()
    source = value["sources"]["mof-open-data"]
    source["status"], source["last_result"] = status, result
    if status == "deleted_tombstone":
        source["deleted_at"] = NOW
    if status == "quarantined":
        source["records"] = []
        for key in ("current_version", "content_sha256", "last_changed_at"):
            source.pop(key)
    with pytest.raises(CorpusStoreError, match="^corpus_import_invalid$"):
        _validate_corpus(value)


@pytest.mark.parametrize("damage", ["missing", "wrong_state", "wrong_kind", "wrong_epoch", "false_compensation"])
def test_maintenance_events_require_matching_journal_operation(tmp_path, damage):
    maintenance, store, _ = install(tmp_path)
    index = Index()
    epoch = image(store)["corpus_state"][2]
    maintenance.rebuild(store, epoch=epoch, key="ready", adapter=index, verifier=index)
    with closing(sqlite3.connect(store.directory / "public_knowledge.sqlite3")) as db:
        event, raw = db.execute(
            "SELECT event,payload FROM maintenance_events WHERE event='index_rebuild_verified'").fetchone()
        payload = json.loads(raw)
        operation_id = payload["operation_id"]
        if damage == "missing":
            payload["operation_id"] = "nonexistent"
        elif damage == "wrong_epoch":
            payload["restore_epoch"] = "different"
        elif damage == "false_compensation":
            event = "inherited_operation_compensated"
        elif damage == "wrong_kind":
            db.execute("UPDATE operations SET kind='sync' WHERE operation_id=?", (operation_id,))
        else:
            db.execute("UPDATE operations SET state='compensated',result_code='compensated' WHERE operation_id=?",
                       (operation_id,))
        # Historical row followed by valid latest rebuild: validating only the
        # last rebuild event would miss the invalid reference.
        db.execute("INSERT INTO maintenance_events(event,payload) VALUES(?,?)", (event, json.dumps(payload)))
        db.execute("INSERT INTO maintenance_events(event,payload) VALUES('index_rebuild_verified',?)", (raw,))
        db.commit()
    target = directory(tmp_path, "backup")
    with pytest.raises(CorpusStoreError, match="^corpus_storage_invalid$"):
        image(store)
    with pytest.raises(CorpusStoreError):
        maintenance.backup(store, target)
    assert not (target / "public_knowledge.backup").exists()


@pytest.mark.parametrize("damage", ["forged_middle", "wrong_parent", "reused_epoch", "repeated_import"])
def test_installation_history_must_form_one_epoch_chain(tmp_path, damage):
    maintenance, source, _ = install(tmp_path)
    backup = directory(tmp_path, "backup")
    maintenance.backup(source, backup)
    restored = PublicCorpusStore(directory(tmp_path, "restored"))
    maintenance.restore(backup, restored)
    with closing(sqlite3.connect(restored.directory / "public_knowledge.sqlite3")) as db:
        rows = db.execute("SELECT sequence,event,payload FROM maintenance_events ORDER BY sequence").fetchall()
        first = json.loads(rows[0][2])
        final = json.loads(rows[-1][2])
        if damage == "forged_middle":
            forged = dict(final, parent_epoch=first["restore_epoch"], restore_epoch="forged-epoch")
            db.execute("UPDATE maintenance_events SET sequence=3 WHERE sequence=2")
            db.execute("INSERT INTO maintenance_events VALUES(2,'restore_installed',?)", (json.dumps(forged),))
        elif damage == "wrong_parent":
            final["parent_epoch"] = "not-the-predecessor"
            db.execute("UPDATE maintenance_events SET payload=? WHERE sequence=2", (json.dumps(final),))
        elif damage == "reused_epoch":
            final["restore_epoch"] = first["restore_epoch"]
            db.execute("UPDATE maintenance_events SET payload=? WHERE sequence=2", (json.dumps(final),))
        else:
            db.execute("UPDATE maintenance_events SET event='import_installed' WHERE sequence=2")
        db.commit()
    rejected = directory(tmp_path, "rejected-backup")
    with pytest.raises(CorpusStoreError, match="^corpus_storage_invalid$"):
        image(restored)
    with pytest.raises(CorpusStoreError):
        maintenance.backup(restored, rejected)
    assert not (rejected / "public_knowledge.backup").exists()


def test_repeated_restore_preserves_valid_epoch_chain(tmp_path):
    maintenance, original, _ = install(tmp_path)
    first_backup = directory(tmp_path, "first-backup")
    maintenance.backup(original, first_backup)
    first = PublicCorpusStore(directory(tmp_path, "first-restore"))
    maintenance.restore(first_backup, first)
    second_backup = directory(tmp_path, "second-backup")
    maintenance.backup(first, second_backup)
    second = PublicCorpusStore(directory(tmp_path, "second-restore"))
    maintenance.restore(second_backup, second)
    verified = image(second)
    assert [row[1] for row in verified["maintenance_events"]] == [
        "import_installed", "restore_installed", "restore_installed"]
    assert verified["corpus_state"][3] == image(original)["corpus_state"][3]
