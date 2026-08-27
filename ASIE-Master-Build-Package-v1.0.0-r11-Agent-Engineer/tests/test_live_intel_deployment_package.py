from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_production_environment_template_is_secret_free_and_pinecone_targeted() -> None:
    content = read(PACKAGE_ROOT / ".env.production.example")
    assert "ASIE_ALLOW_EXTERNAL_FETCH=false" in content
    assert "PINECONE_INDEX=vision2030-kb" in content
    assert "PINECONE_API_VERSION=2026-04" in content
    assert "PINECONE_EMBED_MODEL=multilingual-e5-large" in content
    assert "DEEPSEEK_MODEL=deepseek-v4-flash" in content
    assert "ASIE_EXTERNAL_ROBOTS_FAILURE_MODE=deny" in content
    for secret_name in (
        "DEEPSEEK_API_KEY",
        "TAVILY_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "VITE_GOOGLE_MAPS_BROWSER_KEY",
        "PINECONE_API_KEY",
    ):
        assert f"{secret_name}=\n" in content


def test_google_browser_map_build_configuration_is_separated_from_server_key() -> None:
    environment = read(PACKAGE_ROOT / ".env.production.example")
    frontend = read(PACKAGE_ROOT / "Dockerfile.frontend")
    compose = read(PACKAGE_ROOT / "docker-compose.production.yml")
    workflow = read(REPOSITORY_ROOT / ".github" / "workflows" / "deploy-hostinger.yml")

    assert "VITE_GOOGLE_MAPS_BROWSER_KEY=\n" in environment
    assert "GOOGLE_MAP_ID=\n" in environment
    assert "ARG VITE_GOOGLE_MAPS_BROWSER_KEY\n" in frontend
    assert "ARG VITE_GOOGLE_MAP_ID\n" in frontend
    browser_key_export = "ENV VITE_GOOGLE_MAPS_BROWSER_KEY=${VITE_GOOGLE_MAPS_BROWSER_KEY}"
    map_id_export = "ENV VITE_GOOGLE_MAP_ID=${VITE_GOOGLE_MAP_ID}"
    build_step = "RUN corepack enable && pnpm install --frozen-lockfile && pnpm build"
    assert browser_key_export in frontend
    assert map_id_export in frontend
    assert frontend.index(browser_key_export) < frontend.index(build_step)
    assert frontend.index(map_id_export) < frontend.index(build_step)
    assert "GOOGLE_MAPS_API_KEY" not in frontend

    _before_web, web_marker, after_web = compose.partition("\n  web:\n")
    assert web_marker, "web service block missing"
    web_service, caddy_marker, _after_caddy = after_web.partition("\n  caddy:\n")
    assert caddy_marker, "caddy service block missing after web"
    assert "VITE_GOOGLE_MAPS_BROWSER_KEY: ${VITE_GOOGLE_MAPS_BROWSER_KEY:-}" in web_service
    assert "VITE_GOOGLE_MAP_ID: ${GOOGLE_MAP_ID:-}" in web_service
    assert "GOOGLE_MAPS_API_KEY" not in web_service
    assert "VITE_GOOGLE_MAPS_BROWSER_KEY: ${{ secrets.VITE_GOOGLE_MAPS_BROWSER_KEY }}" in workflow
    assert "GOOGLE_MAP_ID: ${{ secrets.GOOGLE_MAP_ID }}" in workflow
    required_provider_line = "for name in DEEPSEEK_API_KEY TAVILY_API_KEY GOOGLE_MAPS_API_KEY VITE_GOOGLE_MAPS_BROWSER_KEY PINECONE_API_KEY; do"
    assert required_provider_line in workflow
    assert "GOOGLE_MAP_ID" not in required_provider_line
    assert '\"VITE_GOOGLE_MAPS_BROWSER_KEY\": os.environ.get(\"VITE_GOOGLE_MAPS_BROWSER_KEY\", \"\")' in workflow
    assert '\"GOOGLE_MAP_ID\": os.environ.get(\"GOOGLE_MAP_ID\", \"\")' in workflow
    assert 'value=$(printenv "$name")' not in workflow
    assert workflow.count('value=$(printenv "$name" || true)') == 2
    for text in (environment, frontend, compose, workflow):
        assert text.endswith("\n")
    assert Path(__file__).read_bytes().endswith(b"\n")


