from __future__ import annotations

import importlib
import sys
import unittest
import warnings
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SITECUSTOMIZE_PATH = PACKAGE_ROOT / "sitecustomize.py"
ASIE_LOCAL_API_PATH = PACKAGE_ROOT / "backend" / "asie_local_api.py"
FREEZE_MANIFEST_PATH = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"


class Python312DeprecatedCompatTests(unittest.TestCase):
    def test_sitecustomize_declares_python312_deprecated_compatibility_shim(self) -> None:
        source = SITECUSTOMIZE_PATH.read_text(encoding="utf-8")
        self.assertIn("ASIE-PY312-DEPRECATED-COMPAT-v1", source)
        self.assertIn('if not hasattr(warnings, "deprecated")', source)
        self.assertIn("warnings.deprecated = _compat_deprecated", source)
        self.assertIn("__deprecated__", source)

    def test_python_runtime_has_deprecated_after_sitecustomize_import(self) -> None:
        import sitecustomize  # noqa: F401

        self.assertTrue(hasattr(warnings, "deprecated"))

        @warnings.deprecated("legacy test wrapper")  # type: ignore[attr-defined]
        def legacy_value() -> int:
            return 7

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", DeprecationWarning)
            self.assertEqual(legacy_value(), 7)
        self.assertTrue(any(issubclass(row.category, DeprecationWarning) for row in captured))
        self.assertEqual(getattr(legacy_value, "__deprecated__", None), "legacy test wrapper")

    def test_asie_local_api_keeps_legacy_import_but_can_import_under_compat_layer(self) -> None:
        source = ASIE_LOCAL_API_PATH.read_text(encoding="utf-8")
        self.assertIn("from warnings import deprecated", source)
        import sitecustomize  # noqa: F401

        module = importlib.import_module("backend.asie_local_api")
        self.assertTrue(hasattr(module, "BUILD_OVERVIEW_DEPRECATION_MESSAGE"))
        self.assertIn("backend.asie_local_api", sys.modules)

    def test_compatibility_hotfix_does_not_mutate_aas_frozen_runtime_files(self) -> None:
        freeze_manifest = FREEZE_MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertNotIn('"path": "sitecustomize.py"', freeze_manifest)
        self.assertNotIn('"path": "backend/asie_local_api.py"', freeze_manifest)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
