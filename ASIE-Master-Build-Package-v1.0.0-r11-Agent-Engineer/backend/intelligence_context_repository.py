"""Local persistence adapter for ACR-AIA-02, isolated from the frozen run path."""
from __future__ import annotations

import sqlite3
from typing import Any

from backend.contracts import json_dumps, json_loads, now_iso
from backend.intelligence_approval import ApprovalReceipt, ReviewOverlay
from backend.intelligence_context import ContextComponent, IntelligenceContext, idempotency_fingerprint
from backend.intelligence_authorization import authorize_intelligence_action, AuditSink
from backend.identity import Principal


class IntelligenceContextRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        conflict = False
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS intelligence_contexts (
              context_build_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
              project_id TEXT NOT NULL, context_hash TEXT NOT NULL, state TEXT NOT NULL,
              version INTEGER NOT NULL, payload_json TEXT NOT NULL,
              idempotency_fingerprint TEXT NOT NULL UNIQUE, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS intelligence_review_overlays (
              review_overlay_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
              project_id TEXT NOT NULL, context_build_id TEXT NOT NULL,
              overlay_hash TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS intelligence_approval_receipts (
              approval_receipt_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
              project_id TEXT NOT NULL, context_build_id TEXT NOT NULL,
              receipt_hash TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_aia_context_tenant
              ON intelligence_contexts (organization_id, project_id);
            """)
        db.close()

    @staticmethod
    def _context(payload: dict[str, Any]) -> IntelligenceContext:
        components = [ContextComponent(**item) for item in payload.pop("components", [])]
        return IntelligenceContext(components=components, **payload)

    def create_context(self, context: IntelligenceContext) -> IntelligenceContext:
        data = context.__dict__.copy()
        data["components"] = [component.as_dict() for component in context.components]
        with sqlite3.connect(self.db_path) as db:
            try:
                db.execute("INSERT INTO intelligence_contexts VALUES (?,?,?,?,?,?,?,?,?)", (
                    context.context_build_id, context.organization_id, context.project_id,
                    context.context_hash, context.state, context.version, json_dumps(data),
                    idempotency_fingerprint(context.organization_id, context.project_id, context.idempotency_key), context.updated_at))
            except sqlite3.IntegrityError as exc:
                raise ValueError("context_idempotency_or_duplicate") from exc
        db.close()
        return context

    def create_context_authorized(self, context: IntelligenceContext, principal: Principal, audit_sink: AuditSink, correlation_id: str | None = None) -> IntelligenceContext:
        authorize_intelligence_action(principal, organization_id=context.organization_id, project_id=context.project_id, permission="project.edit", action="aia.context.create", target_id=context.context_build_id, audit_sink=audit_sink, correlation_id=correlation_id)
        return self.create_context(context)

    def get_context(self, context_build_id: str, organization_id: str, project_id: str) -> IntelligenceContext | None:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT payload_json FROM intelligence_contexts WHERE context_build_id=? AND organization_id=? AND project_id=?", (context_build_id, organization_id, project_id)).fetchone()
        db.close()
        return self._context(json_loads(row["payload_json"])) if row else None

    def update_context(self, context: IntelligenceContext, expected_version: int) -> IntelligenceContext:
        context.updated_at = now_iso()
        data = context.__dict__.copy()
        data["components"] = [component.as_dict() for component in context.components]
        with sqlite3.connect(self.db_path) as db:
            result = db.execute("UPDATE intelligence_contexts SET context_hash=?, state=?, version=?, payload_json=?, updated_at=? WHERE context_build_id=? AND organization_id=? AND project_id=? AND version=?", (
                context.context_hash, context.state, context.version, json_dumps(data), context.updated_at,
                context.context_build_id, context.organization_id, context.project_id, expected_version))
            if result.rowcount != 1:
                conflict = True
        db.close()
        if conflict:
            raise RuntimeError("context_optimistic_version_conflict")
        return context

    def update_context_authorized(self, context: IntelligenceContext, expected_version: int, principal: Principal, audit_sink: AuditSink, correlation_id: str | None = None) -> IntelligenceContext:
        authorize_intelligence_action(principal, organization_id=context.organization_id, project_id=context.project_id, permission="project.edit", action="aia.context.update", target_id=context.context_build_id, audit_sink=audit_sink, correlation_id=correlation_id)
        return self.update_context(context, expected_version)

    def save_review(self, organization_id: str, project_id: str, overlay: ReviewOverlay) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO intelligence_review_overlays VALUES (?,?,?,?,?,?)", (overlay.review_overlay_id, organization_id, project_id, overlay.intelligence_context_id, overlay.review_overlay_hash, json_dumps(overlay.__dict__)))
        db.close()

    def save_review_authorized(self, organization_id: str, project_id: str, overlay: ReviewOverlay, principal: Principal, audit_sink: AuditSink, correlation_id: str | None = None) -> None:
        authorize_intelligence_action(principal, organization_id=organization_id, project_id=project_id, permission="review.write", action="aia.review.save", target_id=overlay.review_overlay_id, audit_sink=audit_sink, correlation_id=correlation_id)
        self.save_review(organization_id, project_id, overlay)

    def save_receipt(self, receipt: ApprovalReceipt) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO intelligence_approval_receipts VALUES (?,?,?,?,?,?)", (receipt.approval_receipt_id, receipt.organization_id, receipt.project_id, receipt.intelligence_context_id, receipt.approval_receipt_hash, json_dumps(receipt.__dict__)))
        db.close()
