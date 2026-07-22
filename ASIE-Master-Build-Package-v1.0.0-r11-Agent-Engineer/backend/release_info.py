from __future__ import annotations

from typing import Any

RELEASE_ID = "ASIE-local-r11-2026-07-20"
PRODUCT_VERSION = "0.1.0-local"
RUNTIME_FREEZE_VERSION = "1.0"
DIRECT_DEPENDENCIES = (
    {"name": "react", "version": "19.0.0", "ecosystem": "npm"},
    {"name": "react-dom", "version": "19.0.0", "ecosystem": "npm"},
    {"name": "vite", "version": "7.0.0", "ecosystem": "npm"},
    {"name": "typescript", "version": "5.8.0", "ecosystem": "npm"},
    {"name": "lucide-react", "version": "0.468.0", "ecosystem": "npm"},
)

def release_info() -> dict[str, Any]:
    return {
        "release_id": RELEASE_ID,
        "product_version": PRODUCT_VERSION,
        "runtime_freeze": {"version": RUNTIME_FREEZE_VERSION, "status": "frozen"},
        "deployment_profile": "local_controlled",
        "external_access_enabled": False,
        "external_delivery_enabled": False,
        "backup_encryption": {"status": "deferred", "required_before_external_release": True},
        "rollback": {"status": "documented", "requires_approved_release_operator": True},
        "sbom": {"format": "local-direct-dependencies.v1", "dependencies": [dict(item) for item in DIRECT_DEPENDENCIES]},
    }
