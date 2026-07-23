"""W0.4 acceptance: PDF export honors a pinned, environment-configured renderer.

The production image pins the renderer binary and exports through
``ASIE_PDF_RENDERER``; the client browser is never involved. These tests use a
fake renderer script so the contract is verified without a real browser.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.report_exports import export_funder_report_pdf

FAKE_RENDERER = """#!/bin/sh
out=""
for arg in "$@"; do
  case "$arg" in
    --print-to-pdf=*) out="${arg#--print-to-pdf=}" ;;
  esac
done
if [ -n "$out" ]; then
  printf '%s' '%PDF-1.4 asie-pinned-renderer' > "$out"
fi
"""

PROJECTION = {
    "snapshot_id": "snap-w04",
    "run_id": "run-w04",
    "contract_id": "funder.report.v1",
    "profile_id": "reference_profile",
    "readiness_status": "reference_only",
    "sections": [],
    "gaps": [],
    "evidence": {},
    "input_traceability": {"unreviewed_count": 0},
}


class PdfRendererConfigurationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "fake renderer script requires a POSIX shell")
    def test_pdf_export_uses_renderer_pinned_via_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            renderer = Path(directory) / "pinned-renderer.sh"
            renderer.write_text(FAKE_RENDERER, encoding="utf-8")
            renderer.chmod(0o755)
            output = Path(directory) / "funder-report.pdf"
            previous = os.environ.get("ASIE_PDF_RENDERER")
            os.environ["ASIE_PDF_RENDERER"] = str(renderer)
            try:
                result = export_funder_report_pdf(dict(PROJECTION), output)
            finally:
                if previous is None:
                    os.environ.pop("ASIE_PDF_RENDERER", None)
                else:
                    os.environ["ASIE_PDF_RENDERER"] = previous
            self.assertTrue(result.exists())
            self.assertGreater(result.stat().st_size, 0)
            self.assertTrue(result.read_bytes().startswith(b"%PDF"))

    @unittest.skipUnless(os.name == "posix", "fake renderer script requires a POSIX shell")
    def test_pdf_export_fails_closed_when_renderer_produces_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            renderer = Path(directory) / "silent-renderer.sh"
            renderer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            renderer.chmod(0o755)
            output = Path(directory) / "should-not-exist.pdf"
            previous = os.environ.get("ASIE_PDF_RENDERER")
            os.environ["ASIE_PDF_RENDERER"] = str(renderer)
            try:
                with self.assertRaises(RuntimeError):
                    export_funder_report_pdf(dict(PROJECTION), output)
            finally:
                if previous is None:
                    os.environ.pop("ASIE_PDF_RENDERER", None)
                else:
                    os.environ["ASIE_PDF_RENDERER"] = previous
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
