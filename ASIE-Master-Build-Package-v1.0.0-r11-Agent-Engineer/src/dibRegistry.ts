import type { BlueprintItem, Project } from "./contracts";

export interface DIBQuestion {
  question_id: string;
  label: string;
  type: "choice" | "number" | "text";
  options?: string[];
  required: boolean;
}

export interface DIBItemSpec {
  input_key: string;
  label: string;
  category: string;
  unit: string;
  required: boolean;
  finance_key: string;
  default_value?: number;
}

export interface DIBTemplate {
  template_id: string;
  label_ar: string;
  match_terms: string[];
  questions: DIBQuestion[];
  items: DIBItemSpec[];
}

const common: DIBItemSpec[] = [
  { input_key: "startup_cost", label: "تكلفة التأسيس الأساسية", category: "capex", unit: "SAR", required: true, finance_key: "startup_cost" },
  { input_key: "monthly_fixed_cost", label: "التكاليف الشهرية الثابتة", category: "opex", unit: "SAR", required: true, finance_key: "monthly_fixed_cost" },
  { input_key: "unit_price", label: "سعر بيع الوحدة", category: "revenue", unit: "SAR", required: true, finance_key: "unit_price" },
  { input_key: "variable_cost", label: "التكلفة المتغيرة للوحدة", category: "variable_cost", unit: "SAR", required: true, finance_key: "variable_cost" },
  { input_key: "monthly_units", label: "الوحدات المباعة شهريًا", category: "revenue", unit: "count", required: true, finance_key: "monthly_units" },
  { input_key: "annual_discount_rate", label: "معدل الخصم السنوي", category: "finance", unit: "ratio", required: true, finance_key: "annual_discount_rate", default_value: 0.1 },
  { input_key: "working_capital_months", label: "أشهر رأس المال العامل", category: "finance", unit: "months", required: true, finance_key: "working_capital_months", default_value: 2 },
];

