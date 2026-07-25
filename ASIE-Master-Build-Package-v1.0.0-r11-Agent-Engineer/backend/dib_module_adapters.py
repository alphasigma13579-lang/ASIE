from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from backend.dib_registry_admission import DIB_REGISTRY_ADMISSION_ID, assert_dib_runtime_alignment
from backend.dib_runtime import (
    DIB_CONTRACTS,
    DIB_MODULES,
    DIB_SOCKETS,
    apply_customer_decision,
    build_approved_input_manifest,
    build_dynamic_input_blueprint,
    build_market_evidence_pack,
    build_product_ai_interview,
    canonical_question_registry,
    canonical_template_registry,
    create_draft_revision,
    map_intake_to_blueprint_items,
    validate_manifest_for_runtime,
)

DIB_MODULE_ADAPTERS_ID = "DIB-LIVE-002B-MODULE-RUNTIME-ADAPTERS-v1"
DIB_MODULE_ADAPTERS_STATUS = "post_freeze_module_runtime_adapters"
DIB_MODULE_ADAPTERS_SOURCE = "docs/EKB/EKB-04-Agent-Reading-Order.md"

FORBIDDEN_DIB_ADAPTER_INPUT_FIELDS = frozenset(
    {
        "raw_prompt",
        "prompt_template",
        "ai_provider",
        "ai_provider_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "provider_config",
        "api_key",
        "openai_api_key",
        "finance",
        "finance_result",
        "finance_inputs",
        "snapshot",
        "assembled_snapshot",
    }
)


class DIBModuleAdapterError(ValueError):
    pass


class DIBModuleAdapter(Protocol):
    spec: "DIBModuleAdapterSpec"

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class DIBModuleAdapterSpec:
    module_id: str
    socket_id: str
    consumes_contract_id: str
    produces_contract_id: str
    purpose: str
    status: str = "post_freeze_runtime_adapter"

    def to_public(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "socket_id": self.socket_id,
            "consumes_contract_id": self.consumes_contract_id,
            "produces_contract_id": self.produces_contract_id,
            "purpose": self.purpose,
            "status": self.status,
            "adapter_id": DIB_MODULE_ADAPTERS_ID,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
        }


DIB_MODULE_ADAPTER_SPECS: tuple[DIBModuleAdapterSpec, ...] = (
    DIBModuleAdapterSpec(
        module_id="module.template_registry",
        socket_id="socket.template.registry",
        consumes_contract_id="template.registry.v1",
        produces_contract_id="template.registry.v1",
        purpose="Resolve a governed DIB template without mutating the frozen AAS registry.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.question_registry",
        socket_id="socket.question.registry",
        consumes_contract_id="question.registry.v1",
        produces_contract_id="question.registry.v1",
        purpose="Provide governed interview questions for the selected DIB template.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.product_ai_interview",
        socket_id="socket.product.ai.interview",
        consumes_contract_id="product.ai.interview.v1",
        produces_contract_id="product.ai.interview.v1",
        purpose="Run the offline Product AI Interview adapter with AI provider disabled.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.data_intake",
        socket_id="socket.data.intake",
        consumes_contract_id="data.intake.v1",
        produces_contract_id="data.intake.v1",
        purpose="Normalize manual, CSV, XLSX, and PDF-text inputs before DIB item mapping.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.dynamic_input_blueprint",
        socket_id="socket.dynamic.input.blueprint",
        consumes_contract_id="dynamic.input.blueprint.v1",
        produces_contract_id="dynamic.input.blueprint.v1",
        purpose="Assemble governed DIB items and source states before approval.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.market_intelligence",
        socket_id="socket.market.query",
        consumes_contract_id="market.query.request.v1",
        produces_contract_id="market.evidence.pack.v1",
        purpose="Return a local deterministic Market Evidence Pack without network fetch.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.approved_input_manifest",
        socket_id="socket.approved.input.manifest",
        consumes_contract_id="approved.input.manifest.v1",
        produces_contract_id="approved.input.manifest.v1",
        purpose="Convert a reviewed DIB blueprint into an Approved Input Manifest.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.manifest_validation_gate",
        socket_id="socket.manifest.validation",
        consumes_contract_id="manifest.validation.v1",
        produces_contract_id="manifest.validation.v1",
        purpose="Validate the Approved Input Manifest before any Finance Engine wiring.",
    ),
    DIBModuleAdapterSpec(
        module_id="module.dib_revision",
        socket_id="socket.dib.revision",
        consumes_contract_id="dib.draft.revision.v1",
        produces_contract_id="dib.draft.revision.v1",
        purpose="Create a controlled DIB draft revision after customer edits.",
    ),
)

