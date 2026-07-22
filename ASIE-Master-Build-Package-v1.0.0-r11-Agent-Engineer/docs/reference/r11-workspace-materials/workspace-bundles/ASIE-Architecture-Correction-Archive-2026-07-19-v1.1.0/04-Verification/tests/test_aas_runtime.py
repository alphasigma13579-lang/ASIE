from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.aas_kernel import AASKernel, AASKernelConfig
from backend.architecture_status import build_architecture_runtime_status
from backend.ai_integration import AIIntegrationError, AIIntegrationShell, OutputValidation, ProviderRegistry
from backend.aas_registry import (
    AASRegistry,
    ContractDefinition,
    ContractValidationError,
    DuplicateRegistrationError,
    ModuleDefinition,
    SocketDefinition,
    UnknownRegistrationError,
    bootstrap_default_registry,
)
from backend.bus_controller import BusController, BusControllerError
from backend.heart_controller import HeartController, HeartControllerError, HeartTask
from backend.hearts import HeartError, default_hearts
from backend.module_runtime import AIIntegrationModuleAdapter, ModuleRuntime, ModuleRuntimeError, RunScopedModuleRuntime
from backend.project_run_workflow import (
    ProjectRunEnvelope,
    ProjectRunIdempotencyStore,
    ProjectRunWorkflow,
    normalize_project_run_http_request,
)
from backend.socket_contracts import SocketContractError, SocketContractLayer
from backend.snapshot_assembly import REQUIRED_MODULE_OUTPUTS, seal_module_output
from backend.system_bus import BusMessage, SystemBus, SystemBusError