export const DIB_TEMPLATES: DIBTemplate[] = [
  {
    template_id: "template.food_service.shawarma.v1",
    label_ar: "محل شاورما / مطعم خدمة سريعة",
    match_terms: ["شاورما", "shawarma", "مطعم", "restaurant", "وجبات", "food"],
    questions: [
      { question_id: "service_model", label: "هل الخدمة محلية فقط أم تشمل التوصيل؟", type: "choice", options: ["محلي", "توصيل", "هجين"], required: true },
      { question_id: "menu_scope", label: "هل المشروع شاورما فقط أم قائمة أوسع؟", type: "choice", options: ["شاورما فقط", "شاورما ومقبلات", "قائمة أوسع"], required: true },
      { question_id: "site_area_m2", label: "ما المساحة التقريبية للموقع بالمتر المربع؟", type: "number", required: true },
      { question_id: "daily_capacity", label: "كم وجبة تستهدف يوميًا؟", type: "number", required: true },
      { question_id: "new_or_used_equipment", label: "هل تقبل معدات مستعملة بحالة موثقة؟", type: "choice", options: ["جديدة فقط", "جديدة أو مستعملة"], required: true },
    ],
    items: [
      ...common,
      { input_key: "equipment_shawarma_grill", label: "شواية شاورما تجارية", category: "capex_equipment", unit: "SAR", required: true, finance_key: "capex_equipment" },
      { input_key: "equipment_refrigeration", label: "تبريد وثلاجات حفظ", category: "capex_equipment", unit: "SAR", required: true, finance_key: "capex_equipment" },
      { input_key: "equipment_prep", label: "معدات التحضير والتقطيع", category: "capex_equipment", unit: "SAR", required: true, finance_key: "capex_equipment" },
      { input_key: "equipment_pos", label: "نظام نقاط البيع", category: "capex_equipment", unit: "SAR", required: false, finance_key: "capex_equipment" },
      { input_key: "capex_fitout", label: "تجهيز وديكور المحل", category: "capex", unit: "SAR", required: true, finance_key: "capex_fitout" },
      { input_key: "capex_licenses_local", label: "التراخيص والرسوم المحلية", category: "capex", unit: "SAR", required: true, finance_key: "capex_licenses_local" },
      { input_key: "rent_monthly", label: "إيجار الموقع شهريًا", category: "opex", unit: "SAR", required: true, finance_key: "rent_monthly" },
      { input_key: "payroll_monthly", label: "الرواتب الشهرية", category: "opex", unit: "SAR", required: true, finance_key: "payroll_monthly" },
      { input_key: "utilities_monthly", label: "الكهرباء والمياه والغاز", category: "opex", unit: "SAR", required: true, finance_key: "utilities_monthly" },
      { input_key: "maintenance_monthly", label: "الصيانة والنظافة", category: "opex", unit: "SAR", required: false, finance_key: "maintenance_monthly" },
    ],
  },
  {
    template_id: "template.digital.saas.v1",
    label_ar: "منتج رقمي / SaaS",
    match_terms: ["saas", "برمج", "تطبيق", "منصة", "software", "app", "digital"],
    questions: [
      { question_id: "customer_type", label: "هل العملاء أفراد أم منشآت؟", type: "choice", options: ["أفراد", "منشآت", "كلاهما"], required: true },
      { question_id: "billing_model", label: "ما نموذج التحصيل؟", type: "choice", options: ["شهري", "سنوي", "حسب الاستخدام"], required: true },
      { question_id: "team_size", label: "كم حجم الفريق عند الإطلاق؟", type: "number", required: true },
      { question_id: "hosting_model", label: "هل الاستضافة سحابية بالكامل؟", type: "choice", options: ["نعم", "هجين"], required: true },
    ],
    items: [
      ...common,
      { input_key: "capex_equipment", label: "أجهزة ومعدات تقنية", category: "capex_equipment", unit: "SAR", required: false, finance_key: "capex_equipment" },
      { input_key: "payroll_monthly", label: "فريق المنتج والتقنية", category: "opex", unit: "SAR", required: true, finance_key: "payroll_monthly" },
      { input_key: "utilities_monthly", label: "استضافة وخدمات سحابية", category: "opex", unit: "SAR", required: true, finance_key: "utilities_monthly" },
      { input_key: "marketing_monthly", label: "التسويق واكتساب العملاء", category: "opex", unit: "SAR", required: true, finance_key: "marketing_monthly" },
      { input_key: "rent_monthly", label: "إيجار المكتب", category: "opex", unit: "SAR", required: false, finance_key: "rent_monthly" },
    ],
  },
  {
    template_id: "template.retail.v1",
    label_ar: "تجارة تجزئة",
    match_terms: ["متجر", "تجزئة", "retail", "shop", "بيع"],
    questions: [
      { question_id: "sales_channel", label: "ما قناة البيع؟", type: "choice", options: ["متجر", "إلكتروني", "هجين"], required: true },
      { question_id: "inventory_model", label: "هل المخزون مملوك أم بالعمولة؟", type: "choice", options: ["مملوك", "عمولة", "هجين"], required: true },
      { question_id: "site_area_m2", label: "ما مساحة الموقع التقريبية؟", type: "number", required: false },
    ],
    items: [
      ...common,
      { input_key: "capex_equipment", label: "تجهيزات وأرفف ونقاط بيع", category: "capex_equipment", unit: "SAR", required: true, finance_key: "capex_equipment" },
      { input_key: "capex_fitout", label: "تجهيز وديكور", category: "capex", unit: "SAR", required: true, finance_key: "capex_fitout" },
      { input_key: "rent_monthly", label: "الإيجار الشهري", category: "opex", unit: "SAR", required: true, finance_key: "rent_monthly" },
      { input_key: "payroll_monthly", label: "الرواتب الشهرية", category: "opex", unit: "SAR", required: true, finance_key: "payroll_monthly" },
      { input_key: "marketing_monthly", label: "التسويق الشهري", category: "opex", unit: "SAR", required: false, finance_key: "marketing_monthly" },
    ],
  },
  {
    template_id: "template.manufacturing.v1",
    label_ar: "تصنيع",
    match_terms: ["مصنع", "تصنيع", "manufactur", "production", "إنتاج"],
    questions: [
      { question_id: "product_family", label: "ما عائلة المنتج الرئيسية؟", type: "text", required: true },
      { question_id: "monthly_capacity", label: "ما الطاقة الإنتاجية الشهرية المستهدفة؟", type: "number", required: true },
      { question_id: "facility_model", label: "هل المنشأة مملوكة أم مستأجرة؟", type: "choice", options: ["مملوكة", "مستأجرة"], required: true },
      { question_id: "automation_level", label: "ما مستوى الأتمتة؟", type: "choice", options: ["يدوي", "نصف آلي", "آلي"], required: true },
    ],
    items: [
      ...common,
      { input_key: "capex_equipment", label: "خطوط ومعدات الإنتاج", category: "capex_equipment", unit: "SAR", required: true, finance_key: "capex_equipment" },
      { input_key: "capex_fitout", label: "تهيئة المنشأة الصناعية", category: "capex", unit: "SAR", required: true, finance_key: "capex_fitout" },
      { input_key: "rent_monthly", label: "إيجار المنشأة", category: "opex", unit: "SAR", required: true, finance_key: "rent_monthly" },
      { input_key: "payroll_monthly", label: "العمالة والإشراف", category: "opex", unit: "SAR", required: true, finance_key: "payroll_monthly" },
      { input_key: "utilities_monthly", label: "الطاقة والمرافق", category: "opex", unit: "SAR", required: true, finance_key: "utilities_monthly" },
      { input_key: "maintenance_monthly", label: "الصيانة الوقائية", category: "opex", unit: "SAR", required: true, finance_key: "maintenance_monthly" },
    ],
  },
  {
    template_id: "template.generic.v1",
    label_ar: "قالب مشروع عام",
    match_terms: [],
    questions: [
      { question_id: "revenue_model", label: "كيف يحقق المشروع الإيراد؟", type: "text", required: true },
      { question_id: "operating_model", label: "ما طبيعة التشغيل الأساسية؟", type: "text", required: true },
      { question_id: "monthly_volume", label: "ما الحجم الشهري المستهدف؟", type: "number", required: true },
    ],
    items: common,
  },
];

