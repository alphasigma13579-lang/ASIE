"""Dark, explicitly injected lifecycle service; no environment or HTTP activation.

The store lock spans preparation, journaling and external effects. Production
cutover must exclude the legacy JSON writer. Recovery verification is supplied
by a trusted server adapter; absent settled/parity proof, reads remain blocked.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from backend.provider_security_control_plane import TrustedProviderScope
from backend.public_corpus_store import CorpusStoreError, _json
from backend.public_knowledge import (
    PublicKnowledgeSync, _EVIDENCE_REQUIRED_FIELDS, _batched, _safe_failure,
    _utc_now, build_feasibility_evidence_context,
    build_unavailable_feasibility_evidence_context,
)

_WORKLOAD = "public-knowledge-sync"


def _authorize(scope):
    if type(scope) is not TrustedProviderScope:
        raise CorpusStoreError("corpus_scope_denied")
    try:
        TrustedProviderScope.require_platform_workload(scope, _WORKLOAD)
    except PermissionError:
        raise CorpusStoreError("corpus_scope_denied") from None


def _projection(corpus):
    records = {}
    for source in corpus["sources"].values():
        if source.get("status") != "active":
            continue
        for record in source.get("records", []):
            identifier = record["_id"]
            if identifier in records:
                raise CorpusStoreError("corpus_projection_invalid")
            records[identifier] = deepcopy(record)
    return records


class _Plan(PublicKnowledgeSync):
    def __init__(self, *, corpus, tavily, scope, now):
        super().__init__(tavily=tavily, pinecone=None, scope=scope,
                         corpus_path=Path("."), now=now)
        self.corpus = deepcopy(corpus)
        self.commands = []

    def _load(self):
        return deepcopy(self.corpus)

    def _save(self, corpus):
        self.corpus = deepcopy(corpus)

    def _upsert(self, records):
        for batch in _batched(records, 100):
            self.commands.append(("upsert", deepcopy(list(batch))))
        return len(records)

    def _delete_ids(self, record_ids):
        for batch in _batched(record_ids, 1000):
            self.commands.append(("delete", list(batch)))
        return len(record_ids)


class PublicKnowledgeLifecycle:
    """Explicit platform service. Never construct from customer request options.

    verifier.settled(operation_id) proves prior requests cannot apply late.
    verifier.matches(operation_id, expected, absent) proves exact compensated
    projection for affected identifiers, including absence. Neither method has
    a permissive default. A timeout, eventual-consistency guess or fixed sleep
    is not proof. No live verifier is installed by this module.
    """

    def __init__(self, *, store, scope, tavily, pinecone, verifier=None, project_organization_resolver=None, now=_utc_now):
        _authorize(scope)
        self.store, self.scope = store, scope
        self.tavily, self.pinecone = tavily, pinecone
        self.verifier, self.now = verifier, now
        self.project_organization_resolver = project_organization_resolver

    def run(self, registry, *, key, epoch):
        return self._execute("sync", registry, key=key, epoch=epoch)

    def delete_source(self, source_id, *, key, epoch):
        return self._execute("delete", source_id, key=key, epoch=epoch)

    def restore_source(self, source_id, *, key, epoch):
        return self._execute("restore", source_id, key=key, epoch=epoch)

    def reindex(self, *, key, epoch):
        return self._execute("reindex", None, key=key, epoch=epoch)

    def _effect(self, action, values):
        if action == "upsert":
            self.pinecone.upsert_public_knowledge(scope=self.scope, records=values)
        else:
            self.pinecone.delete_public_knowledge(scope=self.scope, record_ids=values)

    def _execute(self, kind, value, *, key, epoch):
        _authorize(self.scope)
        request = {"kind": kind, "value": deepcopy(value)}
        _json(request)
        with self.store.session(self.scope) as session:
            replay = session.lookup(key=key, epoch=epoch, request=request)
            if replay is not None:
                return replay
            snap = session.snapshot()
            plan = _Plan(corpus=snap["corpus"], tavily=self.tavily,
                         scope=self.scope, now=self.now)
            try:
                if kind == "sync":
                    result = plan.run(request["value"])
                elif kind == "delete":
                    result = plan.delete_source(request["value"])
                elif kind == "restore":
                    result = plan.restore_source(request["value"])
                else:
                    result = plan.reindex()
            except Exception as exc:
                # No index effects have occurred. Persist this terminal outcome
                # as well so retries cannot silently refetch under the same key.
                result = {"status": "failed", "error": _safe_failure(exc)}
                plan.corpus = deepcopy(snap["corpus"])
                plan.commands = []
            _projection(plan.corpus)
            _json(result)
            operation = session.begin(
                key=key, epoch=epoch, kind=kind, request=request,
                intent={"command_count": len(plan.commands)},
                expected_revision=snap["revision"], after=plan.corpus)
            try:
                for action, values in plan.commands:
                    identifiers = [r["_id"] for r in values] if action == "upsert" else values
                    session.record_step(operation.operation_id, action=action,
                                        record_ids=identifiers)
                    self._effect(action, values)
                session.commit(operation.operation_id, result=result)
            except Exception:
                # A commit acknowledgement may fail after commit. Never undo a
                # committed projection; re-open/replay resolves the outcome.
                pending = session.pending()
                if not pending:
                    raise CorpusStoreError("corpus_outcome_requires_replay") from None
                session.mark_recovery_required(operation.operation_id)
                return self._recover(session, pending[0])
            return result

    def recover(self):
        _authorize(self.scope)
        with self.store.session(self.scope) as session:
            pending = session.pending()
            if not pending:
                return {"status": "no_recovery_needed"}
            return self._recover(session, pending[0])

    def _recover(self, session, pending):
        blocked = {"status": "recovery_required",
                   "message": "تعذر إثبات اتساق المعرفة. أوقف الاستخدام واطلب فحص الاستعادة."}
        operation_id = pending["operation_id"]
        try:
            if self.verifier is None or self.verifier.settled(operation_id) is not True:
                return blocked
            before = _projection(pending["before"])
            affected = {identifier for step in pending["steps"]
                        for identifier in step["record_ids"]}
            expected = {key: before[key] for key in sorted(affected) if key in before}
            absent = sorted(affected - before.keys())
            for action, values, size in (
                    ("upsert", list(expected.values()), 100), ("delete", absent, 1000)):
                for batch in _batched(values, size):
                    batch = list(batch)
                    identifiers = [r["_id"] for r in batch] if action == "upsert" else batch
                    session.record_step(operation_id, action=action,
                                        record_ids=identifiers, recovery=True)
                    self._effect(action, batch)
            # The first proof covered original requests only. Compensation
            # creates new requests; prove those terminal before opening reads.
            if self.verifier.settled(operation_id) is not True:
                return blocked
            if self.verifier.matches(operation_id, deepcopy(expected), list(absent)) is not True:
                return blocked
            result = {"status": "failed_compensated",
                      "message": "لم تكتمل العملية. احتُفظ بالمعرفة السابقة؛ أعد المحاولة بطلب جديد."}
            session.finish_compensation(operation_id, result=result)
            return result
        except Exception:
            return blocked

    def evidence(self, *, scope, query, top_k=8):
        """Tenant-scoped read; query is never journalled or stored."""
        if type(scope) is not TrustedProviderScope:
            raise CorpusStoreError("corpus_scope_denied")
        try:
            TrustedProviderScope.request_context(scope, "search_public_knowledge")
            if (scope.preflight or scope.organization_id == "__platform__"
                    or self.project_organization_resolver is None
                    or self.project_organization_resolver(scope.project_id) != scope.organization_id):
                raise PermissionError
        except Exception:
            # Resolver failures deny access without exposing backing-store details.
            raise CorpusStoreError("corpus_scope_denied") from None
        if type(query) is not str or not 1 <= len(query.strip()) <= 2000:
            raise CorpusStoreError("corpus_request_invalid")
        if type(top_k) is not int or not 1 <= top_k <= 50:
            raise CorpusStoreError("corpus_request_invalid")
        try:
            with self.store.session(self.scope) as session:
                before = session.snapshot()
                if before["recovery_required"]:
                    return self._unavailable()
            response = self.pinecone.search_public_knowledge(scope=scope, query=query, top_k=top_k)
            with self.store.session(self.scope) as session:
                after = session.snapshot()
                if (after["recovery_required"] or before["restore_epoch"] != after["restore_epoch"]
                        or before["revision"] != after["revision"]):
                    return self._unavailable()
                canonical = _projection(after["corpus"])
                hits = response["payload"]["result"]["hits"]
                if type(hits) is not list or len(hits) > top_k:
                    return self._unavailable()
                for hit in hits:
                    record = canonical.get(hit.get("_id"))
                    fields = hit.get("fields")
                    if record is None or type(fields) is not dict:
                        return self._unavailable()
                    if any(fields.get(name) != record.get(name) for name in _EVIDENCE_REQUIRED_FIELDS):
                        return self._unavailable()
                return build_feasibility_evidence_context(response, as_of=self.now())
        except Exception:
            return self._unavailable()

    def _unavailable(self):
        return build_unavailable_feasibility_evidence_context(
            "public_knowledge_temporarily_unavailable", as_of=self.now())
