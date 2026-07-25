from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.dib_http_mounting import DIB_LOCAL_GATEWAY_INTEGRATION_ID, create_dib_http_mount
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FREEZE_MANIFEST = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"
COMPOSE_FILE = PACKAGE_ROOT / "docker-compose.yml"
NGINX_CONF = PACKAGE_ROOT / "docker" / "nginx.conf"
DOCKERFILE_BACKEND = PACKAGE_ROOT / "Dockerfile.backend"
DIB_HTTP_MOUNTING = PACKAGE_ROOT / "backend" / "dib_http_mounting.py"


class DIBLocalGatewayIntegrationTests(unittest.TestCase):
    def test_gateway_integration_does_not_touch_aas_freeze_runtime_files(self) -> None:
        manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
        frozen_paths = {entry["path"] for entry in manifest["frozen_files"]}
        self.assertNotIn("backend/asie_local_api.py", frozen_paths)
        self.assertNotIn("docker-compose.yml", frozen_paths)
        self.assertNotIn("docker/nginx.conf", frozen_paths)
        self.assertIn("backend/project_run_workflow.py", frozen_paths)
        self.assertIn("backend/snapshot_assembly.py", frozen_paths)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)

    def test_docker_compose_declares_dib_sidecar_as_local_gateway_service(self) -> None:
        compose = COMPOSE_FILE.read_text(encoding="utf-8")
        self.assertIn("  dib-api:\n", compose)
        self.assertIn('command: ["python", "backend/dib_http_mounting.py"]', compose)
        self.assertIn("ASIE_DIB_HTTP_HOST: 0.0.0.0", compose)
        self.assertIn('ASIE_DIB_HTTP_PORT: "8795"', compose)
        self.assertIn("ASIE_DIB_DB_PATH: /var/lib/asie/dib_local.sqlite3", compose)
        self.assertIn('ASIE_ALLOW_EXTERNAL_FETCH: "false"', compose)
        self.assertIn('- "8795"', compose)
        self.assertIn("urllib.request.urlopen('http://127.0.0.1:8795/api/dib/status'", compose)
        self.assertIn("      dib-api:\n        condition: service_healthy", compose)

    def test_nginx_routes_dib_prefix_to_sidecar_before_general_api_route(self) -> None:
        nginx = NGINX_CONF.read_text(encoding="utf-8")
        dib_location = nginx.index("location /api/dib/ {")
        api_location = nginx.index("location /api/ {")
        self.assertLess(dib_location, api_location)
        self.assertIn("proxy_pass http://dib-api:8795;", nginx)
        self.assertIn("proxy_pass http://api:8794;", nginx)

    def test_backend_image_documents_both_local_api_and_dib_sidecar_ports(self) -> None:
        dockerfile = DOCKERFILE_BACKEND.read_text(encoding="utf-8")
        self.assertIn("EXPOSE 8794 8795", dockerfile)
        self.assertIn('CMD ["python", "backend/asie_local_api.py"]', dockerfile)

    def test_dib_sidecar_gateway_requires_auth_for_mutating_routes_but_not_status(self) -> None:
        source = DIB_HTTP_MOUNTING.read_text(encoding="utf-8")
        self.assertIn('DIB_LOCAL_GATEWAY_INTEGRATION_ID = "DIB-LIVE-002I-LOCAL-API-GATEWAY-INTEGRATION-v1"', source)
        self.assertIn("def _sidecar_auth_required", source)
        self.assertIn('if _clean_path(path) == "/api/dib/status":', source)
        self.assertIn("principal_for_token", source)
        self.assertIn("authentication_required", source)
        self.assertIn("Authorization, Content-Type, X-ASIE-Organization-Id", source)

    def test_dib_gateway_mount_status_keeps_forbidden_wiring_disabled(self) -> None:
        mount = create_dib_http_mount()
        self.addCleanup(mount.close)
        status = mount.status()
        self.assertEqual(status["local_gateway_integration_id"], DIB_LOCAL_GATEWAY_INTEGRATION_ID)
        self.assertEqual(status["mount_strategy"], "freeze_safe_dib_http_overlay")
        self.assertTrue(status["sidecar_auth_required_by_default"])
        self.assertEqual(status["sidecar_auth_status_exemption"], "/api/dib/status")
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        self.assertFalse(status["frozen_http_server_mutated"])
        self.assertFalse(status["frozen_runtime_files_mutated"])
        self.assertFalse(status["snapshot_assembly_mutated"])
        self.assertFalse(status["project_run_workflow_mutated"])


if __name__ == "__main__":
    unittest.main()
