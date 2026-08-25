from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

from backend.public_knowledge import load_public_source_registry


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent


class GitHubActionsSafeLoader(yaml.SafeLoader):
    pass


GitHubActionsSafeLoader.yaml_implicit_resolvers = {
    key: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
GitHubActionsSafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|false)$", re.IGNORECASE),
    list("tTfF"),
)


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


GitHubActionsSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_github_actions_workflow(text: str) -> dict[str, object]:
    payload = yaml.load(text, Loader=GitHubActionsSafeLoader)
    if not isinstance(payload, dict):
        raise AssertionError("workflow must be a mapping")
    return payload


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
        self.assertNotIn("public_namespace", public_registry)
        expected_enabled_scope = {
            "saudi-open-data-portal": (
                "saudi_official",
                "https://open.data.gov.sa/en/datasets",
                ("/en/datasets",),
            ),
            "vision2030-open-data": (
                "saudi_official",
                "https://www.vision2030.gov.sa/en/open-data",
                ("/en/open-data",),
            ),
            "mof-open-data": (
                "saudi_official",
                "https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
                ("/en/generalservcies/open-data",),
            ),
            "sama-open-data": (
                "saudi_official",
                "https://sama.gov.sa/en-US/Publications/EconomicReports/Pages/database.aspx",
                ("/en-US/Publications/EconomicReports",),
            ),
            "sdb-open-data": (
                "saudi_official",
                "https://www.sdb.gov.sa/en/open-data/open-data-library",
                ("/en/open-data",),
            ),
            "world-bank-indicators-api": (
                "international_official",
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation",
                ("/knowledgebase/articles",),
            ),
            "imf-data-api": (
                "international_official",
                "https://data.imf.org/en/Resource-Pages/IMF-API",
                ("/en/Resource-Pages",),
            ),
        }
        actual_enabled_scope = {
            row["source_id"]: (
                row["authority"],
                row["url"],
                tuple(row["allowed_paths"]),
            )
            for row in public_registry["sources"]
            if row["state"] == "enabled"
        }
        self.assertEqual(actual_enabled_scope, expected_enabled_scope)
        self.assertTrue(
            any(
                row["authority"] == "private_analytical_reference"
                and row["state"] == "reference_only"
                for row in public_registry["sources"]
            )
        )

    def test_workflow_is_manual_authorized_and_secret_scoped(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "vision2030-kb-sync.yml").read_text(encoding="utf-8")
        parsed = _load_github_actions_workflow(workflow)
        triggers = parsed["on"]
        self.assertIsInstance(triggers, dict)
        self.assertEqual(set(triggers), {"workflow_dispatch"})
        inputs = triggers["workflow_dispatch"]["inputs"]
        self.assertEqual(set(inputs), {"dry_run", "authorization_commit", "source_id"})
        self.assertIs(inputs["dry_run"]["required"], True)
        self.assertIs(inputs["dry_run"]["default"], True)
        self.assertEqual(inputs["dry_run"]["type"], "boolean")
        self.assertIs(inputs["authorization_commit"]["required"], True)
        self.assertEqual(inputs["authorization_commit"]["type"], "string")
        self.assertIs(inputs["source_id"]["required"], True)
        self.assertEqual(inputs["source_id"]["default"], "vision2030-open-data")
        self.assertEqual(inputs["source_id"]["type"], "string")

        environment = parsed["env"]
        self.assertEqual(set(environment), {"PACKAGE_ROOT", "PYTHONPATH"})

        jobs = parsed["jobs"]
        authorize_environment = jobs["authorize"]["env"]
        self.assertEqual(set(authorize_environment), {"ASIE_AUTHORIZATION_COMMIT"})
        self.assertNotIn("ASIE_ALLOW_EXTERNAL_FETCH", authorize_environment)

        sync_environment = jobs["sync"]["env"]
        self.assertEqual(sync_environment["ASIE_ALLOW_EXTERNAL_FETCH"], "true")
        self.assertEqual(sync_environment["ASIE_PROVIDER_GLOBAL_KILL_SWITCH"], "false")
        self.assertEqual(sync_environment["ASIE_PROVIDER_TAVILY_STATE"], "enabled")
        self.assertEqual(sync_environment["ASIE_PROVIDER_TAVILY_KILL_SWITCH"], "false")
        self.assertNotIn("ASIE_PROVIDER_PINECONE_STATE", sync_environment)
        self.assertNotIn("ASIE_PROVIDER_PINECONE_KILL_SWITCH", sync_environment)
        authorize_steps = jobs["authorize"]["steps"]
        sync_steps = jobs["sync"]["steps"]
        authorize_checkout = next(
            step for step in authorize_steps if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        sync_checkout = next(
            step for step in sync_steps if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        self.assertIs(authorize_checkout["with"]["persist-credentials"], False)
        self.assertIs(sync_checkout["with"]["persist-credentials"], False)

        action_uses = [
            step["uses"]
            for job in jobs.values()
            for step in job["steps"]
            if "uses" in step
        ]
        self.assertEqual(len(action_uses), 4)
        for action in action_uses:
            self.assertRegex(action, r"^[^@\s]+@[0-9a-f]{40}$")

        self.assertIn("git rev-parse origin/main", workflow)
        self.assertIn("external_network_authorized", workflow)
        self.assertIn("provider_activation_authorized", workflow)
        self.assertIn("needs: authorize", workflow)
        self.assertIn("environment: production", workflow)
        self.assertIn("secrets.TAVILY_API_KEY", workflow)
        self.assertNotIn("secrets.PINECONE_API_KEY", workflow)
        self.assertNotIn("PINECONE_INDEX", workflow)
        self.assertNotIn("api.pinecone.io", workflow)
        self.assertIn("python -m pip install -r requirements-dev.txt", workflow)
        self.assertIn('REQUESTED_DRY_RUN: ${{ inputs.dry_run }}', workflow)
        self.assertIn('test "$REQUESTED_DRY_RUN" = "true"', workflow)
        self.assertIn('SOURCE_ID: ${{ inputs.source_id }}', workflow)
        self.assertIn('args=(--dry-run --source-id "$SOURCE_ID")', workflow)
        self.assertIn("python -m backend.public_knowledge", workflow)
        self.assertNotIn("actions/cache/", workflow)
        self.assertNotIn("always() && !inputs.dry_run", workflow)
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
