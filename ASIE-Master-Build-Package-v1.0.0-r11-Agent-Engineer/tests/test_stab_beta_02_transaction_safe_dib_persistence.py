from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from backend.dib_api import DIBApiController, DIBApiError
from backend.dib_persistence import DIBPersistenceError, create_dib_persistence_store
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

FROZEN_FILES = {
    "backend/aas_kernel.py",
    "backend/aas_registry.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
}

STAB_BETA_02_ALLOWLIST = {
    "backend/dib_persistence.py",
    "backend/dib_session_continuity.py",
    "tests/test_stab_beta_02_transaction_safe_dib_persistence.py",
    "docs/STAB-BETA-02-TRANSACTION-SAFE-DIB-PERSISTENCE-2026-07-29.md",
}


class TransactionSafeDIBPersistenceTests(unittest.TestCase):
    def test_shared_store_survives_real_threading_http_server_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = create_dib_persistence_store(Path(temp_dir) / "threaded-http.sqlite3")
            controller = DIBApiController(store)

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, _format: str, *args: object) -> None:
                    return

                def do_POST(self) -> None:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    try:
                        response = controller.dispatch("POST", self.path, payload)
                        status = response.status
                        body = response.to_public()
                    except DIBApiError as exc:
                        status = exc.status
                        body = {"status": status, "error": exc.code}
                    raw = json.dumps(body, sort_keys=True).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            def start_session(index: int) -> tuple[int, dict[str, object]]:
                connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=20)
                try:
                    payload = json.dumps(
                        {"project_profile": {"project_id": f"threaded_project_{index}", "sector": "test"}}
                    )
                    connection.request(
                        "POST",
                        "/api/dib/sessions",
                        body=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    response = connection.getresponse()
                    body = json.loads(response.read().decode("utf-8"))
                    return response.status, body
                finally:
                    connection.close()

            try:
                with ThreadPoolExecutor(max_workers=16) as executor:
                    results = list(executor.map(start_session, range(40)))

                self.assertEqual([201] * 40, [status for status, _body in results])
                session_ids = [str(body["session"]["session_id"]) for _status, body in results]
                self.assertEqual(40, len(set(session_ids)))
                for session_id in session_ids:
                    self.assertEqual("active", store.load_session(session_id)["status"])
                    self.assertEqual(1, len(store.list_events(session_id)))
            finally:
                server.shutdown()
                server.server_close()
                controller.close()

    def test_concurrent_reads_and_audit_writes_share_no_sqlite_connection(self) -> None:
        store = create_dib_persistence_store()
        try:
            session = store.start_session({"project_id": "concurrent_audit_project"})
            session_id = session["session_id"]

            def append(index: int) -> str:
                event = store._append_event(
                    session_id,
                    event_type="concurrency.audit",
                    entity_type="test",
                    entity_id=f"audit_{index}",
                    payload={"index": index},
                )
                return event.event_id

            def read(_index: int) -> str:
                return str(store.load_session(session_id)["session_id"])

            with ThreadPoolExecutor(max_workers=20) as executor:
                event_ids = list(executor.map(append, range(30)))
                loaded_ids = list(executor.map(read, range(60)))

            self.assertEqual(30, len(set(event_ids)))
            self.assertEqual([session_id] * 60, loaded_ids)
            self.assertEqual(31, len(store.list_events(session_id)))
            self.assertFalse(hasattr(store, "connection"))
        finally:
            store.close()

    def test_write_transaction_rolls_back_session_when_event_insert_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "rollback.sqlite3"
            store = create_dib_persistence_store(db_path)
            try:
                with mock.patch.object(store, "_append_event_row", side_effect=RuntimeError("forced_event_failure")):
                    with self.assertRaisesRegex(RuntimeError, "forced_event_failure"):
                        store.start_session({"project_id": "rollback_project"})

                self.assertEqual([], store.list_session_ids_for_project("rollback_project"))
            finally:
                store.close()

            reopened = create_dib_persistence_store(db_path)
            try:
                self.assertEqual([], reopened.list_session_ids_for_project("rollback_project"))
            finally:
                reopened.close()

    def test_schema_registry_pragmas_and_reopen_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "schema.sqlite3"
            first = create_dib_persistence_store(db_path)
            first_status = first.status()
            first.start_session({"project_id": "schema_project"})
            first.close()

            second = create_dib_persistence_store(db_path)
            try:
                second_status = second.status()
                self.assertEqual(1, first_status["schema_version"])
                self.assertEqual(1, second_status["schema_version"])
                self.assertEqual("wal", second_status["journal_mode"])
                self.assertTrue(second_status["foreign_keys_enabled"])
                self.assertEqual(30_000, second_status["busy_timeout_ms"])
                self.assertEqual("per_operation_or_transaction", second_status["connection_scope"])
                self.assertEqual(1, len(second.list_session_ids_for_project("schema_project")))
            finally:
                second.close()

    def test_closed_store_fails_closed(self) -> None:
        store = create_dib_persistence_store()
        store.close()
        store.close()
        with self.assertRaisesRegex(DIBPersistenceError, "store is closed"):
            store.status()

    def test_package_allowlist_excludes_frozen_runtime(self) -> None:
        self.assertTrue(STAB_BETA_02_ALLOWLIST.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
