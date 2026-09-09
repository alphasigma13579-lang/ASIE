from __future__ import annotations

from dataclasses import replace
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from backend.provider_security_control_plane import TrustedProviderScope
from backend.public_corpus_store import CorpusStoreError, PublicCorpusStore


def scope():
    return TrustedProviderScope.for_platform_workload("public-knowledge-sync")


def corpus(number=1):
    return {"schema_version": 1, "source_of_truth": True, "sources": {},
            "audit_events": [{"sequence": number}]}


def request(session, key="request-1", number=1):
    snap = session.snapshot()
    return dict(key=key, epoch=snap["restore_epoch"], kind="sync",
                intent={"sequence": number}, expected_revision=snap["revision"],
                after=corpus(number))


def test_atomic_commit_reopen_replay_and_changed_intent(tmp_path):
    store = PublicCorpusStore(tmp_path)
    with store.session(scope()) as session:
        args = request(session)
        operation = session.begin(**args)
        assert session.snapshot()["revision"] == 0
        assert session.snapshot()["recovery_required"]
        assert session.record_step(operation.operation_id, action="upsert",
                                   record_ids=["public-one"]) == 0
        assert session.commit(operation.operation_id).result_code == "committed"
    with store.session(scope()) as session:
        assert session.snapshot()["corpus"] == corpus()
        assert session.snapshot()["revision"] == 1
        assert session.begin(**args).operation_id == operation.operation_id
        with pytest.raises(CorpusStoreError, match="intent_conflict"):
            session.begin(**{**args, "intent": {"sequence": 2}})
        with pytest.raises(CorpusStoreError, match="revision_conflict"):
            session.begin(**{**args, "key": "new"})
        with pytest.raises(CorpusStoreError, match="epoch_mismatch"):
            session.begin(**{**args, "epoch": "old-epoch"})
        assert session.snapshot()["revision"] == 1
    with pytest.raises(CorpusStoreError, match="session_closed"):
        session.snapshot()


