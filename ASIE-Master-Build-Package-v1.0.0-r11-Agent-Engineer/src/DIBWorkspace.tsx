import { useEffect, useMemo, useState } from "react";
import {
  compareSnapshots,
  createProject,
  fetchProjectRuns,
  fetchProjects,
  runProject,
  updateProject,
} from "./api";
import type { BlueprintItem, Project, ProjectInputs, Run, SnapshotComparison } from "./contracts";
import type {
  ClientApprovedInputManifest,
  DIBRevision,
  MarketEvidencePack,
} from "./contracts.dib";
import { buildMarketEvidencePack, importDIBFile } from "./dibApi";
import {
  classifyTemplate,
  createItems,
  DIB_TEMPLATES,
  mapRowsToItems,
  mergeItems,
  type DIBQuestion,
  type DIBTemplate,
} from "./dibRegistry";
import "./dib.css";

type StartType = "idea_only" | "data_intake" | "mixed";
type Notice = { kind: "ok" | "error" | "info"; text: string } | null;

const APPROVABLE_STATES = new Set([
  "VALUE_ENTERED",
  "CLIENT_ESTIMATE",
  "INTENTIONAL_ZERO",
  "NOT_APPLICABLE",
  "EXPERIMENTAL_ESTIMATE",
]);

function uid(prefix: string): string {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}:${suffix}`;
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, stableValue(nested)])
    );
  }
  return value;
}

async function contentHash(value: unknown): Promise<string> {
  const text = JSON.stringify(stableValue(value));
  const bytes = new TextEncoder().encode(text);
  if (typeof crypto !== "undefined" && crypto.subtle) {
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(digest)].map((part) => part.toString(16).padStart(2, "0")).join("");
  }
  let hash = 2166136261;
  for (const byte of bytes) hash = Math.imul(hash ^ byte, 16777619);
  return `local-${(hash >>> 0).toString(16)}`;
}

function numericValue(value: BlueprintItem["value"]): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const text = String(value ?? "").replace(/,/g, "").trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function itemValueForInput(item: BlueprintItem): string | number {
  if (typeof item.value === "number" || typeof item.value === "string") return item.value;
  return "";
}

function updateItem(items: BlueprintItem[], itemId: string, patch: Partial<BlueprintItem>): BlueprintItem[] {
  return items.map((item) => (item.item_id === itemId ? { ...item, ...patch } : item));
}

function manifestBlocker(code: string, message: string) {
  return { code, severity: "critical", message };
}

async function buildClientManifest(
  project: Project,
  template: DIBTemplate,
  items: BlueprintItem[],
  revision: DIBRevision
): Promise<ClientApprovedInputManifest> {
  const blockers: Array<{ code: string; severity: string; message: string }> = [];
  const normalized: Record<string, unknown> = {};

  for (const item of items) {
    const key = item.input_key;
    const state = item.state;
    const required = Boolean(item.required) || [
      "startup_cost",
      "monthly_fixed_cost",
      "unit_price",
      "variable_cost",
      "monthly_units",
    ].includes(item.finance_key ?? key);
    const number = numericValue(item.value);

    if (state === "UNKNOWN" && required) {
      blockers.push(manifestBlocker(`UNKNOWN_${key.toUpperCase()}`, `البند المطلوب «${item.label ?? key}» غير معروف.`));
      continue;
    }
    if ((state === "INTENTIONAL_ZERO" || state === "NOT_APPLICABLE") && !String(item.reason ?? "").trim()) {
      blockers.push(manifestBlocker("BLUEPRINT_REASON_REQUIRED", `يلزم توثيق سبب حالة «${item.label ?? key}».`));
    }
    if (APPROVABLE_STATES.has(state) && item.approval_status !== "approved") {
      blockers.push(manifestBlocker("BLUEPRINT_ITEM_NOT_APPROVED", `البند «${item.label ?? key}» لم يعتمد.`));
    }
    if (state === "EXPERIMENTAL_ESTIMATE") {
      const pack = item.evidence_pack as MarketEvidencePack | null | undefined;
      if (
        !pack ||
        pack.contract_id !== "market.evidence.pack.v1" ||
        pack.review_decision !== "approved" ||
        pack.selected_value === null ||
        number !== pack.selected_value
      ) {
        blockers.push(manifestBlocker("MARKET_EVIDENCE_PACK_INVALID", `التقدير السوقي للبند «${item.label ?? key}» غير معتمد أو لا يطابق القيمة.`));
      }
    }
    if (state === "UNKNOWN" || item.approval_status !== "approved") continue;

    const financeKey = item.finance_key ?? key;
    let accepted: number | string | boolean | null = item.value ?? null;
    if (state === "NOT_APPLICABLE" || state === "INTENTIONAL_ZERO") accepted = 0;
    if (accepted === null || accepted === "") {
      blockers.push(manifestBlocker("APPROVED_ITEM_VALUE_MISSING", `البند المعتمد «${item.label ?? key}» بلا قيمة.`));
      continue;
    }
    if (item.treatment === "exclude" && state !== "NOT_APPLICABLE") continue;

    const current = normalized[financeKey];
    if (typeof current === "number" && typeof accepted === "number") normalized[financeKey] = current + accepted;
    else normalized[financeKey] = accepted;
  }

  for (const financeKey of ["startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"]) {
    if (!(financeKey in normalized)) {
      blockers.push(manifestBlocker(`MANIFEST_MISSING_${financeKey.toUpperCase()}`, `الـManifest لا يحتوي ${financeKey}.`));
    }
  }

  const manifestBase = {
    contract_id: "approved.input.manifest.v1" as const,
    manifest_id: uid("manifest"),
    project_id: project.project_id,
    version: revision.revision,
    status: blockers.length ? ("blocked" as const) : ("approved" as const),
    blueprint_id: revision.blueprint_id,
    blueprint_revision_id: revision.revision_id,
    template_id: template.template_id,
    items,
    normalized_inputs: normalized,
    blockers,
    created_at: new Date().toISOString(),
  };
  return { ...manifestBase, content_hash: await contentHash(manifestBase) };
}

async function fileToBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  }
  return btoa(binary);
}

function questionInput(
  question: DIBQuestion,
  value: unknown,
  onChange: (value: string) => void
) {
  if (question.type === "choice") {
    return (
      <select value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        <option value="">اختر</option>
        {(question.options ?? []).map((option) => <option key={option}>{option}</option>)}
      </select>
    );
  }
  return (
    <input
      type={question.type === "number" ? "number" : "text"}
      value={String(value ?? "")}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export function DIBWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [items, setItems] = useState<BlueprintItem[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [startType, setStartType] = useState<StartType>("idea_only");
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [notice, setNotice] = useState<Notice>(null);
  const [busy, setBusy] = useState("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [compareIds, setCompareIds] = useState<[string, string]>(["", ""]);
  const [comparison, setComparison] = useState<SnapshotComparison | null>(null);
  const [profile, setProfile] = useState({
    name: "",
    sector: "",
    jurisdiction: "Saudi Arabia",
    stage: "idea",
    activity: "",
    region: "",
    city: "",
  });

  const project = projects.find((row) => row.project_id === projectId) ?? null;
  const classified = project ? classifyTemplate(project) : DIB_TEMPLATES[DIB_TEMPLATES.length - 1];
  const template = DIB_TEMPLATES.find((row) => row.template_id === templateId) ?? classified;

  const approvedCount = useMemo(
    () => items.filter((item) => item.approval_status === "approved").length,
    [items]
  );
  const unresolvedCount = useMemo(
    () => items.filter((item) => item.state === "UNKNOWN" || item.approval_status !== "approved").length,
    [items]
  );

  useEffect(() => {
    void refreshProjects();
  }, []);

  useEffect(() => {
    if (!project) return;
    const selectedTemplate =
      DIB_TEMPLATES.find((row) => row.template_id === project.inputs.template_id) ?? classifyTemplate(project);
    setTemplateId(selectedTemplate.template_id);
    setStartType((project.inputs.start_type as StartType | undefined) ?? "idea_only");
    setAnswers(project.inputs.interview_answers ?? {});
    setItems(createItems(project, selectedTemplate));
    setProfile({
      name: project.name,
      sector: project.sector,
      jurisdiction: project.jurisdiction,
      stage: project.depth_profile,
      activity: project.inputs.activity_description ?? "",
      region: project.inputs.location_region ?? "",
      city: project.inputs.location_city ?? "",
    });
    void refreshRuns(project.project_id);
  }, [projectId]);

  async function refreshProjects(preferredId?: string) {
    try {
      const rows = await fetchProjects();
      setProjects(rows);
      const next = preferredId ?? projectId ?? rows[0]?.project_id ?? "";
      if (next) setProjectId(next);
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذر تحميل المشاريع." });
    }
  }

  async function refreshRuns(id: string) {
    try {
      const rows = await fetchProjectRuns(id);
      setRuns(rows);
      const snapshots = rows.map((row) => row.snapshot_id).filter((value): value is string => Boolean(value));
      setCompareIds([snapshots[1] ?? "", snapshots[0] ?? ""]);
    } catch {
      setRuns([]);
    }
  }

  async function createOrUpdateProfile() {
    setBusy("profile");
    setNotice(null);
    try {
      const inputs: ProjectInputs = {
        ...(project?.inputs ?? {}),
        activity_description: profile.activity,
        location_country: "SA",
        location_scope: [profile.region, profile.city].filter(Boolean).join(" / "),
        location_region: profile.region,
        location_city: profile.city,
        primary_sector_id: profile.sector,
      };
      if (project) {
        const updated = await updateProject(project.project_id, {
          name: profile.name,
          sector: profile.sector,
          jurisdiction: profile.jurisdiction,
          depth_profile: profile.stage,
          inputs,
        });
        await refreshProjects(updated.project_id);
      } else {
        const created = await createProject({
          name: profile.name,
          sector: profile.sector,
          jurisdiction: profile.jurisdiction,
          depth_profile: profile.stage,
          inputs,
        });
        await refreshProjects(created.project_id);
      }
      setNotice({ kind: "ok", text: "تم حفظ Project Profile." });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذر حفظ الملف." });
    } finally {
      setBusy("");
    }
  }

  function rebuildBlueprint(nextTemplate = template) {
    if (!project) return;
    setItems(createItems(project, nextTemplate));
    setTemplateId(nextTemplate.template_id);
    setNotice({ kind: "info", text: "تم إنشاء Dynamic Input Blueprint من القالب المحكوم. راجع كل بند واعتمده." });
  }

  async function handleFile(file: File) {
    if (!project) return;
    setBusy("file");
    setNotice(null);
    try {
      const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
      const payload: {
        file_name: string;
        file_type: string;
        file_base64?: string;
        csv_text?: string;
        title: string;
        publisher: string;
        mapping_specs: Array<Record<string, unknown>>;
      } = {
        file_name: file.name,
        file_type: file.type,
        title: file.name,
        publisher: "User local upload",
        mapping_specs: template.items.map((spec) => ({ ...spec })),
      };
      if (extension === "csv") payload.csv_text = await file.text();
      else payload.file_base64 = await fileToBase64(file);
      const dataset = await importDIBFile(payload);
      const notes = (dataset.notes ?? {}) as {
        file_intake?: { mapped_candidates?: BlueprintItem[] };
      };
      let mapped = notes.file_intake?.mapped_candidates ?? [];
      if (!mapped.length && Array.isArray(dataset.preview)) {
        mapped = mapRowsToItems(
          dataset.preview as Record<string, unknown>[],
          template,
          { datasetId: String(dataset.dataset_id ?? ""), fileName: file.name }
        );
      }
      setItems((current) => mergeItems(current, mapped));
      setStartType(startType === "idea_only" ? "mixed" : "data_intake");
      setNotice({
        kind: "ok",
        text: `تم استيراد ${file.name} وربط ${mapped.length} بندًا بالـBlueprint. جميع القيم المستوردة تحتاج مراجعة واعتماد.`,
      });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذر تحليل الملف." });
    } finally {
      setBusy("");
    }
  }

  async function researchItem(item: BlueprintItem) {
    if (!project || !item.item_id) return;
    setBusy(`market:${item.item_id}`);
    setNotice(null);
    try {
      const pack = await buildMarketEvidencePack(project, item);
      setItems((current) =>
        updateItem(current, item.item_id!, {
          evidence_pack: pack,
          market_query: {
            specification: pack.specification,
            query_id: pack.query_id,
            geography: pack.geography,
          },
          evidence_refs: pack.evidence_refs,
          source_type: pack.data_mode === "demo_simulated_external" ? "simulated_evidence" : "market_evidence",
          confidence: pack.confidence === "medium" ? 0.65 : 0.35,
          review_decision: "PENDING",
        })
      );
      setNotice({
        kind: "info",
        text: "عادت حزمة Evidence Pack عبر Kernel → Hearts → Bus → Socket → ASIE Market Intelligence Module. يلزم قرارك.",
      });
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذر بناء Evidence Pack." });
    } finally {
      setBusy("");
    }
  }

  function approveMarketPack(item: BlueprintItem) {
    if (!item.item_id || !item.evidence_pack) return;
    const pack = item.evidence_pack as MarketEvidencePack;
    const approved: MarketEvidencePack = {
      ...pack,
      review_decision: "approved",
      selected_value: pack.weighted_median,
    };
    setItems((current) =>
      updateItem(current, item.item_id!, {
        value: pack.weighted_median,
        state: "EXPERIMENTAL_ESTIMATE",
        approval_status: "approved",
        review_decision: "approved",
        evidence_pack: approved,
        reason: "اعتمد المستخدم Weighted Median من حزمة الدليل السوقي.",
      })
    );
  }

  function rejectMarketPack(item: BlueprintItem) {
    if (!item.item_id) return;
    setItems((current) =>
      updateItem(current, item.item_id!, {
        evidence_pack: item.evidence_pack ? { ...(item.evidence_pack as MarketEvidencePack), review_decision: "rejected" } : null,
        review_decision: "rejected",
        state: "UNKNOWN",
        approval_status: "draft",
        reason: "رفض المستخدم التقدير ويجب تعديل المواصفة أو إدخال قيمة.",
      })
    );
  }

  async function persistBlueprint(runAfterSave = false) {
    if (!project) return;
    setBusy(runAfterSave ? "run" : "save");
    setNotice(null);
    try {
      const previous = project.inputs.blueprint_revisions ?? [];
      const revisionNumber = (project.inputs.blueprint_revision ?? previous.length) + 1;
      const revisionBase = {
        contract_id: "blueprint.revision.v1" as const,
        blueprint_id: project.inputs.blueprint_id ?? `dib:${project.project_id}`,
        project_id: project.project_id,
        template_id: template.template_id,
        revision_id: uid("dibrev"),
        revision: revisionNumber,
        parent_revision_id: project.inputs.blueprint_revision_id ?? null,
        start_type: startType,
        items,
        interview_answers: answers,
        created_at: new Date().toISOString(),
      };
      const revision: DIBRevision = {
        ...revisionBase,
        content_hash: await contentHash(revisionBase),
      };
      const manifest = await buildClientManifest(project, template, items, revision);
      if (runAfterSave && manifest.status !== "approved") {
        setNotice({
          kind: "error",
          text: `Manifest Validation Gate رفض التشغيل: ${manifest.blockers.map((row) => row.message).join(" | ")}`,
        });
        return;
      }

      const inputs: ProjectInputs = {
        ...project.inputs,
        start_type: startType,
        template_id: template.template_id,
        interview_answers: answers,
        blueprint_id: revision.blueprint_id,
        blueprint_revision_id: revision.revision_id,
        blueprint_revision: revision.revision,
        blueprint_items: items,
        blueprint_revisions: [...previous, revision],
        approved_input_manifest: manifest,
        approved_input_manifests: [...(project.inputs.approved_input_manifests ?? []), manifest],
        intake_mode: startType === "idea_only" ? "assisted_estimate" : "file",
      };
      for (const [key, value] of Object.entries(manifest.normalized_inputs)) {
        (inputs as Record<string, unknown>)[key] = value;
      }

      const updated = await updateProject(project.project_id, {
        name: project.name,
        sector: project.sector,
        jurisdiction: project.jurisdiction,
        depth_profile: project.depth_profile,
        inputs,
      });
      await refreshProjects(updated.project_id);
      if (runAfterSave) {
        const overview = await runProject(updated.project_id);
        await refreshRuns(updated.project_id);
        setNotice({
          kind: "ok",
          text: `تم اجتياز Manifest Validation Gate وإنشاء Snapshot ${overview.snapshot.snapshot_id}.`,
        });
      } else {
        setNotice({
          kind: manifest.status === "approved" ? "ok" : "info",
          text:
            manifest.status === "approved"
              ? "تم حفظ Draft Revision وApproved Input Manifest."
              : `تم حفظ Draft Revision؛ الـManifest ما زال محجوبًا بسبب ${manifest.blockers.length} ملاحظة.`,
        });
      }
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذر حفظ DIB." });
    } finally {
      setBusy("");
    }
  }

  async function compareSelected() {
    if (!compareIds[0] || !compareIds[1]) return;
    setBusy("compare");
    try {
      setComparison(await compareSnapshots(compareIds[0], compareIds[1]));
    } catch (error) {
      setNotice({ kind: "error", text: error instanceof Error ? error.message : "تعذرت المقارنة." });
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="dib-shell" dir="rtl">
      <header className="dib-header">
        <div>
          <span className="dib-kicker">AlphaSigma Intelligence Engine — ASIE</span>
          <h1>Dynamic Input Blueprint</h1>
          <p>المسار التشغيلي الكامل من فكرة/ملف إلى Approved Input Manifest ثم Finance وSnapshot.</p>
        </div>
        <a href="#" className="dib-back">العودة للمنصة</a>
      </header>

      {notice && <div className={`dib-notice ${notice.kind}`}>{notice.text}</div>}

      <section className="dib-card">
        <h2>1. Project Profile</h2>
        <div className="dib-grid profile">
          <label>المشروع
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">مشروع جديد</option>
              {projects.map((row) => <option key={row.project_id} value={row.project_id}>{row.name}</option>)}
            </select>
          </label>
          <label>الفكرة / الاسم<input value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} /></label>
          <label>القطاع<input value={profile.sector} onChange={(event) => setProfile({ ...profile, sector: event.target.value })} /></label>
          <label>المرحلة
            <select value={profile.stage} onChange={(event) => setProfile({ ...profile, stage: event.target.value })}>
              <option value="idea">فكرة</option><option value="validation">تحقق</option><option value="operating">قائم</option>
            </select>
          </label>
          <label>المنطقة<input value={profile.region} onChange={(event) => setProfile({ ...profile, region: event.target.value })} /></label>
          <label>المدينة<input value={profile.city} onChange={(event) => setProfile({ ...profile, city: event.target.value })} /></label>
          <label className="wide">وصف النشاط<input value={profile.activity} onChange={(event) => setProfile({ ...profile, activity: event.target.value })} /></label>
        </div>
        <button disabled={busy === "profile" || !profile.name || !profile.sector} onClick={() => void createOrUpdateProfile()}>
          {busy === "profile" ? "جارٍ الحفظ…" : "حفظ Project Profile"}
        </button>
      </section>

      {project && (
        <>
          <section className="dib-card">
            <h2>2. المصنف المحكوم + نوع البداية</h2>
            <div className="dib-grid">
              <label>Template Registry
                <select
                  value={template.template_id}
                  onChange={(event) => {
                    const next = DIB_TEMPLATES.find((row) => row.template_id === event.target.value) ?? classified;
                    setTemplateId(next.template_id);
                    rebuildBlueprint(next);
                  }}
                >
                  {DIB_TEMPLATES.map((row) => <option key={row.template_id} value={row.template_id}>{row.label_ar}</option>)}
                </select>
              </label>
              <label>نوع البداية
                <select value={startType} onChange={(event) => setStartType(event.target.value as StartType)}>
                  <option value="idea_only">فكرة فقط</option>
                  <option value="data_intake">أرقام / ملفات / عروض</option>
                  <option value="mixed">مسار مختلط</option>
                </select>
              </label>
            </div>
            <div className="dib-actions">
              <button onClick={() => rebuildBlueprint()}>إعادة توليد البنود من القالب</button>
              <label className="dib-file-button">
                {busy === "file" ? "جارٍ تحليل الملف…" : "استيراد CSV / XLSX / PDF / عرض سعر"}
                <input
                  type="file"
                  accept=".csv,.xlsx,.pdf"
                  disabled={busy === "file"}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void handleFile(file);
                    event.currentTarget.value = "";
                  }}
                />
              </label>
            </div>
          </section>

          <section className="dib-card">
            <h2>3. Product AI Interview المحكوم</h2>
            <p className="dib-guard">أسئلة محددة من Question Registry فقط؛ لا يوجد مزود AI خارجي، ولا توليد أرقام نهائية.</p>
            <div className="dib-grid questions">
              {template.questions.map((question) => (
                <label key={question.question_id}>
                  {question.label}{question.required ? " *" : ""}
                  {questionInput(question, answers[question.question_id], (value) =>
                    setAnswers((current) => ({ ...current, [question.question_id]: value }))
                  )}
                </label>
              ))}
            </div>
          </section>

          <section className="dib-card">
            <div className="dib-title-row">
              <div>
                <h2>4. بنود Dynamic Input Blueprint</h2>
                <p>{items.length} بندًا — {approvedCount} معتمد — {unresolvedCount} يحتاج معالجة</p>
              </div>
              <button onClick={() => setItems((current) => [...current, {
                item_id: uid("custom-item"),
                input_key: `custom_${current.length + 1}`,
                finance_key: `custom_${current.length + 1}`,
                label: "بند مخصص",
                category: "custom",
                unit: "SAR",
                value: null,
                state: "UNKNOWN",
                approval_status: "draft",
                treatment: "include",
                source_type: "user_input",
                confidence: 0.4,
                evidence_refs: [],
                required: false,
              }])}>إضافة بند</button>
            </div>

            <div className="dib-items">
              {items.map((item) => {
                const pack = item.evidence_pack as MarketEvidencePack | null | undefined;
                return (
                  <article className="dib-item" key={item.item_id ?? item.input_key}>
                    <div className="dib-item-head">
                      <input
                        className="dib-item-label"
                        value={item.label ?? item.input_key}
                        onChange={(event) => item.item_id && setItems((current) => updateItem(current, item.item_id!, { label: event.target.value }))}
                      />
                      <span>{item.category} · {item.unit}</span>
                      {item.required && <strong>مطلوب</strong>}
                    </div>
                    <div className="dib-item-controls">
                      <label>القيمة
                        <input
                          type="number"
                          value={itemValueForInput(item)}
                          onChange={(event) => item.item_id && setItems((current) => updateItem(current, item.item_id!, {
                            value: event.target.value === "" ? null : Number(event.target.value),
                          }))}
                        />
                      </label>
                      <label>حالة البند
                        <select
                          value={item.state}
                          onChange={(event) => item.item_id && setItems((current) => updateItem(current, item.item_id!, {
                            state: event.target.value as BlueprintItem["state"],
                            approval_status: "draft",
                          }))}
                        >
                          <option value="VALUE_ENTERED">رقم العميل</option>
                          <option value="CLIENT_ESTIMATE">رقم تقريبي</option>
                          <option value="INTENTIONAL_ZERO">صفر مقصود</option>
                          <option value="NOT_APPLICABLE">غير منطبق</option>
                          <option value="UNKNOWN">لا أعرف</option>
                          <option value="EXPERIMENTAL_ESTIMATE">تقدير سوقي تجريبي</option>
                        </select>
                      </label>
                      <label>القرار
                        <select
                          value={item.approval_status ?? "draft"}
                          onChange={(event) => item.item_id && setItems((current) => updateItem(current, item.item_id!, {
                            approval_status: event.target.value as BlueprintItem["approval_status"],
                          }))}
                        >
                          <option value="draft">قيد المراجعة</option>
                          <option value="approved">معتمد</option>
                          <option value="rejected">مرفوض</option>
                        </select>
                      </label>
                      <label className="wide">السبب / الملاحظة
                        <input
                          value={item.reason ?? ""}
                          onChange={(event) => item.item_id && setItems((current) => updateItem(current, item.item_id!, { reason: event.target.value }))}
                          placeholder="إلزامي للصفر المقصود وغير المنطبق"
                        />
                      </label>
                    </div>
                    <div className="dib-actions">
                      <button
                        disabled={busy === `market:${item.item_id}`}
                        onClick={() => void researchItem(item)}
                      >
                        {busy === `market:${item.item_id}` ? "جارٍ البحث…" : "لا أعرف — ابحث عن هذا البند"}
                      </button>
                      <span className="dib-source">المصدر: {item.source_type ?? "user_input"} · الثقة: {item.confidence ?? 0}</span>
                    </div>
                    {pack && (
                      <div className="dib-pack">
                        <strong>Evidence Pack</strong>
                        <span>P25: {pack.p25}</span>
                        <span>Weighted Median: {pack.weighted_median}</span>
                        <span>P75: {pack.p75}</span>
                        <span>عينات: {pack.sample_count}</span>
                        <span>الثقة: {pack.confidence}</span>
                        <span className={pack.data_mode === "demo_simulated_external" ? "warning" : ""}>
                          {pack.data_mode === "demo_simulated_external" ? "محاكاة تطوير محلية — ليست سعرًا حقيقيًا" : "عينات مستخدم/بيانات محلية"}
                        </span>
                        <div>
                          <button onClick={() => approveMarketPack(item)}>اعتماد المتوسط المرجح</button>
                          <button className="secondary" onClick={() => rejectMarketPack(item)}>رفض / تعديل المواصفة</button>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          <section className="dib-card">
            <h2>5. Approved Input Manifest → Validation Gate → AAS Runtime</h2>
            <div className="dib-flow">
              <span>Dynamic Input Blueprint</span><b>→</b><span>Approved Input Manifest</span><b>→</b>
              <span>Manifest Validation Gate</span><b>→</b><span>Kernel / Hearts / Bus / Socket / Module Runtime</span><b>→</b>
              <span>Finance Engine</span><b>→</b><span>Snapshot Assembly</span>
            </div>
            <div className="dib-actions">
              <button disabled={Boolean(busy)} onClick={() => void persistBlueprint(false)}>
                {busy === "save" ? "جارٍ الحفظ…" : "حفظ Draft Revision وManifest"}
              </button>
              <button className="primary" disabled={Boolean(busy)} onClick={() => void persistBlueprint(true)}>
                {busy === "run" ? "جارٍ التشغيل…" : "اعتماد وتشغيل وإنشاء Snapshot"}
              </button>
            </div>
          </section>

          <section className="dib-card">
            <h2>6. Revision Lineage ومقارنة Snapshots</h2>
            <p>كل تعديل ينشئ Draft Revision جديدًا. لا تُعدّل Snapshot سابقة.</p>
            <div className="dib-grid">
              <label>Snapshot الأولى
                <select value={compareIds[0]} onChange={(event) => setCompareIds([event.target.value, compareIds[1]])}>
                  <option value="">اختر</option>
                  {runs.map((run) => run.snapshot_id && <option key={run.snapshot_id} value={run.snapshot_id}>{run.snapshot_id}</option>)}
                </select>
              </label>
              <label>Snapshot الثانية
                <select value={compareIds[1]} onChange={(event) => setCompareIds([compareIds[0], event.target.value])}>
                  <option value="">اختر</option>
                  {runs.map((run) => run.snapshot_id && <option key={run.snapshot_id} value={run.snapshot_id}>{run.snapshot_id}</option>)}
                </select>
              </label>
            </div>
            <button disabled={!compareIds[0] || !compareIds[1] || busy === "compare"} onClick={() => void compareSelected()}>
              مقارنة
            </button>
            {comparison && (
              <pre className="dib-comparison">{JSON.stringify(comparison, null, 2)}</pre>
            )}
          </section>

          <section className="dib-card dib-governance">
            <h2>ضوابط الحوكمة</h2>
            <ul>
              <li>AI Providers: DISABLED / DENY_ALL.</li>
              <li>External network research: DISABLED.</li>
              <li>البحث السوقي يعمل عبر AAS Bus/Socket ويعيد Candidate Assumption فقط.</li>
              <li>Finance لا يستقبل أرقام المحادثة أو الملف الخام؛ يستقبل Manifest-derived normalized inputs.</li>
              <li>Snapshot السابقة غير قابلة للتعديل.</li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