CUSTOMER_DECISION_ADAPTER_SPEC = DIBModuleAdapterSpec(
    module_id="module.dynamic_input_blueprint",
    socket_id="socket.customer.item.decision",
    consumes_contract_id="customer.item.decision.v1",
    produces_contract_id="customer.item.decision.v1",
    purpose="Apply customer item decisions inside the Dynamic Input Blueprint module boundary.",
)


class BaseDIBModuleAdapter:
    spec: DIBModuleAdapterSpec

    def _validate_payload(self, payload: dict[str, Any], required_fields: tuple[str, ...] = ()) -> None:
        if not isinstance(payload, dict):
            raise DIBModuleAdapterError("DIB adapter payload must be a dict")
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise DIBModuleAdapterError(
                f"{self.spec.module_id} payload is missing fields: " + ", ".join(sorted(missing))
            )
        forbidden = sorted(FORBIDDEN_DIB_ADAPTER_INPUT_FIELDS & set(payload))
        if forbidden:
            raise DIBModuleAdapterError(
                f"{self.spec.module_id} received forbidden runtime fields: " + ", ".join(forbidden)
            )

    def _wrap_output(self, output: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(output, dict):
            raise DIBModuleAdapterError(f"{self.spec.module_id} output must be a dict")
        output_contract = str(output.get("contract_id") or self.spec.produces_contract_id)
        if output_contract != self.spec.produces_contract_id:
            raise DIBModuleAdapterError(
                f"{self.spec.module_id} produced {output_contract}, expected {self.spec.produces_contract_id}"
            )
        if output.get("external_fetch_enabled") is True:
            raise DIBModuleAdapterError(f"{self.spec.module_id} attempted to enable external fetch")
        if output.get("ai_provider_enabled") is True or output.get("ai_enabled") is True:
            raise DIBModuleAdapterError(f"{self.spec.module_id} attempted to enable AI provider")
        wrapped = dict(output)
        wrapped["contract_id"] = self.spec.produces_contract_id
        wrapped["input_contract_id"] = self.spec.consumes_contract_id
        wrapped["module_id"] = self.spec.module_id
        wrapped["socket_id"] = self.spec.socket_id
        wrapped["adapter_id"] = DIB_MODULE_ADAPTERS_ID
        wrapped["adapter_status"] = "completed"
        wrapped["adapter_source"] = DIB_MODULE_ADAPTERS_SOURCE
        wrapped["guards"] = {
            "post_freeze_overlay": True,
            "requires_live_bus_delivery_before_product_wiring": True,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "frozen_module_runtime_mutated": False,
        }
        return wrapped


class TemplateRegistryAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[0]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("project_profile",))
        registry = canonical_template_registry()
        selected = _select_template(registry, payload["project_profile"], payload.get("template_id"))
        return self._wrap_output(
            {
                "contract_id": "template.registry.v1",
                "registry_id": registry["registry_id"],
                "project_profile": dict(payload["project_profile"]),
                "template_id": selected["template_id"],
                "selected_template": selected,
                "template_items": list(selected.get("required_item_keys", []))
                + list(selected.get("recommended_item_keys", [])),
                "external_fetch_enabled": False,
            }
        )


class QuestionRegistryAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[1]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("template_id",))
        registry = canonical_question_registry()
        return self._wrap_output(
            {
                "contract_id": "question.registry.v1",
                "registry_id": registry["registry_id"],
                "template_id": payload["template_id"],
                "questions": list(registry["questions"]),
                "external_fetch_enabled": False,
            }
        )


class ProductAIInterviewAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[2]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("project_profile",))
        interview = build_product_ai_interview(dict(payload["project_profile"]))
        return self._wrap_output(interview)


class DataIntakeAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[3]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("intake_payload",))
        result = map_intake_to_blueprint_items(
            dict(payload["intake_payload"]),
            list(payload.get("existing_items") or []),
        )
        result["source_type"] = result.get("file_type") or "manual_table"
        result["normalized_rows"] = list(result.get("rows") or [])
        return self._wrap_output(result)


class DynamicInputBlueprintAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[4]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("project_profile", "items"))
        blueprint = build_dynamic_input_blueprint(
            dict(payload["project_profile"]),
            list(payload["items"]),
            source=str(payload.get("source") or "module_runtime_adapter"),
        )
        return self._wrap_output(blueprint)


class MarketIntelligenceAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[5]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload)
        item = dict(payload.get("item") or {})
        input_key = str(payload.get("input_key") or item.get("input_key") or "")
        if not input_key:
            raise DIBModuleAdapterError("module.market_intelligence requires input_key or item.input_key")
        query = payload.get("query") or item.get("label") or input_key
        pack = build_market_evidence_pack(
            {
                "input_key": input_key,
                "query": query,
                "geography": payload.get("geography") or payload.get("location_country") or "SA",
                "samples": payload.get("samples") or [],
            }
        )
        return self._wrap_output(pack)


class CustomerItemDecisionAdapter(BaseDIBModuleAdapter):
    spec = CUSTOMER_DECISION_ADAPTER_SPEC

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("item", "decision"))
        updated = apply_customer_decision(dict(payload["item"]), dict(payload["decision"]))
        return self._wrap_output(
            {
                "contract_id": "customer.item.decision.v1",
                "decision_action": payload["decision"].get("action"),
                "item": updated,
                "external_fetch_enabled": False,
            }
        )


class ApprovedInputManifestAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[6]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("blueprint",))
        return self._wrap_output(build_approved_input_manifest(dict(payload["blueprint"])))


class ManifestValidationGateAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[7]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("manifest",))
        return self._wrap_output(validate_manifest_for_runtime(dict(payload["manifest"])))


class DIBRevisionAdapter(BaseDIBModuleAdapter):
    spec = DIB_MODULE_ADAPTER_SPECS[8]

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload, ("previous_blueprint", "changes"))
        revision = create_draft_revision(
            dict(payload["previous_blueprint"]),
            list(payload["changes"]),
            reason=str(payload.get("reason") or "module_runtime_adapter_revision"),
        )
        return self._wrap_output(revision)


DIB_MODULE_ADAPTER_CLASSES: tuple[type[BaseDIBModuleAdapter], ...] = (
    TemplateRegistryAdapter,
    QuestionRegistryAdapter,
    ProductAIInterviewAdapter,
    DataIntakeAdapter,
    DynamicInputBlueprintAdapter,
    MarketIntelligenceAdapter,
    ApprovedInputManifestAdapter,
    ManifestValidationGateAdapter,
    DIBRevisionAdapter,
)


def build_dib_module_adapters(*, include_customer_decision: bool = True) -> dict[str, BaseDIBModuleAdapter]:
    adapters: dict[str, BaseDIBModuleAdapter] = {adapter_class.spec.module_id: adapter_class() for adapter_class in DIB_MODULE_ADAPTER_CLASSES}
    if include_customer_decision:
        adapters["module.customer_item_decision"] = CustomerItemDecisionAdapter()
    return adapters