export function classifyTemplate(project: Project): DIBTemplate {
  const text = [project.name, project.sector, project.inputs.activity_description, project.inputs.primary_sector_id]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return (
    DIB_TEMPLATES.find(
      (template) =>
        template.template_id !== "template.generic.v1" &&
        template.match_terms.some((term) => text.includes(term.toLowerCase()))
    ) ?? DIB_TEMPLATES[DIB_TEMPLATES.length - 1]
  );
}

export function createItems(project: Project, template: DIBTemplate): BlueprintItem[] {
  const existingRaw = project.inputs.blueprint_items;
  const existing = Array.isArray(existingRaw)
    ? new Map(existingRaw.map((item) => [item.input_key, item]))
    : new Map(Object.entries(existingRaw ?? {}).map(([key, item]) => [key, { ...item, input_key: item.input_key || key }]));
  return template.items.map((spec) => {
    const stored = existing.get(spec.input_key);
    const scalar = (project.inputs as Record<string, unknown>)[spec.input_key];
    const value = stored?.value ?? scalar ?? spec.default_value ?? null;
    return {
      item_id: stored?.item_id ?? `item:${project.project_id}:${spec.input_key}`,
      input_key: spec.input_key,
      finance_key: spec.finance_key,
      label: stored?.label ?? spec.label,
      category: stored?.category ?? spec.category,
      value,
      unit: stored?.unit ?? spec.unit,
      state: stored?.state ?? (value === null || value === undefined || value === "" ? "UNKNOWN" : "VALUE_ENTERED"),
      reason: stored?.reason ?? "",
      source_type: stored?.source_type ?? "user_input",
      treatment: stored?.treatment ?? "include",
      approval_status: stored?.approval_status ?? "draft",
      confidence: stored?.confidence ?? (value === null || value === undefined ? 0.35 : 0.65),
      evidence_refs: stored?.evidence_refs ?? [],
      assumption_refs: stored?.assumption_refs ?? [],
      required: spec.required,
      market_query: stored?.market_query,
      evidence_pack: stored?.evidence_pack,
      review_decision: stored?.review_decision,
      import_source: stored?.import_source,
    } as BlueprintItem;
  });
}