class AASRuntimeTests(unittest.TestCase):
    def test_kernel_boots_local_runtime_with_expected_ports(self) -> None:
        kernel = AASKernel()
        status = kernel.boot()

        self.assertEqual(status["kernel"]["state"], "booted")
        self.assertEqual(status["ports"]["frontend"], 5194)
        self.assertEqual(status["ports"]["api"], 8794)
        self.assertFalse(status["guards"]["external_fetch_enabled"])
        self.assertFalse(status["guards"]["ai_enabled"])
        self.assertEqual(status["kernel"]["business_logic_owner"], "none")

    def test_kernel_rejects_forbidden_ports_external_fetch_and_ai(self) -> None:
        invalid_configs = [
            AASKernelConfig(frontend_port=5173),
            AASKernelConfig(api_port=8000),
            AASKernelConfig(external_fetch_enabled=True),
            AASKernelConfig(ai_enabled=True),
        ]

        for config in invalid_configs:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    AASKernel(config=config).boot()

    def test_default_registry_contains_runtime_and_current_engine_descriptors(self) -> None:
        registry = bootstrap_default_registry()
        snapshot = registry.snapshot()
        module_ids = {module["module_id"] for module in snapshot["modules"]}
        contract_ids = {contract["contract_id"] for contract in snapshot["contracts"]}

        self.assertIn("aas.kernel", module_ids)
        self.assertIn("aas.registry", module_ids)
        self.assertIn("module.finance", module_ids)
        self.assertIn("module.evidence_ledger", module_ids)
        self.assertIn("module.sector_intelligence", module_ids)
        self.assertIn("module.decision_council", module_ids)
        self.assertIn("module.risk_engine", module_ids)
        self.assertIn("module.execution_engine", module_ids)
        self.assertIn("module.reports", module_ids)
        self.assertIn("aas.kernel.boot.v1", contract_ids)
        self.assertIn("aas.registry.snapshot.v1", contract_ids)
        self.assertIn("aas.heart_controller", module_ids)
        self.assertIn("aas.heart.M1", module_ids)
        self.assertIn("aas.heart.M2", module_ids)
        self.assertIn("aas.heart.M3", module_ids)
        self.assertIn("aas.heart.status.v1", contract_ids)
        self.assertIn("aas.heart.assignment.v1", contract_ids)
        self.assertIn("aas.bus_controller", module_ids)
        self.assertIn("aas.system_bus", module_ids)
        self.assertIn("aas.bus.status.v1", contract_ids)
        self.assertIn("aas.bus.message.v1", contract_ids)
        self.assertIn("aas.socket_contract_layer", module_ids)
        self.assertIn("aas.socket.enforcement.v1", contract_ids)
        self.assertIn("aas.module_runtime", module_ids)
        self.assertIn("aas.module.execution.v1", contract_ids)
        self.assertIn("risk.register.v1", contract_ids)
        self.assertIn("risk.advisory.summary.v1", contract_ids)
        self.assertIn("execution.plan.v1", contract_ids)
        self.assertIn("finance.calculate.v1", contract_ids)
        self.assertIn("evidence.ledger.build.v1", contract_ids)
        self.assertIn("sector.intelligence.build.v1", contract_ids)
        self.assertIn("decision.council.evaluate.v1", contract_ids)
        self.assertIn("risk.register.build.v1", contract_ids)
        self.assertIn("execution.plan.build.v1", contract_ids)
        self.assertIn("report.snapshot.project.v1", contract_ids)
        self.assertIn("decision.pack.project.v1", contract_ids)
        self.assertIn("aas.sealed.module.output.v1", contract_ids)
        self.assertIn("snapshot.assemble.v1", contract_ids)
        self.assertIn("decision.pack.v1", contract_ids)
        self.assertIn("module.snapshot_assembly", module_ids)
        self.assertIn("module.decision_pack", module_ids)
        self.assertIn("module.ai_integration", module_ids)
        self.assertIn("ai.integration.request.v1", contract_ids)
        self.assertIn("ai.integration.result.v1", contract_ids)
        self.assertEqual(registry.socket("socket.finance.evaluate").contract_id, "finance.calculate.v1")
        self.assertEqual(registry.socket("socket.report.snapshot").contract_id, "report.snapshot.project.v1")
        self.assertEqual(registry.socket("socket.decision.pack").contract_id, "decision.pack.project.v1")
        self.assertFalse(snapshot["external_fetch_enabled"])

    def test_registry_enforces_contract_before_socket_and_socket_before_module(self) -> None:
        registry = AASRegistry()

        with self.assertRaises(UnknownRegistrationError):
            registry.register_socket(
                SocketDefinition(
                    socket_id="socket.test",
                    contract_id="missing.contract.v1",
                    provider_module_id="module.test",
                )
            )

        registry.register_contract(
            ContractDefinition(
                contract_id="test.contract.v1",
                version="1.0.0",
                owner="Test",
                purpose="Test contract",
            )
        )

        with self.assertRaises(UnknownRegistrationError):
            registry.register_module(
                ModuleDefinition(
                    module_id="module.test",
                    label="Test",
                    module_type="test",
                    owner_file="backend/test.py",
                    provides=("socket.missing",),
                )
            )

        registry.register_socket(
            SocketDefinition(
                socket_id="socket.test",
                contract_id="test.contract.v1",
                provider_module_id="module.test",
            )
        )
        registered = registry.register_module(
            ModuleDefinition(
                module_id="module.test",
                label="Test",
                module_type="test",
                owner_file="backend/test.py",
                provides=("socket.test",),
            )
        )

        self.assertEqual(registered.module_id, "module.test")

    def test_registry_rejects_duplicates_external_fetch_and_invalid_payloads(self) -> None:
        registry = AASRegistry()
        contract = ContractDefinition(
            contract_id="payload.contract.v1",
            version="1.0.0",
            owner="Test",
            purpose="Required field test",
            required_fields=("project_id", "snapshot_id"),
        )
        registry.register_contract(contract)

        with self.assertRaises(DuplicateRegistrationError):
            registry.register_contract(contract)

        registry.register_socket(
            SocketDefinition(
                socket_id="socket.payload",
                contract_id="payload.contract.v1",
                provider_module_id="module.payload",
            )
        )

        with self.assertRaises(ContractValidationError):
            registry.register_module(
                ModuleDefinition(
                    module_id="module.payload",
                    label="Payload",
                    module_type="test",
                    owner_file="backend/payload.py",
                    provides=("socket.payload",),
                    external_fetch_enabled=True,
                )
            )

        with self.assertRaises(ContractValidationError):
            registry.validate_contract_payload("payload.contract.v1", {"project_id": "proj_1"})

        registry.validate_contract_payload(
            "payload.contract.v1",
            {"project_id": "proj_1", "snapshot_id": "snap_1"},
        )

    def test_heart_controller_requires_booted_kernel(self) -> None:
        kernel = AASKernel()
        controller = HeartController(kernel)

        with self.assertRaises(HeartControllerError):
            controller.bootstrap()

    def test_heart_controller_bootstraps_primary_assist_and_reserve(self) -> None:
        kernel = AASKernel()
        kernel.boot()
        controller = HeartController(kernel)
        status = controller.bootstrap()
        hearts = {heart["role"]: heart for heart in status["hearts"]}

        self.assertEqual(status["state"], "ready")
        self.assertEqual(hearts["primary"]["heart_id"], "M1")
        self.assertEqual(hearts["primary"]["state"], "active")
        self.assertEqual(hearts["assist"]["heart_id"], "M2")
        self.assertEqual(hearts["assist"]["state"], "assist_ready")
        self.assertEqual(hearts["reserve"]["heart_id"], "M3")
        self.assertEqual(hearts["reserve"]["state"], "reserved")
        self.assertTrue(status["guards"]["no_heart_acts_without_controller"])
        self.assertTrue(status["guards"]["no_heart_executes_business_logic"])
        self.assertTrue(status["guards"]["no_heart_issues_sovereign_verdict"])

    def test_heart_cannot_accept_assignment_without_controller(self) -> None:
        hearts = default_hearts()
        primary = hearts["primary"]
        primary.bootstrap(state="active", activation_reason="test")

        with self.assertRaises(HeartError):
            primary.assign(task_id="task_1", assigned_by="direct_module", reason="bypass")

    def test_controller_assigns_primary_only_or_primary_with_assist(self) -> None:
        kernel = AASKernel()
        kernel.boot()
        controller = HeartController(kernel)
        controller.bootstrap()

        primary_only = controller.assign_task(
            HeartTask(task_id="task_primary", purpose="runtime_coordination", requires_assist=False)
        )
        with_assist = controller.assign_task(
            HeartTask(task_id="task_assist", purpose="runtime_coordination", requires_assist=True)
        )

        self.assertEqual(primary_only["mode"], "primary_only")
        self.assertEqual(len(primary_only["assignments"]), 1)
        self.assertEqual(primary_only["assignments"][0]["role"], "primary")
        self.assertFalse(primary_only["business_logic_executed"])
        self.assertFalse(primary_only["sovereign_verdict_issued"])
        self.assertEqual(with_assist["mode"], "primary_with_assist")
        self.assertEqual({item["role"] for item in with_assist["assignments"]}, {"primary", "assist"})
        self.assertFalse(with_assist["reserve_used"])

    def test_reserve_heart_is_failover_only(self) -> None:
        kernel = AASKernel()
        kernel.boot()
        controller = HeartController(kernel)
        controller.bootstrap()

        before = {heart["role"]: heart for heart in controller.status()["hearts"]}
        event = controller.failover_to_reserve(reason="primary_degraded_test")
        after = {heart["role"]: heart for heart in controller.status()["hearts"]}

        self.assertEqual(before["reserve"]["state"], "reserved")
        self.assertEqual(event["event"], "reserve_failover")
        self.assertEqual(after["primary"]["state"], "degraded")
        self.assertEqual(after["reserve"]["state"], "active")
        self.assertFalse(event["business_logic_executed"])
        self.assertFalse(event["sovereign_verdict_issued"])

    def test_bus_controller_requires_kernel_and_heart_controller_ready(self) -> None:
        kernel = AASKernel()
        heart_controller = HeartController(kernel)

        with self.assertRaises(BusControllerError):
            BusController(kernel, heart_controller).bootstrap()

        kernel.boot()
        with self.assertRaises(BusControllerError):
            BusController(kernel, heart_controller).bootstrap()

        heart_controller.bootstrap()
        status = BusController(kernel, heart_controller).bootstrap()

        self.assertEqual(status["state"], "ready")
        self.assertTrue(status["guards"]["requires_contract_id"])
        self.assertTrue(status["guards"]["requires_socket_id"])
        self.assertTrue(status["guards"]["requires_operation_id"])
        self.assertTrue(status["guards"]["requires_idempotency_key"])
        self.assertTrue(status["guards"]["requires_input_hash"])
        self.assertTrue(status["guards"]["requires_correlation_id"])
        self.assertTrue(status["guards"]["requires_audit_ref"])
        self.assertFalse(status["guards"]["executes_business_logic"])
        self.assertIsNotNone(status["guards"]["socket_contract_layer"])
        self.assertEqual(status["guards"]["socket_contract_layer"]["state"], "enforcing")

    def test_system_bus_requires_ready_bus_controller(self) -> None:
        kernel = AASKernel()
        kernel.boot()
        heart_controller = HeartController(kernel)
        heart_controller.bootstrap()
        bus_controller = BusController(kernel, heart_controller)

        with self.assertRaises(SystemBusError):
            SystemBus(bus_controller).bootstrap()

    def test_system_bus_accepts_complete_message_without_executing_business_logic(self) -> None:
        kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_test_1",
            audit_ref="audit:test:bus:1",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {},
            },
        )

        record = bus.publish(message)

        self.assertTrue(record["delivered"])
        self.assertTrue(record["admission"]["accepted"])
        self.assertFalse(record["business_logic_executed"])
        self.assertEqual(record["message"]["correlation_id"], "corr_test_1")
        self.assertTrue(record["message"]["operation_id"].startswith("op_"))
        self.assertTrue(record["message"]["idempotency_key"].startswith("idem_"))
        self.assertRegex(record["message"]["input_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(kernel.registry.socket("socket.finance.evaluate").provider_module_id, "module.finance")

    def test_system_bus_rejects_message_missing_required_envelope_fields(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        incomplete = SimpleNamespace(
            message_id="msg_missing",
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_missing",
            payload={"project_id": "proj_1", "run_id": "run_1", "snapshot_id": "snap_1", "inputs": {}},
        )

        record = bus.try_publish(incomplete)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertIn("missing_required_message_fields", record["admission"]["reason"])
        self.assertIn("audit_ref", record["admission"]["reason"])
        self.assertIn("operation_id", record["admission"]["reason"])
        self.assertIn("idempotency_key", record["admission"]["reason"])
        self.assertIn("input_hash", record["admission"]["reason"])

    def test_system_bus_rejects_target_that_does_not_provide_socket(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.reports",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_wrong_target",
            audit_ref="audit:test:bus:wrong-target",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {},
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertEqual(record["admission"]["reason"], "target_module_does_not_provide_socket")

    def test_system_bus_publish_raises_for_rejected_contract_payload(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_bad_payload",
            audit_ref="audit:test:bus:bad-payload",
            payload={"project_id": "proj_1"},
        )

        with self.assertRaises(BusControllerError):
            bus.publish(message)

    def test_decision_council_contract_requires_sealed_upstream_envelopes(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.decision_council",
            contract_id="decision.council.evaluate.v1",
            socket_id="socket.decision.council",
            correlation_id="corr_decision_missing_inputs",
            audit_ref="audit:test:decision:missing-inputs",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertIn("contract_validation_failed", record["admission"]["reason"])
        self.assertIn("finance", record["admission"]["reason"])
        self.assertIn("readiness_gates", record["admission"]["reason"])
        self.assertIn("sector_intelligence", record["admission"]["reason"])

    def test_risk_register_contract_requires_independent_upstream_envelopes(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.risk_engine",
            contract_id="risk.register.build.v1",
            socket_id="socket.risk.register",
            correlation_id="corr_risk_missing_inputs",
            audit_ref="audit:test:risk:missing-inputs",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertIn("contract_validation_failed", record["admission"]["reason"])
        self.assertIn("finance", record["admission"]["reason"])
        self.assertIn("evidence_register", record["admission"]["reason"])
        self.assertIn("source_policy", record["admission"]["reason"])
        self.assertIn("readiness_gates", record["admission"]["reason"])

    def test_execution_plan_contract_requires_independent_upstream_envelopes(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.execution_engine",
            contract_id="execution.plan.build.v1",
            socket_id="socket.execution.plan",
            correlation_id="corr_execution_missing_inputs",
            audit_ref="audit:test:execution:missing-inputs",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertIn("contract_validation_failed", record["admission"]["reason"])
        self.assertIn("finance", record["admission"]["reason"])
        self.assertIn("decision_council", record["admission"]["reason"])
        self.assertIn("readiness_gates", record["admission"]["reason"])
        self.assertIn("risk_advisory_summary", record["admission"]["reason"])

    def test_report_snapshot_contract_requires_sealed_overview(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.reports",
            contract_id="report.snapshot.project.v1",
            socket_id="socket.report.snapshot",
            correlation_id="corr_report_missing_overview",
            audit_ref="audit:test:report:missing-overview",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertFalse(record["admission"]["accepted"])
        self.assertIn("contract_validation_failed", record["admission"]["reason"])
        self.assertIn("overview", record["admission"]["reason"])

    def test_decision_pack_contract_requires_saved_snapshot_and_report(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus = self.make_ready_bus()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.decision_pack",
            contract_id="decision.pack.project.v1",
            socket_id="socket.decision.pack",
            correlation_id="corr_decision_pack_missing_inputs",
            audit_ref="audit:test:decision-pack:missing-inputs",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
            },
        )

        record = bus.try_publish(message)

        self.assertFalse(record["delivered"])
        self.assertIn("snapshot_overview", record["admission"]["reason"])
        self.assertIn("snapshot_report", record["admission"]["reason"])

    def test_decision_pack_runtime_rejects_review_overlay_input(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.decision_pack",
            contract_id="decision.pack.project.v1",
            socket_id="socket.decision.pack",
            correlation_id="corr_decision_pack_forbidden_review",
            audit_ref="audit:test:decision-pack:forbidden-review",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "input_contract_id": "DecisionPackInputEnvelope.v1",
                "snapshot_overview": {},
                "snapshot_report": {},
                "reviews": [],
            },
        )

        with self.assertRaisesRegex(ModuleRuntimeError, "forbidden live or review inputs"):
            runtime.execute(message)

    def test_ai_integration_shell_routes_allowed_explanation_to_disabled_no_provider(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()

        execution = runtime.execute(self.ai_message())
        result = execution.output["ai_result"]

        self.assertEqual(result["status"], "disabled_no_provider")
        self.assertEqual(result["provider_registry"]["providers"], [])
        self.assertEqual(result["provider_registry"]["provider_count"], 0)
        self.assertEqual(result["provider_registry"]["status"], "DISABLED")
        self.assertEqual(result["provider_registry"]["policy"], "DENY_ALL")
        self.assertEqual(result["provider_registry"]["registration_decision_owner"], "policy_engine")
        self.assertEqual(result["routing"]["status"], "disabled_no_provider")
        self.assertFalse(result["routing"]["network_attempted"])
        self.assertEqual(result["human_review_gate"]["status"], "required_pending")
        self.assertIsNone(result["output"])
        self.assertFalse(result["audit_event"]["prompt_content_stored"])
        self.assertEqual(result["audit_event"]["event_type"], "ai_request_attempt")
        self.assertNotIn("prompt_text", execution.bus_record["message"]["payload"])

    def test_ai_integration_shell_rejects_finance_and_sovereign_ownership_before_routing(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = self.ai_message()
        message.payload["prompt_class"] = "financial_calculation"
        message.payload["requested_output_types"] = ["financial_result", "sovereign_verdict"]

        result = runtime.execute(message).output["ai_result"]

        self.assertEqual(result["status"], "rejected_governance")
        self.assertEqual(result["routing"]["status"], "skipped_governance_blocked")
        self.assertFalse(result["routing"]["network_attempted"])
        self.assertIn(
            "forbidden_prompt_class:financial_calculation",
            result["prompt_governance"]["reasons"],
        )
        self.assertIn(
            "forbidden_output_type:sovereign_verdict",
            result["prompt_governance"]["reasons"],
        )
        self.assertEqual(result["audit_event"]["outcome"], "rejected_governance")
        self.assertIsNotNone(result["security_audit_event"])
        self.assertEqual(result["security_audit_event"]["event_type"], "ai_request_rejected")
        self.assertEqual(result["security_audit_event"]["reason"], "prompt_governance_blocked")
        self.assertFalse(result["security_audit_event"]["prompt_content_stored"])
        self.assertNotIn("prompt_text", result["security_audit_event"]["metadata"])

    def test_ai_output_validation_rejects_numeric_legal_and_finance_truth_ownership(self) -> None:
        validation = OutputValidation().validate(
            {
                "owner_domain": "finance",
                "claims_numeric_truth": True,
                "controlled_numbers": [100],
                "legal_interpretation": "binding",
                "sovereign_verdict": "APPROVED",
            }
        )

        self.assertEqual(validation["status"], "rejected")
        self.assertIn("forbidden_owner_domain:finance", validation["violations"])
        self.assertIn("numeric_truth_claim_forbidden", validation["violations"])
        self.assertIn("legal_interpretation_forbidden", validation["violations"])
        self.assertIn("sovereign_verdict_forbidden", validation["violations"])
        self.assertFalse(validation["can_own_controlled_numbers"])

    def test_ai_provider_registry_cannot_register_provider(self) -> None:
        registry = ProviderRegistry()

        with self.assertRaisesRegex(AIIntegrationError, "provider_registration_denied_by_policy"):
            registry.register({"provider_id": "forbidden", "api_key": "must-not-be-stored"})

        snapshot = registry.snapshot()
        self.assertEqual(snapshot["providers"], [])
        self.assertEqual(snapshot["status"], "DISABLED")
        self.assertEqual(snapshot["policy"], "DENY_ALL")
        self.assertEqual(snapshot["registration_decision_owner"], "policy_engine")
        self.assertEqual(snapshot["security_audit"]["event_count"], 1)
        event = snapshot["security_audit"]["events"][0]
        self.assertEqual(event["event_type"], "ai_provider_registration_rejected")
        self.assertEqual(event["reason"], "provider_registration_denied_by_policy")
        self.assertNotIn("api_key", event["metadata"])

    def test_ai_security_audit_records_rejected_raw_prompt_metadata_only(self) -> None:
        shell = AIIntegrationShell()
        request = dict(self.ai_message().payload)
        request.pop("input_contract_id")
        request["prompt_text"] = "sensitive user prompt must not be stored"

        with self.assertRaisesRegex(AIIntegrationError, "ai_request_forbidden_fields:prompt_text"):
            shell.process(request)

        audit = shell.status()["security_audit"]
        self.assertEqual(audit["event_count"], 1)
        event = audit["events"][0]
        self.assertEqual(event["event_type"], "ai_request_rejected")
        self.assertEqual(event["reason"], "ai_request_forbidden_fields")
        self.assertEqual(event["metadata"]["forbidden_fields"], ["prompt_text"])
        self.assertFalse(event["prompt_content_stored"])
        self.assertNotIn("sensitive user prompt", str(event))

    def test_ai_security_audit_records_invalid_contract_and_human_review_bypass_attempts(self) -> None:
        adapter = AIIntegrationModuleAdapter()
        bad_contract_payload = self.ai_message().payload | {"input_contract_id": "ai.generate.v1"}

        with self.assertRaisesRegex(ModuleRuntimeError, "AI Integration requires AIIntegrationInputEnvelope.v1"):
            adapter.handle(bad_contract_payload)

        contract_audit = adapter.shell.status()["security_audit"]["events"][0]
        self.assertEqual(contract_audit["reason"], "invalid_ai_input_contract")
        self.assertEqual(contract_audit["metadata"]["received_input_contract_id"], "ai.generate.v1")

        shell = AIIntegrationShell()
        bypass_payload = dict(self.ai_message().payload)
        bypass_payload.pop("input_contract_id")
        bypass_payload["human_review_approved"] = True
        with self.assertRaisesRegex(AIIntegrationError, "ai_request_forbidden_fields:human_review_approved"):
            shell.process(bypass_payload)

        bypass_audit = shell.status()["security_audit"]["events"][0]
        self.assertEqual(bypass_audit["reason"], "ai_request_forbidden_fields")
        self.assertEqual(bypass_audit["metadata"]["forbidden_fields"], ["human_review_approved"])

    def test_architecture_runtime_status_reports_final_aas_acceptance(self) -> None:
        status = build_architecture_runtime_status()

        self.assertEqual(status["overall_status"], "passed")
        self.assertEqual(status["projection_type"], "read_only_runtime_projection")
        self.assertEqual(status["mutability"], "read_only_projection")
        self.assertEqual(status["allowed_methods"], ["GET"])
        self.assertEqual(status["forbidden_methods"], ["POST", "PATCH", "PUT", "DELETE"])
        self.assertEqual(status["ports"], {"frontend": 5194, "api": 8794})
        self.assertEqual(status["kernel"]["business_logic_owner"], "none")
        self.assertEqual(status["heart_controller"]["state"], "ready")
        self.assertEqual(status["bus_controller"]["state"], "ready")
        self.assertEqual(status["system_bus"]["state"], "ready")
        self.assertEqual(status["socket_contract_layer"]["state"], "enforcing")
        self.assertEqual(status["module_runtime"]["state"], "ready")
        self.assertEqual(status["snapshot_assembly"]["status"], "registered_runtime_wrapped")
        self.assertEqual(status["ai_integration_shell"]["state"], "disabled_governed")
        self.assertEqual(status["ai_integration_shell"]["provider_registry"]["provider_count"], 0)
        self.assertEqual(status["final_aas_acceptance"]["failed"], 0)
        self.assertTrue(all(row["passed"] for row in status["final_aas_acceptance"]["checks"]))
        self.assertFalse(status["guards"]["allows_runtime_mutation"])
        self.assertFalse(status["guards"]["allows_reboot"])
        self.assertFalse(status["guards"]["allows_registry_mutation"])
        self.assertFalse(status["guards"]["allows_provider_policy_mutation"])
        self.assertFalse(status["guards"]["allows_ai_activation"])
        self.assertFalse(status["guards"]["allows_module_registration"])
        self.assertFalse(status["guards"]["allows_heart_mutation"])
        self.assertFalse(status["guards"]["allows_bus_mutation"])
        self.assertFalse(status["guards"]["allows_socket_mutation"])

    def test_architecture_runtime_status_keeps_three_hearts_and_current_modules_visible(self) -> None:
        status = build_architecture_runtime_status()
        hearts = {row["role"]: row for row in status["heart_controller"]["hearts"]}
        handlers = set(status["module_runtime"]["registered_handlers"])

        self.assertEqual(hearts["primary"]["heart_id"], "M1")
        self.assertEqual(hearts["assist"]["heart_id"], "M2")
        self.assertEqual(hearts["reserve"]["heart_id"], "M3")
        self.assertTrue(all(row["controlled_by"] == "heart_controller" for row in hearts.values()))
        self.assertTrue(
            {
                "module.finance",
                "module.evidence_ledger",
                "module.sector_intelligence",
                "module.decision_council",
                "module.risk_engine",
                "module.execution_engine",
                "module.snapshot_assembly",
                "module.reports",
                "module.decision_pack",
                "module.ai_integration",
            }.issubset(handlers)
        )

    def test_architecture_runtime_status_guards_no_product_expansion_external_fetch_or_ai_provider(self) -> None:
        status = build_architecture_runtime_status()

        self.assertFalse(status["guards"]["product_features_added"])
        self.assertFalse(status["guards"]["new_engines_added"])
        self.assertFalse(status["guards"]["external_fetch_enabled"])
        self.assertFalse(status["guards"]["ai_provider_enabled"])
        self.assertFalse(status["snapshot_assembly"]["recalculates"])
        self.assertFalse(status["snapshot_assembly"]["persists"])
        self.assertFalse(status["snapshot_assembly"]["external_fetch_enabled"])
        self.assertFalse(status["snapshot_assembly"]["ai_enabled"])
        self.assertFalse(status["ai_integration_shell"]["provider_registry"]["external_network_enabled"])

    def test_socket_contract_layer_requires_bootstrap_before_verification(self) -> None:
        registry = bootstrap_default_registry()
        layer = SocketContractLayer(registry)
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_socket_bootstrap",
            audit_ref="audit:test:socket:bootstrap",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {},
            },
        )

        with self.assertRaises(SocketContractError):
            layer.verify_message(message)

    def test_socket_contract_layer_accepts_socket_first_module_second_message(self) -> None:
        registry = bootstrap_default_registry()
        layer = SocketContractLayer(registry)
        status = layer.bootstrap()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_socket_accept",
            audit_ref="audit:test:socket:accept",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {},
            },
        )

        check = layer.verify_message(message)

        self.assertEqual(status["state"], "enforcing")
        self.assertTrue(status["guards"]["socket_first_module_second"])
        self.assertTrue(check.passed)
        self.assertEqual(check.reason, "accepted")
        self.assertFalse(layer.status()["guards"]["executes_business_logic"])

    def test_socket_contract_layer_rejects_socket_contract_mismatch(self) -> None:
        registry = bootstrap_default_registry()
        layer = SocketContractLayer(registry)
        layer.bootstrap()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="report.snapshot.project.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_socket_mismatch",
            audit_ref="audit:test:socket:mismatch",
            payload={"snapshot_id": "snap_1", "run_id": "run_1"},
        )

        check = layer.verify_message(message)

        self.assertFalse(check.passed)
        self.assertIn("socket_contract_mismatch", check.reason)

    def test_socket_contract_layer_rejects_payload_contract_mismatch(self) -> None:
        registry = bootstrap_default_registry()
        layer = SocketContractLayer(registry)
        layer.bootstrap()
        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_socket_payload",
            audit_ref="audit:test:socket:payload",
            payload={"project_id": "proj_1", "run_id": "run_1"},
        )

        check = layer.verify_message(message)

        self.assertFalse(check.passed)
        self.assertIn("contract_validation_failed", check.reason)

    def test_module_runtime_requires_ready_bus_before_bootstrap(self) -> None:
        kernel = AASKernel()
        kernel.boot()
        heart_controller = HeartController(kernel)
        heart_controller.bootstrap()
        bus_controller = BusController(kernel, heart_controller)
        bus_controller.bootstrap()
        bus = SystemBus(bus_controller)

        with self.assertRaises(ModuleRuntimeError):
            ModuleRuntime(kernel, bus).bootstrap()

    def test_module_runtime_rejects_execution_without_registered_handler(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus, runtime = self.make_ready_module_runtime()
        message = self.finance_message()

        with self.assertRaises(ModuleRuntimeError):
            runtime.execute(message)

    def test_module_runtime_executes_finance_after_bus_and_socket_delivery(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = self.finance_message()

        result = runtime.execute(message).to_public()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["module_id"], "module.finance")
        self.assertEqual(result["bus_record"]["message"]["contract_id"], "finance.calculate.v1")
        self.assertEqual(result["output"]["contract_id"], "finance.result.v1")
        self.assertTrue(result["bus_record"]["delivered"])
        self.assertTrue(result["guards"]["executed_after_bus_delivery"])
        self.assertFalse(result["guards"]["external_fetch_enabled"])
        self.assertFalse(result["guards"]["ai_enabled"])
        self.assertEqual(result["output"]["finance"]["status"], "ready")
        self.assertEqual(result["output"]["finance"]["baseline"]["revenue"], 136000.0)
        self.assertEqual(bus.status()["delivered_count"], 1)

    def test_project_run_workflow_is_registered_behind_bus_and_socket(self) -> None:
        kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        contract_ids = {row["contract_id"] for row in kernel.registry.snapshot()["contracts"]}
        socket_ids = {row["socket_id"] for row in kernel.registry.snapshot()["sockets"]}
        module_ids = {row["module_id"] for row in kernel.registry.snapshot()["modules"]}

        self.assertIn("ProjectRunHttpRequest.v1", contract_ids)
        self.assertIn("project.run.request.v1", contract_ids)
        self.assertIn("project.run.workflow.v1", contract_ids)
        self.assertIn("project.run.completed.v1", contract_ids)
        self.assertIn("socket.project.run", socket_ids)
        self.assertIn("module.project_run_workflow", module_ids)
        self.assertIn("module.project_run_workflow", runtime.status()["registered_handlers"])

    def test_project_run_workflow_idempotency_replays_without_rebuilding(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        store = ProjectRunIdempotencyStore()
        workflow = ProjectRunWorkflow(
            runtime,
            store,
            source_module_id="aas.heart.M1",
            heart_assignment={"assignments": [{"heart_id": "M1"}], "mode": "primary_only"},
        )
        request = normalize_project_run_http_request(
            "proj_1",
            {"scenario_id": "baseline", "idempotency_key": "idem-project-run-1"},
        )
        build_calls: list[str] = []
        save_calls: list[str] = []

        def build_once(run_envelope: ProjectRunEnvelope) -> tuple[dict[str, object], dict[str, object]]:
            build_calls.append("build")
            return (
                {
                    "project": {"project_id": "proj_1"},
                    "run": {"run_id": run_envelope.run_id},
                    "snapshot": {"snapshot_id": run_envelope.snapshot_id},
                },
                {"snapshot_id": run_envelope.snapshot_id},
            )

        def save_once(overview: dict[str, object], report: dict[str, object]) -> dict[str, str]:
            save_calls.append("save")
            return {"run_id": str(overview["run"]["run_id"]), "snapshot_id": str(report["snapshot_id"])}

        first = workflow.run(request, build=build_once, save=save_once)
        replayed = workflow.run(
            request,
            build=lambda _run_envelope: self.fail("idempotency replay must not rebuild"),
            save=lambda _overview, _report: self.fail("idempotency replay must not save"),
        )

        self.assertFalse(first.idempotency_replayed)
        self.assertTrue(replayed.idempotency_replayed)
        self.assertEqual(first.run_id, replayed.run_id)
        self.assertEqual(first.snapshot_id, replayed.snapshot_id)
        self.assertEqual(first.workflow["assigned_source_module_id"], "aas.heart.M1")
        self.assertEqual(first.workflow["heart_assignment"]["assignments"][0]["heart_id"], "M1")
        self.assertEqual(first.workflow["pipeline_policy_id"], "project-run-pipeline.v1")
        self.assertEqual(build_calls, ["build"])
        self.assertEqual(save_calls, ["save"])

    def test_module_runtime_does_not_execute_rejected_message(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        bad_message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_runtime_bad_payload",
            audit_ref="audit:test:runtime:bad-payload",
            payload={"project_id": "proj_1"},
        )

        with self.assertRaises(Exception):
            runtime.execute(bad_message)

        self.assertEqual(runtime.status()["execution_count"], 0)

    def test_snapshot_assembly_runtime_builds_immutable_run_scoped_snapshot(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()

        result = runtime.execute(self.snapshot_assembly_message()).output["assembled_snapshot"]

        self.assertEqual(result["assembly_contract_id"], "snapshot.assemble.v1")
        self.assertEqual(result["snapshot_id"], "snap_1")
        self.assertEqual(result["run_id"], "run_1")
        self.assertTrue(result["immutable"])
        self.assertEqual(set(result["module_outputs"]), set(REQUIRED_MODULE_OUTPUTS))
        self.assertEqual(len(result["lineage"]), len(REQUIRED_MODULE_OUTPUTS))
        self.assertEqual(set(result["correlation_map"]), set(REQUIRED_MODULE_OUTPUTS))
        self.assertEqual(len(result["content_hash"]), 64)
        self.assertEqual(len(result["integrity_hash"]), 64)
        self.assertFalse(result["external_fetch_enabled"])
        self.assertFalse(result["ai_enabled"])

    def test_snapshot_assembly_fails_closed_when_required_output_is_missing(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = self.snapshot_assembly_message()
        message.payload["sealed_outputs"] = message.payload["sealed_outputs"][:-1]

        with self.assertRaisesRegex(ModuleRuntimeError, "required sealed module outputs missing"):
            runtime.execute(message)

        self.assertEqual(runtime.status()["execution_count"], 0)

    def test_snapshot_assembly_rejects_tampered_sealed_output(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = self.snapshot_assembly_message()
        message.payload["sealed_outputs"][0]["output"]["finance"] = {"status": "tampered"}

        with self.assertRaisesRegex(ModuleRuntimeError, "integrity check failed"):
            runtime.execute(message)

        self.assertEqual(runtime.status()["execution_count"], 0)

    def test_snapshot_assembly_rejects_run_identity_mismatch(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        message = self.snapshot_assembly_message()
        message.payload["sealed_outputs"][0]["run_id"] = "run_wrong"

        with self.assertRaisesRegex(ModuleRuntimeError, "run_id mismatch"):
            runtime.execute(message)

        self.assertEqual(runtime.status()["execution_count"], 0)

    def test_run_scoped_runtime_seals_six_outputs_then_assembles_once(self) -> None:
        _kernel, _heart_controller, _bus_controller, bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        session = RunScopedModuleRuntime(
            runtime,
            project_id="proj_1",
            run_id="run_1",
            snapshot_id="snap_1",
        )
        socket_by_output = {
            "finance_result": "socket.finance.evaluate",
            "evidence_ledger": "socket.evidence.ledger",
            "sector_intelligence": "socket.sector.intelligence",
            "decision_result": "socket.decision.council",
            "risk_result": "socket.risk.register",
            "execution_result": "socket.execution.plan",
        }
        command_contract_by_output = {
            "finance_result": "finance.calculate.v1",
            "evidence_ledger": "evidence.ledger.build.v1",
            "sector_intelligence": "sector.intelligence.build.v1",
            "decision_result": "decision.council.evaluate.v1",
            "risk_result": "risk.register.build.v1",
            "execution_result": "execution.plan.build.v1",
        }
        common_payload = {
            "project_id": "proj_1",
            "run_id": "run_1",
            "snapshot_id": "snap_1",
            "inputs": {},
            "input_contract_id": "TestInputEnvelope.v1",
            "finance": {},
            "blockers": [],
            "readiness_gates": {},
            "sector_intelligence": {},
            "evidence_register": {},
            "source_records": [],
            "transformations": [],
            "source_policy": {},
            "decision_council": {},
            "risk_advisory_summary": {},
        }
        for output_key, (module_id, contract_id) in REQUIRED_MODULE_OUTPUTS.items():
            runtime.register_handler(
                module_id,
                lambda payload, module_id=module_id, contract_id=contract_id, output_key=output_key: {
                    "module_id": module_id,
                    "contract_id": contract_id,
                    "project_id": payload["project_id"],
                    "run_id": payload["run_id"],
                    "snapshot_id": payload["snapshot_id"],
                    "result": {"output_key": output_key},
                },
            )
            session.execute_and_seal(
                output_key,
                BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id=module_id,
                    contract_id=command_contract_by_output[output_key],
                    socket_id=socket_by_output[output_key],
                    correlation_id=f"corr:run_1:{output_key}",
                    audit_ref=f"audit:snap_1:{output_key}",
                    operation_id=session.operation_id,
                    idempotency_key=session.idempotency_key,
                    input_hash=session.input_hash,
                    payload=dict(common_payload),
                ),
            )

        result = session.assemble(
            project_context={"name": "One runtime"},
            readiness_state={"status": "ready"},
            blockers=[],
        ).output["assembled_snapshot"]

        self.assertEqual(set(session.sealed_outputs), set(REQUIRED_MODULE_OUTPUTS))
        self.assertEqual(session.sealed_outputs["finance_result"]["producer_contract_id"], "finance.result.v1")
        self.assertEqual(session.sealed_outputs["execution_result"]["producer_contract_id"], "execution.plan.v1")
        self.assertEqual(runtime.status()["execution_count"], 7)
        self.assertEqual(bus.status()["delivered_count"], 7)
        self.assertEqual(result["snapshot_id"], "snap_1")
        with self.assertRaisesRegex(ModuleRuntimeError, "already been assembled"):
            session.assemble(project_context={}, readiness_state={}, blockers=[])

    def test_run_scoped_runtime_rejects_message_envelope_mismatch(self) -> None:
        _kernel, _heart_controller, _bus_controller, _bus, runtime = self.make_ready_module_runtime()
        runtime.register_default_handlers()
        session = RunScopedModuleRuntime(
            runtime,
            project_id="proj_1",
            run_id="run_1",
            snapshot_id="snap_1",
            operation_id="op_run_1",
            idempotency_key="idem_run_1",
            input_hash="hash_run_1",
        )

        message = BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr:run_1:finance",
            audit_ref="audit:snap_1:finance",
            operation_id="op_other",
            idempotency_key=session.idempotency_key,
            input_hash=session.input_hash,
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {},
            },
        )

        with self.assertRaisesRegex(ModuleRuntimeError, "operation_id mismatch"):
            session.execute_and_seal("finance_result", message)

    def make_ready_bus(self) -> tuple[AASKernel, HeartController, BusController, SystemBus]:
        kernel = AASKernel()
        kernel.boot()
        heart_controller = HeartController(kernel)
        heart_controller.bootstrap()
        bus_controller = BusController(kernel, heart_controller)
        bus_controller.bootstrap()
        bus = SystemBus(bus_controller)
        bus.bootstrap()
        return kernel, heart_controller, bus_controller, bus

    def make_ready_module_runtime(self) -> tuple[AASKernel, HeartController, BusController, SystemBus, ModuleRuntime]:
        kernel, heart_controller, bus_controller, bus = self.make_ready_bus()
        runtime = ModuleRuntime(kernel, bus)
        runtime.bootstrap()
        return kernel, heart_controller, bus_controller, bus, runtime

    def finance_message(self) -> BusMessage:
        return BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id="corr_runtime_finance",
            audit_ref="audit:test:runtime:finance",
            payload={
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "inputs": {
                    "startup_cost": 250000,
                    "monthly_fixed_cost": 62000,
                    "unit_price": 85,
                    "variable_cost": 34,
                    "monthly_units": 1600,
                    "annual_discount_rate": 0.10,
                    "working_capital_months": 2,
                },
            },
        )

    def snapshot_assembly_message(self) -> BusMessage:
        project_id = "proj_1"
        run_id = "run_1"
        snapshot_id = "snap_1"
        sealed_outputs = []
        for output_key, (module_id, contract_id) in REQUIRED_MODULE_OUTPUTS.items():
            module_output = {
                "module_id": module_id,
                "contract_id": contract_id,
                "project_id": project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "result": {"status": "ready", "output_key": output_key},
                "external_fetch_enabled": False,
                "ai_enabled": False,
            }
            sealed_outputs.append(
                seal_module_output(
                    output_key=output_key,
                    producer_module_id=module_id,
                    producer_contract_id=contract_id,
                    producer_contract_version="1.0.0-local-core",
                    project_id=project_id,
                    run_id=run_id,
                    snapshot_id=snapshot_id,
                    message_id=f"msg_{output_key}",
                    correlation_id=f"corr:{run_id}:{output_key}",
                    audit_ref=f"audit:{snapshot_id}:{output_key}",
                    produced_at="2026-07-18T00:00:00+00:00",
                    output=module_output,
                )
            )
        return BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.snapshot_assembly",
            contract_id="snapshot.assemble.v1",
            socket_id="socket.snapshot.assemble",
            correlation_id=f"corr:{run_id}:snapshot-assembly",
            audit_ref=f"audit:{snapshot_id}:snapshot-assembly",
            payload={
                "project_id": project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "input_contract_id": "SnapshotAssemblyInputEnvelope.v1",
                "sealed_outputs": sealed_outputs,
                "project_context": {"name": "Assembly parity project"},
                "readiness_state": {"status": "warning"},
                "blockers": [{"code": "EVIDENCE_REVIEW_PENDING"}],
            },
        )

    def ai_message(self) -> BusMessage:
        return BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.ai_integration",
            contract_id="ai.integration.request.v1",
            socket_id="socket.ai.integration",
            correlation_id="corr:run_1:ai-shell",
            audit_ref="audit:snap_1:ai-shell",
            payload={
                "request_id": "ai_req_1",
                "project_id": "proj_1",
                "run_id": "run_1",
                "snapshot_id": "snap_1",
                "input_contract_id": "AIIntegrationInputEnvelope.v1",
                "purpose": "explain_saved_snapshot",
                "prompt_class": "explanation",
                "prompt_template_id": "explain-saved-snapshot-v1",
                "prompt_hash": "sha256:local-template-only",
                "requested_output_types": ["narrative_explanation"],
                "context_refs": ["snap_1"],
            },
        )


if __name__ == "__main__":
    unittest.main()
