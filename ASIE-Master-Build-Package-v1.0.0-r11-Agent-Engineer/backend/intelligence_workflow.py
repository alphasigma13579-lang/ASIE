"""Governed offline Pre-Run workflow; it never assembles or mutates a Snapshot."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable

from backend.snapshot_assembly import canonical_hash

WORKFLOW_STATES = {"DRAFT", "VALIDATING", "INTEGRITY_LOCKED", "REVIEW_PENDING", "COMPLETED", "FAILED"}


@dataclass
class ContextBuildResult:
    context_build_id: str
    idempotency_key: str
    state: str = "DRAFT"
    attempts: int = 0
    audit: list[dict[str, Any]] = field(default_factory=list)
    output: dict[str, Any] | None = None
    error: str | None = None


class IntelligenceContextWorkflow:
    def __init__(self, *, timeout_seconds: float = 5.0, max_retries: int = 2, audit_sink: Callable[[dict[str, Any]], None] | None = None):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.audit_sink = audit_sink
        self._completed: dict[tuple[str, str], ContextBuildResult] = {}

    def _record(self, result: ContextBuildResult, action: str, outcome: str, reason: str = "") -> None:
        event = {"action": action, "outcome": outcome, "reason": reason, "context_build_id": result.context_build_id, "snapshot_mutation": False, "external_fetch_enabled": False}
        result.audit.append(event)
        if self.audit_sink:
            self.audit_sink(event)

    def execute(self, *, organization_id: str, project_id: str, context_build_id: str, idempotency_key: str, builder: Callable[[], dict[str, Any]]) -> ContextBuildResult:
        key = (organization_id, idempotency_key)
        if key in self._completed:
            replay = self._completed[key]
            replay.audit.append({"action": "context_build.replay", "outcome": "replayed", "context_build_id": replay.context_build_id, "snapshot_mutation": False})
            return replay
        result = ContextBuildResult(context_build_id, idempotency_key)
        started = monotonic()
        self._record(result, "context_build.start", "accepted")
        try:
            result.state = "VALIDATING"
            for attempt in range(self.max_retries + 1):
                result.attempts = attempt + 1
                try:
                    output = builder()
                    if monotonic() - started > self.timeout_seconds:
                        raise TimeoutError("context_build_timeout")
                    if not isinstance(output, dict) or not output:
                        raise ValueError("context_build_empty_output")
                    output = dict(output) | {"organization_id": organization_id, "project_id": project_id, "context_build_id": context_build_id}
                    output["output_hash"] = canonical_hash(output)
                    result.output = output
                    result.state = "INTEGRITY_LOCKED"
                    self._record(result, "context_build.integrity_lock", "locked")
                    result.state = "REVIEW_PENDING"
                    self._record(result, "context_build.review_pending", "awaiting_review")
                    self._completed[key] = result
                    return result
                except (TimeoutError, OSError) as exc:
                    if attempt >= self.max_retries:
                        raise
                    self._record(result, "context_build.retry", "bounded_retry", str(exc))
        except Exception as exc:
            result.state = "FAILED"
            result.error = str(exc)
            self._record(result, "context_build.fail", "fail_closed", result.error)
            return result