def test_pending_operation_survives_and_cannot_be_committed_by_new_session(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        args = request(session)
        operation = session.begin(**args)
        session.record_step(operation.operation_id, action="delete", record_ids=["old"])
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        pending = session.pending()[0]
        assert pending["before"]["sources"] == {}
        assert pending["after"] == corpus()
        assert pending["steps"] == [{"action": "delete", "record_ids": ["old"]}]
        for key in ("request-1", "different"):
            with pytest.raises(CorpusStoreError, match="recovery_required"):
                session.begin(**{**args, "key": key})
        with pytest.raises(CorpusStoreError, match="recovery_required"):
            session.commit(operation.operation_id)
        assert session.snapshot()["revision"] == 0


def test_explicit_recovery_gate_cannot_commit(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        operation = session.begin(**request(session))
        session.mark_recovery_required(operation.operation_id)
        assert session.pending()[0]["state"] == "recovery_required"
        with pytest.raises(CorpusStoreError, match="operation_not_prepared"):
            session.commit(operation.operation_id)


def test_no_io_for_unauthorized_scope(tmp_path, monkeypatch):
    def no_io(*args, **kwargs):
        pytest.fail("unauthorized call performed I/O")
    monkeypatch.setattr(os, "open", no_io)
    monkeypatch.setattr(sqlite3, "connect", no_io)
    trusted = scope()
    tenant = TrustedProviderScope.for_tenant(
        principal=SimpleNamespace(user_id="u", session_id="s",
                                  organization_id="org", role="analyst"),
        project_id="project", project_organization_resolver=lambda _: "org")
    bad = [None, tenant, TrustedProviderScope.for_platform_preflight(),
           replace(trusted, _proof=object()),
           SimpleNamespace(require_platform_workload=lambda _: None)]
    for candidate in bad:
        with pytest.raises(CorpusStoreError, match="scope_denied"):
            with PublicCorpusStore(tmp_path / "not-created").session(candidate):
                pytest.fail("unauthorized")
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("payload", [
    {"schema_version": 2, "source_of_truth": True, "sources": {}, "audit_events": []},
    {"schema_version": True, "source_of_truth": True, "sources": {}, "audit_events": []},
    {**corpus(), "sources": {"secret": "DO_NOT_LEAK"}},
    {**corpus(), "query": "customer query"},
    {**corpus(), "audit_events": [float("nan")]},
])
def test_invalid_payload_has_no_effect(tmp_path, payload):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        args = request(session)
        with pytest.raises(CorpusStoreError, match="payload_invalid") as error:
            session.begin(**{**args, "after": payload})
        assert "DO_NOT_LEAK" not in str(error.value)
        assert session.pending() == []
        assert session.snapshot()["revision"] == 0


def test_schema_and_durability(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()):
        pass
    path = tmp_path / "public_knowledge.sqlite3"
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        db.execute("PRAGMA user_version=999")
    with pytest.raises(CorpusStoreError, match="schema_unsupported"):
        with PublicCorpusStore(tmp_path).session(scope()):
            pass
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 999


def test_schema_zero_with_existing_data_not_overwritten(tmp_path):
    path = tmp_path / "public_knowledge.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE owner_data(value)")
        db.execute("INSERT INTO owner_data VALUES('keep')")
    with pytest.raises(CorpusStoreError, match="schema_unsupported"):
        with PublicCorpusStore(tmp_path).session(scope()):
            pass
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM owner_data").fetchone()[0] == "keep"


def test_effective_setting_mismatch_fails_closed(tmp_path, monkeypatch):
    real_connect = sqlite3.connect

    class Result:
        def fetchone(self):
            return (0,)

    class Connection:
        def __init__(self, *args, **kwargs):
            self.db = real_connect(*args, **kwargs)
        def execute(self, sql, *args):
            if sql == "PRAGMA synchronous":
                return Result()
            return self.db.execute(sql, *args)
        def __getattr__(self, name):
            return getattr(self.db, name)

    monkeypatch.setattr(sqlite3, "connect", Connection)
    with pytest.raises(CorpusStoreError, match="durability_unavailable"):
        with PublicCorpusStore(tmp_path).session(scope()):
            pass
    with real_connect(tmp_path / "public_knowledge.sqlite3") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0


def test_database_error_does_not_leak_and_releases_lock(tmp_path, monkeypatch):
    real_connect = sqlite3.connect
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("SENSITIVE_SECRET_PATH")
    monkeypatch.setattr(sqlite3, "connect", fail)
    with pytest.raises(CorpusStoreError) as error:
        with PublicCorpusStore(tmp_path).session(scope()):
            pass
    assert str(error.value) == "corpus_storage_unavailable"
    monkeypatch.setattr(sqlite3, "connect", real_connect)
    with PublicCorpusStore(tmp_path, lock_timeout=0).session(scope()):
        pass


def test_linked_database_denied(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"not a database")
    alias = tmp_path / "public_knowledge.sqlite3"
    os.link(target, alias)
    with pytest.raises(CorpusStoreError, match="path_invalid"):
        with PublicCorpusStore(tmp_path).session(scope()):
            pass
    assert target.read_bytes() == b"not a database"


def _writer(directory, ready, go, results, number):
    try:
        ready.put(number)
        assert go.wait(15)
        with PublicCorpusStore(Path(directory), lock_timeout=10).session(scope()) as session:
            snap = session.snapshot()
            after = snap["corpus"]
            after["audit_events"].append({"sequence": number})
            op = session.begin(key=f"writer-{number}", epoch=snap["restore_epoch"],
                               kind="sync", intent={"sequence": number},
                               expected_revision=snap["revision"], after=after)
            session.commit(op.operation_id)
        results.put("ok")
    except Exception as exc:
        results.put(type(exc).__name__ + ":" + str(exc))


def test_separate_process_writers_do_not_lose_updates(tmp_path):
    ctx = mp.get_context("spawn")
    ready, results, go = ctx.Queue(), ctx.Queue(), ctx.Event()
    children = [ctx.Process(target=_writer, args=(str(tmp_path), ready, go, results, n))
                for n in range(4)]
    try:
        for child in children:
            child.start()
        for _ in children:
            ready.get(timeout=20)
        go.set()
        assert [results.get(timeout=20) for _ in children] == ["ok"] * 4
        for child in children:
            child.join(20)
            assert child.exitcode == 0
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(5)
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        snap = session.snapshot()
        assert snap["revision"] == 4
        assert sorted(e["sequence"] for e in snap["corpus"]["audit_events"]) == list(range(4))


def _crash_writer(directory, ready):
    with PublicCorpusStore(Path(directory)).session(scope()) as session:
        op = session.begin(**request(session))
        session.record_step(op.operation_id, action="upsert", record_ids=["one"])
        ready.set()
        # Parent terminates us without running Python finally blocks.
        import time
        time.sleep(60)


def test_process_death_releases_lock_but_preserves_intent(tmp_path):
    ctx = mp.get_context("spawn")
    ready = ctx.Event()
    child = ctx.Process(target=_crash_writer, args=(str(tmp_path), ready))
    child.start()
    try:
        assert ready.wait(20)
        with pytest.raises(CorpusStoreError, match="corpus_busy"):
            with PublicCorpusStore(tmp_path, lock_timeout=0).session(scope()):
                pass
    finally:
        child.terminate()
        child.join(10)
    assert child.exitcode is not None
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        assert session.snapshot()["revision"] == 0
        assert session.snapshot()["recovery_required"]
        assert session.pending()[0]["steps"][0]["record_ids"] == ["one"]


def test_commit_failure_rolls_back_corpus_and_operation(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        operation = session.begin(**request(session))
        session._db.execute("""
            CREATE TEMP TRIGGER fail_operation_commit
            BEFORE UPDATE OF state ON operations
            WHEN NEW.state='committed'
            BEGIN SELECT RAISE(ABORT, 'SENSITIVE_TRANSACTION_MARKER'); END
        """)
        with pytest.raises(CorpusStoreError) as error:
            session.commit(operation.operation_id)
        assert str(error.value) == "corpus_storage_unavailable"
        assert session.snapshot()["revision"] == 0
        assert session.snapshot()["corpus"]["audit_events"] == []
        assert session.pending()[0]["state"] == "prepared"
        session._db.execute("DROP TRIGGER fail_operation_commit")
        assert session.commit(operation.operation_id).state == "committed"
        assert session.snapshot()["revision"] == 1


def test_invalid_request_type_has_no_effect(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        with pytest.raises(CorpusStoreError, match="request_invalid"):
            session.begin(**{**request(session), "kind": []})
        assert session.pending() == []


@pytest.mark.parametrize("failure", [OSError("caller effect"), sqlite3.OperationalError("caller database")])
def test_caller_failure_classification_preserved_and_lock_released(tmp_path, failure):
    store = PublicCorpusStore(tmp_path, lock_timeout=0)
    with pytest.raises(type(failure)) as error:
        with store.session(scope()):
            raise failure
    assert error.value is failure
    with store.session(scope()) as session:
        assert session.snapshot()["revision"] == 0


def test_excessively_nested_persisted_json_uses_stable_error(tmp_path):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        session._db.execute("UPDATE corpus_state SET payload=? WHERE id=1",
                            ("[" * 2000 + "0" + "]" * 2000,))
        with pytest.raises(CorpusStoreError) as error:
            session.snapshot()
        assert str(error.value) == "corpus_storage_invalid"


def test_decoder_recursion_failure_uses_stable_error(tmp_path, monkeypatch):
    import backend.public_corpus_store as storage
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        def fail_decode(value):
            raise RecursionError("SENSITIVE_DECODER_MARKER")
        monkeypatch.setattr(storage.json, "loads", fail_decode)
        with pytest.raises(CorpusStoreError) as error:
            session.snapshot()
        assert str(error.value) == "corpus_storage_invalid"


@pytest.mark.parametrize("payload", ['{}', '{"schema_version":2,"source_of_truth":true,"sources":{},"audit_events":[]}'])
def test_invalid_stored_corpus_schema_uses_storage_error(tmp_path, payload):
    with PublicCorpusStore(tmp_path).session(scope()) as session:
        session._db.execute("UPDATE corpus_state SET payload=? WHERE id=1", (payload,))
        with pytest.raises(CorpusStoreError, match="corpus_storage_invalid"):
            session.snapshot()


def test_empty_version_one_database_denied_before_yield(tmp_path):
    with sqlite3.connect(tmp_path / "public_knowledge.sqlite3") as db:
        db.execute("PRAGMA user_version=1")
    with pytest.raises(CorpusStoreError, match="schema_unsupported"):
        with PublicCorpusStore(tmp_path).session(scope()):
            pytest.fail("invalid schema was exposed")


@pytest.mark.parametrize("mutation,code", [
    ("DROP INDEX one_unfinished", "schema_unsupported"),
    ("ALTER TABLE operations ADD COLUMN unexpected TEXT", "schema_unsupported"),
    ("DELETE FROM corpus_state", "storage_invalid"),
    ("UPDATE corpus_state SET restore_epoch=''", "storage_invalid"),
])
def test_mutated_version_one_database_denied_before_yield(tmp_path, mutation, code):
    with PublicCorpusStore(tmp_path).session(scope()):
        pass
    with sqlite3.connect(tmp_path / "public_knowledge.sqlite3") as db:
        db.execute(mutation)
    with pytest.raises(CorpusStoreError, match=code):
        with PublicCorpusStore(tmp_path).session(scope()):
            pytest.fail("invalid database was exposed")