const aliases: Record<string, string[]> = {
  startup_cost: ["تكلفة التأسيس", "startup"],
  monthly_fixed_cost: ["تكاليف ثابتة", "monthly fixed", "fixed cost"],
  unit_price: ["سعر الوحدة", "سعر البيع", "unit price"],
  variable_cost: ["تكلفة متغيرة", "variable cost"],
  monthly_units: ["وحدات شهرية", "مبيعات شهرية", "monthly units"],
  rent_monthly: ["إيجار", "rent"],
  payroll_monthly: ["رواتب", "أجور", "payroll", "salary"],
  utilities_monthly: ["كهرباء", "مياه", "غاز", "مرافق", "utilities"],
  marketing_monthly: ["تسويق", "marketing"],
  maintenance_monthly: ["صيانة", "maintenance"],
  capex_equipment: ["معدات", "equipment", "machinery"],
  capex_fitout: ["تجهيز", "ديكور", "fitout"],
  capex_licenses_local: ["ترخيص", "رسوم", "license", "permit"],
  equipment_shawarma_grill: ["شواية شاورما", "shawarma grill", "grill"],
  equipment_refrigeration: ["ثلاجة", "تبريد", "freezer", "refriger"],
  equipment_prep: ["تحضير", "تقطيع", "prep"],
  equipment_pos: ["نقاط البيع", "pos", "cashier"],
};

function numberFrom(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const match = String(value ?? "").replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

export function mapRowsToItems(
  rows: Record<string, unknown>[],
  template: DIBTemplate,
  source: { datasetId?: string; fileName?: string }
): BlueprintItem[] {
  return rows.flatMap((row, index) => {
    const values = Object.values(row);
    const description = values.filter((value) => numberFrom(value) === null).join(" ").trim();
    const amounts = values.map(numberFrom).filter((value): value is number => value !== null);
    if (!amounts.length) return [];
    const amount = amounts[amounts.length - 1];
    const ranked = template.items
      .map((spec) => {
        const text = description.toLowerCase();
        const score = (aliases[spec.input_key] ?? []).reduce(
          (total, alias) => total + (text.includes(alias.toLowerCase()) ? 6 : 0),
          text.includes(spec.label.toLowerCase()) ? 8 : 0
        );
        return { spec, score };
      })
      .sort((a, b) => b.score - a.score);
    const match = ranked[0];
    const base = match?.score > 0 ? match.spec : undefined;
    const key = base?.input_key ?? `imported_row_${index + 1}`;
    return [
      {
        item_id: `imported:${source.datasetId ?? "local"}:${index + 1}`,
        input_key: key,
        finance_key: base?.finance_key ?? key,
        label: base?.label ?? (description || `بند مستورد ${index + 1}`),
        category: base?.category ?? "custom",
        value: amount,
        unit: base?.unit ?? "SAR",
        state: "CLIENT_ESTIMATE",
        reason: "قيمة مستوردة وتحتاج مراجعة المستخدم.",
        source_type: "file_import",
        treatment: "include",
        approval_status: "draft",
        confidence: match?.score >= 6 ? 0.55 : 0.35,
        evidence_refs: source.datasetId ? [`dataset:${source.datasetId}:row:${index + 1}`] : [],
        required: base?.required ?? false,
        import_source: {
          dataset_id: source.datasetId ?? "",
          file_name: source.fileName ?? "",
          row_index: index,
          raw_row: row,
          mapping_score: match?.score ?? 0,
        },
      } as BlueprintItem,
    ];
  });
}

export function mergeItems(base: BlueprintItem[], incoming: BlueprintItem[]): BlueprintItem[] {
  const merged = new Map(base.map((item) => [item.input_key, item]));
  for (const item of incoming) {
    const current = merged.get(item.input_key);
    merged.set(item.input_key, current ? { ...current, ...item, item_id: current.item_id ?? item.item_id } : item);
  }
  return [...merged.values()];
}
