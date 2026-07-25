from __future__ import annotations

import unittest
from pathlib import Path

from backend.aas_registry import bootstrap_default_registry
from backend.dib_registry_admission import (
    DIB_CONTRACT_SPECS,
    DIB_MODULE_SPECS,
    DIB_REGISTRY_ADMISSION_ID,
    DIB_SOCKET_SPECS,
    assert_all_frozen_files_unchanged,
    assert_dib_runtime_alignment,
    assert_frozen_registry_file_unchanged,
    build_effective_dib_registry,
    dib_contract_ids,
    dib_module_ids,
    dib_socket_ids,
    effective_dib_registry_snapshot,
)
from backend.dib_runtime import DIB_CONTRACTS, DIB_MODULES, DIB_SOCKETS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DIBRegistryAdmissionTests(unittest.TestCase):
    def test_dib_admission_matches_runtime_identifiers_exactly(self) -> None:
        self.assertEqual(dib_contract_ids(), set(DIB_CONTRACTS))
        self.assertEqual(dib_socket_ids(), set(DIB_SOCKETS))
        self.assertEqual(dib_module_ids(), set(DIB_MODULES))
        self.assertEqual(len(DIB_CONTRACT_SPECS), 11)
        self.assertEqual(len(DIB_SOCKET_SPECS), 10)
        self.assertEqual(len(DIB_MODULE_SPECS), 9)
        assert_dib_runtime_alignment()

    def test_default_frozen_registry_does_not_contain_dib_admission(self) -> None:
        frozen = bootstrap_default_registry().snapshot()
        frozen_contracts = {item["contract_id"] for item in frozen["contracts"]}
        frozen_sockets = {item["socket_id"] for item in frozen["sockets"]}
        frozen_modules = {item["module_id"] for item in frozen["modules"]}
        self.assertFalse(frozen_contracts & set(DIB_CONTRACTS))
        self.assertFalse(frozen_sockets & set(DIB_SOCKETS))
        self.assertFalse(frozen_modules & set(DIB_MODULES))

    def test_effective_registry_admits_dib_as_post_freeze_overlay(self) -> None:
        base_counts = bootstrap_default_registry().counts()
        registry = build_effective_dib_registry()
        effective = registry.snapshot()
        effective_contracts = {item["contract_id"] for item in effective["contracts"]}
        effective_sockets = {item["socket_id"] for item in effective["sockets"]}
        effective_modules = {item["module_id"] for item in effective["modules"]}

        self.assertTrue(set(DIB_CONTRACTS).issubset(effective_contracts))
        self.assertTrue(set(DIB_SOCKETS).issubset(effective_sockets))
        self.assertTrue(set(DIB_MODULES).issubset(effective_modules))
        self.assertEqual(registry.counts()["contracts"], base_counts["contracts"] + len(DIB_CONTRACTS))
        self.assertEqual(registry.counts()["sockets"], base_counts["sockets"] + len(DIB_SOCKETS))
        self.assertEqual(registry.counts()["modules"], base_counts["modules"] + len(DIB_MODULES))

    def test_dib_admission_has_no_ai_provider_or_network_fetch(self) -> None:
        snapshot = effective_dib_registry_snapshot()
        self.assertEqual(snapshot["admission"]["admission_id"], DIB_REGISTRY_ADMISSION_ID)
        self.assertFalse(snapshot["admission"]["frozen_registry_mutated"])
        self.assertFalse(snapshot["admission"]["ai_provider_enabled"])
        self.assertFalse(snapshot["admission"]["external_fetch_enabled"])
        dib_modules = [item for item in snapshot["modules"] if item["module_id"] in DIB_MODULES]
        self.assertTrue(dib_modules)
        self.assertTrue(all(item["external_fetch_enabled"] is False for item in dib_modules))
        self.assertTrue(all("backend/dib_runtime.py" == item["owner_file"] for item in dib_modules))

    def test_dib_sockets_reference_only_admitted_contracts_or_existing_contracts(self) -> None:
        snapshot = effective_dib_registry_snapshot()
        contract_ids = {item["contract_id"] for item in snapshot["contracts"]}
        socket_ids = {item["socket_id"] for item in snapshot["sockets"]}
        for socket in DIB_SOCKET_SPECS:
            self.assertIn(socket.contract_id, contract_ids)
            self.assertIn(socket.socket_id, socket_ids)

    def test_frozen_registry_and_runtime_files_are_unchanged(self) -> None:
        assert_frozen_registry_file_unchanged(PACKAGE_ROOT)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