def test_gitignore_blocks_populated_environments_and_private_keys() -> None:
    content = read(PACKAGE_ROOT / ".gitignore")
    assert ".env.*" in content
    assert "!.env.production.example" in content
    assert "*.pem" in content
    assert "*.key" in content
    assert "secrets/" in content


def test_production_compose_exposes_only_caddy_and_keeps_apis_internal() -> None:
    content = read(PACKAGE_ROOT / "docker-compose.production.yml")
    assert '"80:80"' in content
    assert '"443:443"' in content
    assert '"443:443/udp"' in content
    assert '"8794:8794"' not in content
    assert '"8795:8795"' not in content
    assert 'expose:\n      - "8794"' in content
    assert 'expose:\n      - "8795"' in content
    assert "read_only: true" in content
    assert "no-new-privileges:true" in content
    assert "ASIE_ALLOWED_ORIGINS: https://${ASIE_DOMAIN}" in content
    assert "caddy-data:" in content
    assert "asie-data:" in content


def test_caddy_enables_tls_and_security_headers() -> None:
    content = read(PACKAGE_ROOT / "deploy" / "Caddyfile")
    assert "{$ASIE_DOMAIN}" in content
    assert "reverse_proxy web:80" in content
    assert "Strict-Transport-Security" in content
    assert "X-Content-Type-Options" in content
    assert "Permissions-Policy" in content
    assert "geolocation=(self)" in content


def test_deployment_workflow_is_manual_and_protected() -> None:
    content = read(REPOSITORY_ROOT / ".github" / "workflows" / "deploy-hostinger.yml")
    assert "workflow_dispatch:" in content
    assert "push:" not in content
    assert "environment: production" in content
    assert "HOSTINGER_VPS_SSH_KEY" in content
    assert "PINECONE_INDEX\": \"vision2030-kb\"" in content
    assert "DEEPSEEK_MODEL\": \"deepseek-v4-flash\"" in content
    assert "ASIE_EXTERNAL_ALLOWED_HOSTS" in content
    assert "enable_external_fetch" in content
    assert "release_commit" in content
    assert "release_evidence_run_id" in content
    assert "public_release_authorized" in content
    assert "production_deployment_authorized" in content
    assert "git rev-parse origin/main" in content
    assert "rel-beta-07-complete-evidence" in content
    assert "pytest -q" in content
    assert 'git checkout --detach "$ASIE_RELEASE_COMMIT"' in content
    assert "git reset --hard origin/main" not in content
    assert "rm -f /tmp/asie.env.production" in content


def test_deployment_and_backup_scripts_are_fail_fast() -> None:
    deploy = read(PACKAGE_ROOT / "deploy" / "hostinger-vps-deploy.sh")
    backup = read(PACKAGE_ROOT / "deploy" / "backup.sh")
    assert "set -eu" in deploy
    assert "docker compose" in deploy
    assert "config --quiet" in deploy
    assert "up -d --remove-orphans" in deploy
    assert "set -eu" in backup
    assert "sqlite3.connect" in backup
    assert "PRAGMA integrity_check" in backup
    assert "gzip.open" in backup
    assert "ASIE_BACKUP_RETENTION_DAYS" in read(PACKAGE_ROOT / ".env.production.example")


def test_provider_files_do_not_touch_frozen_runtime() -> None:
    paths = (
        PACKAGE_ROOT / "backend" / "external_acquisition.py",
        PACKAGE_ROOT / "backend" / "live_provider_catalog.py",
        PACKAGE_ROOT / "backend" / "live_provider_clients.py",
    )
    content = "\n".join(read(path) for path in paths)
    for forbidden in (
        "from backend.aas_kernel",
        "from backend.system_bus",
        "from backend.project_run_workflow",
        "from backend.snapshot_assembly",
        "ProjectRunWorkflow(",
        "SnapshotAssembly(",
    ):
        assert forbidden not in content
    assert '"eligible_for_controlled_assumptions": False' in content
    assert '"source_of_truth": False' in content


def test_live_intel_execution_record_is_honest_about_remaining_work() -> None:
    content = read(PACKAGE_ROOT / "docs" / "LIVE-INTEL-001-GOVERNED-EXTERNAL-ACQUISITION-AND-DEPLOYMENT-2026-07-27.md")
    assert "vision2030-kb" in content
    assert "not yet connected" in content
    assert "actual VPS deployment" in content
    assert "not a sovereign source of truth" in content
    assert "DeepSeek activation inside `AIIntegrationShell`" in content
