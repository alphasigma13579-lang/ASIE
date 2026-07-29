from __future__ import annotations

from typing import Any

from backend.dib_api import (
    DIBApiController,
    DIBApiError,
    DIBApiResponse,
    _parts,
    _query_bool,
    _query_value,
)
from backend.dib_canonical_finance_admission import (
    DIBCanonicalFinanceAdmission,
    DIBCanonicalFinanceAdmissionError,
)
from backend.dib_persistence import DIBPersistenceStore, create_dib_persistence_store
from backend.dib_server_owned_manifest_chain import (
    DIBServerOwnedManifestChain,
    DIBServerOwnedManifestChainError,
)
from backend.dib_tenant_boundary import (
    DIBTenantBoundary,
    DIBTenantBoundaryError,
    DIBTenantContext,
    ProjectOrganizationResolver,
)

DIB_TENANT_API_ID = "SEC-BETA-03-DIB-TENANT-SCOPED-API-v1"


class TenantScopedDIBApiController(DIBApiController):
    """DIB API controller with tenant ownership and canonical run admission."""

    def __init__(
        self,
        store: DIBPersistenceStore | None = None,
        *,
        project_organization_resolver: ProjectOrganizationResolver | None = None,
        trusted_internal_context: DIBTenantContext | None = None,
        canonical_finance_admission: DIBCanonicalFinanceAdmission | None = None,
    ) -> None:
        super().__init__(store or create_dib_persistence_store())
        self.tenant_boundary = DIBTenantBoundary(
            self.store,
            project_organization_resolver=project_organization_resolver,
        )
        self.server_owned_manifest_chain = DIBServerOwnedManifestChain(self.store)
        self.canonical_finance_admission = canonical_finance_admission
        self.trusted_internal_context = trusted_internal_context

    def status(self) -> dict[str, Any]:
        return {
            **super().status(),
            "tenant_api_id": DIB_TENANT_API_ID,
            "tenant_boundary": self.tenant_boundary.status(),
            "server_owned_manifest_chain": self.server_owned_manifest_chain.status(),
            "canonical_finance_admission": (
                self.canonical_finance_admission.status()
                if self.canonical_finance_admission is not None
                else {
                    "status": "executor_unavailable",
                    "direct_finance_execution_enabled": False,
                    "canonical_project_run_execution_enabled": False,
                }
            ),
            "organization_scope_required": True,
            "cross_tenant_access_blocked": True,
            "client_owned_manifest_rejected": True,
            "client_owned_gate_rejected": True,
            "direct_finance_execution_enabled": False,
            "canonical_project_run_execution_enabled": self.canonical_finance_admission is not None,
        }

    def dispatch(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        context: DIBTenantContext | None = None,
    ) -> DIBApiResponse:
        method = method.upper().strip()
        parts = _parts(path)
        if method == "GET" and parts == ["api", "dib", "status"]:
            return super().dispatch(method, path, payload)

        request_context = context or self.trusted_internal_context
        if request_context is None:
            raise DIBApiError("dib_tenant_context_required", 403)

        try:
            if method == "POST" and parts == ["api", "dib", "sessions"]:
                return self._start_tenant_session(request_context, dict(payload or {}))
            if method == "GET" and parts == ["api", "dib", "sessions"]:
                return self._list_tenant_sessions(request_context, path)
            if len(parts) >= 4 and parts[:3] == ["api", "dib", "sessions"]:
                session_id = parts[3]
                tail = parts[4:]
                if method == "GET" and not tail:
                    return DIBApiResponse(
                        200,
                        {"session": self.tenant_boundary.load_session(request_context, session_id)},
                    )
                if method == "GET" and tail == ["events"]:
                    return DIBApiResponse(
                        200,
                        {"events": self.tenant_boundary.load_events(request_context, session_id)},
                    )
                if method == "POST" and tail == ["close"]:
                    return DIBApiResponse(
                        200,
                        {
                            "session": self.tenant_boundary.close_session(request_context, session_id),
                            "snapshot_mutation": False,
                        },
                    )
                self.tenant_boundary.require_session_access(request_context, session_id)
                if method == "POST" and tail == ["approved-manifests"]:
                    return self._build_server_owned_manifest(
                        request_context,
                        session_id,
                        dict(payload or {}),
                    )
                if method == "POST" and tail == ["validation-gates"]:
                    return self._build_server_owned_gate(
                        request_context,
                        session_id,
                        dict(payload or {}),
                    )
                if method == "POST" and tail == ["controlled-finance"]:
                    return self._execute_canonical_finance_admission(
                        request_context,
                        session_id,
                        dict(payload or {}),
                    )
            return super().dispatch(method, path, payload)
        except DIBTenantBoundaryError as exc:
            code = str(exc)
            if code in {
                "dib_session_not_found",
                "dib_project_not_found",
                "dib_project_ownership_resolver_required",
            }:
                raise DIBApiError("dib_resource_not_found", 404) from exc
            raise DIBApiError(code, 403) from exc
        except DIBServerOwnedManifestChainError as exc:
            code = str(exc)
            status = 409 if code.startswith("stale_") or "requires_persisted" in code else 422
            raise DIBApiError(code, status) from exc
        except DIBCanonicalFinanceAdmissionError as exc:
            raise DIBApiError(exc.code, exc.status) from exc

    def _start_tenant_session(
        self,
        context: DIBTenantContext,
        payload: dict[str, Any],
    ) -> DIBApiResponse:
        project_profile = payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else payload
        if not isinstance(project_profile, dict) or not project_profile.get("project_id"):
            raise DIBApiError("dib_session_requires_project_profile", 400)
        session = self.tenant_boundary.start_session(context, dict(project_profile))
        return DIBApiResponse(201, {"session": session, "snapshot_mutation": False})

    def _list_tenant_sessions(self, context: DIBTenantContext, path: str) -> DIBApiResponse:
        project_id = _query_value(path, "project_id")
        if not project_id:
            raise DIBApiError("dib_session_query_requires_project_id", 400)
        try:
            limit = min(25, max(1, int(_query_value(path, "limit") or 10)))
        except ValueError as exc:
            raise DIBApiError("invalid DIB session query limit", 422) from exc
        session_ids = self.tenant_boundary.list_session_ids_for_project(
            context,
            project_id,
            include_closed=_query_bool(path, "include_closed", default=False),
            limit=limit,
        )
        sessions = [self.tenant_boundary.load_session(context, session_id) for session_id in session_ids]
        return DIBApiResponse(
            200,
            {
                "sessions": sessions,
                "latest_session": sessions[0] if sessions else None,
                "resume_available": bool(sessions),
                "project_id": project_id,
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _build_server_owned_manifest(
        self,
        context: DIBTenantContext,
        session_id: str,
        payload: dict[str, Any],
    ) -> DIBApiResponse:
        manifest = self.server_owned_manifest_chain.build_manifest(
            session_id,
            payload,
            actor_user_id=context.user_id,
        )
        return DIBApiResponse(
            201,
            {
                "approved_manifest": manifest,
                "manifest_server_owned": True,
                "finance_wiring_enabled": False,
                "snapshot_mutation": False,
            },
        )

    def _build_server_owned_gate(
        self,
        context: DIBTenantContext,
        session_id: str,
        payload: dict[str, Any],
    ) -> DIBApiResponse:
        gate = self.server_owned_manifest_chain.build_gate(
            session_id,
            payload,
            actor_user_id=context.user_id,
        )
        return DIBApiResponse(
            201,
            {
                "validation_gate": gate,
                "validation_gate_server_owned": True,
                "finance_wiring_enabled": False,
                "snapshot_mutation": False,
            },
        )

    def _execute_canonical_finance_admission(
        self,
        context: DIBTenantContext,
        session_id: str,
        payload: dict[str, Any],
    ) -> DIBApiResponse:
        if self.canonical_finance_admission is None:
            raise DIBApiError("canonical_project_run_executor_unavailable", 503)
        result = self.canonical_finance_admission.execute(
            session_id,
            context,
            payload,
        )
        self.tenant_boundary.append_event(
            context,
            session_id,
            event_type="project_run.canonical_admission",
            entity_type="project_run",
            entity_id=str(result.get("run_id") or result.get("input_hash") or session_id),
            payload={
                "status": result.get("status"),
                "run_id": result.get("run_id"),
                "snapshot_id": result.get("snapshot_id"),
                "manifest_id": result.get("lineage", {}).get("manifest_id"),
                "gate_id": result.get("lineage", {}).get("gate_id"),
                "project_run_workflow_mount": result.get("project_run_workflow_mount"),
                "idempotency_replayed": result.get("idempotency_replayed", False),
            },
        )
        executed = result.get("status") == "executed"
        replayed = bool(result.get("idempotency_replayed"))
        return DIBApiResponse(
            200 if replayed or not executed else 201,
            {
                "controlled_finance": result,
                "controlled_finance_executed": executed,
                "canonical_project_run_executed": executed,
                "run_id": result.get("run_id"),
                "snapshot_id": result.get("snapshot_id"),
                "project_run_workflow_mount": result.get("project_run_workflow_mount"),
                "finance_wiring_enabled": False,
                "snapshot_mutation": bool(result.get("snapshot_mutation")),
            },
        )


def create_tenant_scoped_dib_api_controller(
    store: DIBPersistenceStore | None = None,
    *,
    project_organization_resolver: ProjectOrganizationResolver | None = None,
    trusted_internal_context: DIBTenantContext | None = None,
    canonical_finance_admission: DIBCanonicalFinanceAdmission | None = None,
) -> TenantScopedDIBApiController:
    return TenantScopedDIBApiController(
        store,
        project_organization_resolver=project_organization_resolver,
        trusted_internal_context=trusted_internal_context,
        canonical_finance_admission=canonical_finance_admission,
    )
