# قائمة تنفيذ التصحيح

## المرحلة A — عقود التشغيل

- [ ] تثبيت `project.run.request.v1`
- [ ] تثبيت `project.run.workflow.v1`
- [ ] فصل command/result contracts
- [ ] تثبيت message envelope
- [ ] تثبيت idempotency semantics

## المرحلة B — Project Run Workflow

- [ ] لا Direct Calls
- [ ] dispatch حصريًا عبر Bus/Socket
- [ ] إدارة dependency graph
- [ ] جمع sealed outputs
- [ ] عدم بدء مرحلة تعتمد على output فاشل

## المرحلة C — Snapshot

- [ ] integrity validator
- [ ] run_id consistency
- [ ] output hashes
- [ ] lineage
- [ ] atomic transaction
- [ ] rollback كامل
- [ ] post-write verification
- [ ] duplicate commit guard

## المرحلة D — Projections

- [ ] Report من Snapshot فقط
- [ ] Decision Pack من Snapshot فقط
- [ ] استقلال Report عن Decision Pack
- [ ] retry مستقل
- [ ] no recalculation

## المرحلة E — Audit

- [ ] accepted events
- [ ] rejected events
- [ ] metadata only
- [ ] no secrets/raw prompts

## المرحلة F — Acceptance

- [ ] تنفيذ اختبارات `AAS-RUN-001` إلى `AAS-RUN-025`
- [ ] حفظ Evidence Matrix
- [ ] عدم إعلان Runtime Freeze قبل نجاحها