def registered_dib_module_adapter_specs() -> tuple[dict[str, Any], ...]:
    specs = [spec.to_public() for spec in DIB_MODULE_ADAPTER_SPECS]
    specs.append(CUSTOMER_DECISION_ADAPTER_SPEC.to_public() | {"adapter_alias": "module.customer_item_decision"})
    return tuple(specs)


def execute_dib_module_adapter(module_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    adapters = build_dib_module_adapters()
    try:
        adapter = adapters[module_id]
    except KeyError as exc:
        raise DIBModuleAdapterError(f"unknown DIB module adapter: {module_id}") from exc
    return adapter.handle(payload)


def assert_dib_module_adapter_alignment() -> None:
    assert_dib_runtime_alignment()
    specs = set(DIB_MODULE_ADAPTER_SPECS)
    module_ids = {spec.module_id for spec in specs}
    socket_ids = {spec.socket_id for spec in specs} | {CUSTOMER_DECISION_ADAPTER_SPEC.socket_id}
    consumed_contracts = {spec.consumes_contract_id for spec in specs} | {CUSTOMER_DECISION_ADAPTER_SPEC.consumes_contract_id}
    produced_contracts = {spec.produces_contract_id for spec in specs} | {CUSTOMER_DECISION_ADAPTER_SPEC.produces_contract_id}
    missing_modules = set(DIB_MODULES) - module_ids
    extra_modules = module_ids - set(DIB_MODULES)
    if missing_modules or extra_modules:
        raise DIBModuleAdapterError(
            "DIB module adapter module mismatch: "
            f"missing={sorted(missing_modules)} extra={sorted(extra_modules)}"
        )
    if not socket_ids.issubset(set(DIB_SOCKETS)):
        raise DIBModuleAdapterError("DIB module adapter references unknown sockets")
    if not consumed_contracts.issubset(set(DIB_CONTRACTS)):
        raise DIBModuleAdapterError("DIB module adapter consumes unknown contracts")
    if not produced_contracts.issubset(set(DIB_CONTRACTS)):
        raise DIBModuleAdapterError("DIB module adapter produces unknown contracts")


def assert_dib_module_adapters_keep_finance_unwired() -> None:
    for spec in DIB_MODULE_ADAPTER_SPECS:
        material = " ".join((spec.module_id, spec.socket_id, spec.consumes_contract_id, spec.produces_contract_id)).lower()
        if "finance" in material:
            raise DIBModuleAdapterError("DIB-LIVE-002B must not wire Finance Engine")


def dib_module_adapter_status() -> dict[str, Any]:
    return {
        "adapter_id": DIB_MODULE_ADAPTERS_ID,
        "status": DIB_MODULE_ADAPTERS_STATUS,
        "registry_admission_id": DIB_REGISTRY_ADMISSION_ID,
        "spec_count": len(DIB_MODULE_ADAPTER_SPECS),
        "customer_decision_adapter_included": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "frozen_module_runtime_mutated": False,
        "adapters": list(registered_dib_module_adapter_specs()),
    }


def _select_template(registry: dict[str, Any], project_profile: dict[str, Any], template_id: Any = None) -> dict[str, Any]:
    templates = [dict(row) for row in registry.get("templates", [])]
    requested_template_id = str(template_id or "").strip()
    if requested_template_id:
        for template in templates:
            if template.get("template_id") == requested_template_id:
                return template
        raise DIBModuleAdapterError(f"unknown DIB template_id: {requested_template_id}")
    activity_material = " ".join(
        str(project_profile.get(key) or "")
        for key in ("activity", "activity_description", "name", "project_name", "sector")
    ).lower()
    preferred_id = "template:food-service:shawarma:v1" if "shawarma" in activity_material or "شاور" in activity_material else "template:generic-startup:v1"
    for template in templates:
        if template.get("template_id") == preferred_id:
            return template
    if not templates:
        raise DIBModuleAdapterError("DIB template registry is empty")
    return templates[0]
