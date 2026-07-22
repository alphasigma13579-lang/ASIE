from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.aas_registry import AASRegistry, bootstrap_default_registry
from backend.contracts import PROFILE_ID, now_iso


@dataclass(frozen=True)
class AASKernelConfig:
    runtime_id: str = "asie-local-runtime"
    profile_id: str = PROFILE_ID
    frontend_port: int = 5194
    api_port: int = 8794
    external_fetch_enabled: bool = False
    ai_enabled: bool = False

    def to_boot_payload(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "profile_id": self.profile_id,
            "ports": {
                "frontend": self.frontend_port,
                "api": self.api_port,
            },
            "external_fetch_enabled": self.external_fetch_enabled,
            "ai_enabled": self.ai_enabled,
        }


class AASKernel:
    def __init__(self, config: AASKernelConfig | None = None, registry: AASRegistry | None = None) -> None:
        self.config = config or AASKernelConfig()
        self.registry = registry or bootstrap_default_registry()
        self.state = "created"
        self.created_at = now_iso()
        self.booted_at: str | None = None

    def boot(self) -> dict[str, Any]:
        self._validate_local_runtime_constraints()
        boot_payload = self.config.to_boot_payload()
        self.registry.validate_contract_payload("aas.kernel.boot.v1", boot_payload)
        self.registry.assert_socket_contract("socket.kernel.boot", "aas.kernel.boot.v1")
        self.state = "booted"
        self.booted_at = now_iso()
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "kernel": {
                "runtime_id": self.config.runtime_id,
                "profile_id": self.config.profile_id,
                "state": self.state,
                "created_at": self.created_at,
                "booted_at": self.booted_at,
                "business_logic_owner": "none",
            },
            "ports": {
                "frontend": self.config.frontend_port,
                "api": self.config.api_port,
            },
            "guards": {
                "external_fetch_enabled": self.config.external_fetch_enabled,
                "ai_enabled": self.config.ai_enabled,
                "allowed_frontend_port": 5194,
                "allowed_api_port": 8794,
            },
            "registry": self.registry.snapshot(),
        }

    def _validate_local_runtime_constraints(self) -> None:
        if self.config.frontend_port != 5194:
            raise ValueError("ASIE frontend runtime must stay on port 5194")
        if self.config.api_port != 8794:
            raise ValueError("ASIE API runtime must stay on port 8794")
        if self.config.external_fetch_enabled:
            raise ValueError("external fetch is disabled in this local AAS phase")
        if self.config.ai_enabled:
            raise ValueError("AI providers remain disabled inside the governed AI shell")


def boot_local_kernel() -> AASKernel:
    kernel = AASKernel()
    kernel.boot()
    return kernel
