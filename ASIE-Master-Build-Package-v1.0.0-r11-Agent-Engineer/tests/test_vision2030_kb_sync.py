from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.vision2030_kb_sync import (
    Vision2030KnowledgeSync,
    Vision2030SyncError,
    _chunk_text,
    load_registry,
)


class FakeTavily:
    def __init__(self, content_by_url: dict[str, str]) -> None:
        self.content_by_url = content_by_url
        self.calls: list[dict[str, Any]] = []

    def extract(self, *, urls: list[str], query: str | None = None, depth: str = "basic") -> dict[str, Any]:
        self.calls.append({"urls": urls, "query": query, "depth": depth})
        url = urls[0]
        return {
            "payload": {
                "results": [
                    {
                        "url": url,
                        "raw_content": self.content_by_url[url],
                    }
                ]
            }
        }


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"payload": {}, "status_code": 200}


class FakePinecone:
    index_name = "vision2030-kb"
    namespace_prefix = "asie"

    def __init__(self) -> None:
        self.transport = FakeTransport()
        self.upserts: list[list[dict[str, Any]]] = []

    def upsert_approved_text(self, *, organization_id: str, project_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        self.upserts.append(records)
        return {"record_count": len(records)}

    def _host(self) -> str:
        return "vision2030-kb.example.svc.pinecone.io"

    def _headers(self) -> dict[str, str]:
        return {"Api-Key": "redacted", "X-Pinecone-Api-Version": "2026-04"}


def registry(url: str = "https://www.vision2030.gov.sa/ar/") -> dict[str, Any]:
    return {
        "registry_id": "test-registry",
        "sources": [
            {
                "source_id": "vision2030-ar-home",
                "title": "الرؤية",
                "url": url,
                "language": "ar",
                "authority": "Saudi Vision 2030",
                "enabled": True,
                "extract_depth": "advanced",
            }
        ],
    }


class Vision2030SyncTests(unittest.TestCase):
    def test_registry_rejects_non_official_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            payload = registry("https://example.com/vision2030")
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(Vision2030SyncError, "official_https"):
                load_registry(path)

    def test_chunking_is_bounded_and_overlapping(self) -> None:
        text = ("رؤية 2030 والتحول الوطني والاقتصاد المزدهر. " * 400).strip()
        chunks = _chunk_text(text, maximum=1_200, overlap=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(1 <= len(chunk) <= 1_200 for chunk in chunks))

    def test_first_run_upserts_and_second_unchanged_run_is_noop(self) -> None:
        content = ("المحتوى الرسمي لرؤية السعودية 2030. " * 40).strip()
        tavily = FakeTavily({"https://www.vision2030.gov.sa/ar/": content})
        pinecone = FakePinecone()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            sync = Vision2030KnowledgeSync(tavily=tavily, pinecone=pinecone, state_path=state)
            first = sync.run(registry())
            second = sync.run(registry())

        self.assertEqual(first["status"], "changed")
        self.assertEqual(first["sources_changed"], 1)
        self.assertGreater(first["records_upserted"], 0)
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(second["sources_unchanged"], 1)
        self.assertEqual(len(pinecone.upserts), 1)

    def test_changed_content_replaces_records_and_deletes_stale_tail(self) -> None:
        url = "https://www.vision2030.gov.sa/ar/"
        long_content = ("قسم طويل من وثيقة الرؤية والتحول الوطني. " * 500).strip()
        short_content = ("نسخة محدثة مختصرة من وثيقة الرؤية. " * 40).strip()
        tavily = FakeTavily({url: long_content})
        pinecone = FakePinecone()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            sync = Vision2030KnowledgeSync(tavily=tavily, pinecone=pinecone, state_path=state)
            first = sync.run(registry())
            tavily.content_by_url[url] = short_content
            second = sync.run(registry())

        self.assertEqual(first["status"], "changed")
        self.assertEqual(second["status"], "changed")
        self.assertGreater(second["records_deleted"], 0)
        self.assertEqual(len(pinecone.transport.calls), 1)
        delete_call = pinecone.transport.calls[0]
        self.assertTrue(delete_call["url"].endswith("/vectors/delete"))
        self.assertNotIn("Api-Key", json.dumps(delete_call["body"]))

    def test_dry_run_detects_change_without_writing_pinecone(self) -> None:
        content = ("بيانات رسمية جديدة لرؤية السعودية 2030. " * 30).strip()
        tavily = FakeTavily({"https://www.vision2030.gov.sa/ar/": content})
        pinecone = FakePinecone()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            result = Vision2030KnowledgeSync(tavily=tavily, pinecone=pinecone, state_path=state).run(
                registry(), dry_run=True
            )
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["records_upserted"], 0)
        self.assertEqual(pinecone.upserts, [])

    def test_sync_never_claims_snapshot_finance_or_source_truth(self) -> None:
        content = ("المصدر الرسمي للرؤية. " * 30).strip()
        tavily = FakeTavily({"https://www.vision2030.gov.sa/ar/": content})
        pinecone = FakePinecone()
        with tempfile.TemporaryDirectory() as directory:
            result = Vision2030KnowledgeSync(
                tavily=tavily,
                pinecone=pinecone,
                state_path=Path(directory) / "state.json",
            ).run(registry(), dry_run=True)
        self.assertFalse(result["source_of_truth"])
        self.assertFalse(result["snapshot_mutated"])
        self.assertFalse(result["finance_mutated"])


if __name__ == "__main__":
    unittest.main()
