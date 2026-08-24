from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.public_knowledge import load_public_source_registry


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent


def _parse_simple_yaml_mapping(text: str) -> dict[str, object]:
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indentation = len(raw_line) - len(raw_line.lstrip(" "))
        key, separator, raw_value = raw_line.strip().partition(":")
        if not separator or not key:
            raise AssertionError(f"unsupported workflow mapping line: {raw_line}")
        while stack[-1][0] >= indentation:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise AssertionError(f"duplicate workflow mapping key: {key}")
        value = raw_value.strip()
        if not value:
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indentation, child))
        elif value in {"true", "false"}:
            parent[key] = value == "true"
        elif value.startswith('"'):
            parent[key] = json.loads(value)
        else:
            parent[key] = value
    return root


class Vision2030SyncPackageGuardrails(unittest.TestCase):
    def test_registry_contains_only_official_https_sources(self) -> None:
        registry = json.loads((PACKAGE_ROOT / "config" / "vision2030_sources.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["refresh_policy"], "monthly_change_detection")
        self.assertGreaterEqual(len(registry["sources"]), 4)
        for source in registry["sources"]:
            self.assertTrue(source["url"].startswith("https://www.vision2030.gov.sa/"))
            self.assertEqual(source["authority"], "Saudi Vision 2030")

        public_registry = load_public_source_registry(
            PACKAGE_ROOT / "config" / "public_knowledge_sources.json"
        )
        self.assertEqual(public_registry["policy"], "official_open_auto_with_anomaly_quarantine")
        self.assertTrue(any(row["source_id"] == "world-bank-indicators-api" for row in public_registry["sources"]))
        self.assertTrue(any(row["source_id"] == "imf-data-api" for row in public_registry["sources"]))
        self.assertTrue(
            any(
                row["authority"] == "private_analytical_reference"
                and row["state"] == "reference_only"
                for row in public_registry["sources"]
            )
        )

    def test_workflow_is_manual_authorized_and_secret_scoped(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "vision2030-kb-sync.yml").read_text(encoding="utf-8")
        header = _parse_simple_yaml_mapping(workflow.split("\npermissions:", 1)[0])
        triggers = header["on"]
        self.assertIsInstance(triggers, dict)
        self.assertEqual(set(triggers), {"workflow_dispatch"})
        inputs = triggers["workflow_dispatch"]["inputs"]
        self.assertEqual(set(inputs), {"dry_run", "authorization_commit", "source_id"})
        self.assertEqual(inputs["dry_run"]["required"], True)
        self.assertEqual(inputs["dry_run"]["default"], True)
        self.assertEqual(inputs["dry_run"]["type"], "boolean")
        self.assertEqual(inputs["authorization_commit"]["required"], True)
        self.assertEqual(inputs["authorization_commit"]["type"], "string")
        self.assertEqual(inputs["source_id"]["required"], True)
        self.assertEqual(inputs["source_id"]["default"], "vision2030-open-data")
        self.assertEqual(inputs["source_id"]["type"], "string")

        env_block = "env:\n" + workflow.split("\nenv:\n", 1)[1].split("\njobs:\n", 1)[0]
        environment = _parse_simple_yaml_mapping(env_block)["env"]
        self.assertEqual(environment["ASIE_ALLOW_EXTERNAL_FETCH"], "true")
        self.assertEqual(environment["ASIE_PROVIDER_GLOBAL_KILL_SWITCH"], "false")
        self.assertEqual(environment["ASIE_PROVIDER_TAVILY_STATE"], "enabled")
        self.assertEqual(environment["ASIE_PROVIDER_PINECONE_STATE"], "enabled")
        self.assertEqual(environment["ASIE_PROVIDER_TAVILY_KILL_SWITCH"], "false")
        self.assertEqual(environment["ASIE_PROVIDER_PINECONE_KILL_SWITCH"], "false")

        self.assertIn("git rev-parse origin/main", workflow)
        self.assertIn("external_network_authorized", workflow)
        self.assertIn("provider_activation_authorized", workflow)
        self.assertIn("needs: authorize", workflow)
        self.assertIn("environment: production", workflow)
        self.assertIn("secrets.TAVILY_API_KEY", workflow)
        self.assertIn("secrets.PINECONE_API_KEY", workflow)
        self.assertIn('PINECONE_INDEX: "vision2030-kb"', workflow)
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", workflow)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", workflow)
        self.assertIn("actions/cache/restore@0057852bfaa89a56745cba8c7296529d2fc39830", workflow)
        self.assertIn("actions/cache/save@0057852bfaa89a56745cba8c7296529d2fc39830", workflow)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", workflow)
        self.assertIn("python -m pip install -r requirements-dev.txt", workflow)
        self.assertIn("--dry-run", workflow)
        self.assertIn('SOURCE_ID: ${{ inputs.source_id }}', workflow)
        self.assertIn('args+=(--source-id "$SOURCE_ID")', workflow)
        self.assertNotIn('args+=(--source-id "${{ inputs.source_id }}")', workflow)
        self.assertIn("always() && !inputs.dry_run", workflow)
        self.assertIn("python -m backend.public_knowledge", workflow)
        self.assertIn("ASIE_PROVIDER_TAVILY_STATE: enabled", workflow)
        self.assertIn("ASIE_PROVIDER_PINECONE_STATE: enabled", workflow)
        self.assertNotIn("DEEPSEEK_API_KEY", workflow)
        self.assertNotIn("GOOGLE_MAPS_API_KEY", workflow)

    def test_sync_does_not_import_frozen_runtime_or_finance(self) -> None:
        source = (PACKAGE_ROOT / "backend" / "public_knowledge.py").read_text(encoding="utf-8")
        forbidden = (
            "backend.aas_kernel",
            "backend.heart_controller",
            "backend.system_bus",
            "ProjectRunWorkflow",
            "SnapshotAssembly",
            "FinanceEngine",
            "DecisionCouncil",
        )
        for token in forbidden:
            self.assertNotIn(token, source)
        self.assertIn('"source_of_truth": False', source)
        self.assertIn('"snapshot_mutated": False', source)
        self.assertIn('"finance_mutated": False', source)

    def test_no_provider_secret_is_committed(self) -> None:
        source = (PACKAGE_ROOT / "backend" / "public_knowledge.py").read_text(encoding="utf-8")
        registry = (PACKAGE_ROOT / "config" / "public_knowledge_sources.json").read_text(encoding="utf-8")
        self.assertNotIn("pcsk_", source + registry)
        self.assertNotIn("tvly-", source + registry)
        self.assertNotIn("Bearer ", source + registry)


if __name__ == "__main__":
    unittest.main()
