export type OutputStatus =
  | "ready"
  | "needs_input"
  | "insufficient_data"
  | "blocked"
  | "stale"
  | "error"
  | "permission_denied";

export type SourceState = "candidate" | "blocked" | "enabled" | "reference_only";
export type DatasetState = "draft" | "review_required" | "approved_for_use" | "rejected" | "archived";

export interface ProjectInputs {
  primary_sector_id?: string;
  subsector_id?: string;
  activity_description?: string;
  location_scope?: string;
  location_country?: "SA" | string;
  location_region?: string;
  location_city?: string;
  location_district?: string;
  location_latitude?: number;
  location_longitude?: number;
  gap_statement?: string;
  competitive_edge?: string;
  target_audience?: string;
  intake_mode?: "manual" | "file" | "assisted_estimate" | string;
  capital_available?: number;
  startup_cost?: number;
  monthly_fixed_cost?: number;
  unit_price?: number;
  variable_cost?: number;
  monthly_units?: number;
  use_operating_capacity?: boolean;
  capacity_units_per_day?: number;
  operating_days_per_month?: number;
  utilization_rate?: number;
  payroll_monthly?: number;
  rent_monthly?: number;
  utilities_monthly?: number;
  marketing_monthly?: number;
  maintenance_monthly?: number;
  capex_equipment?: number;
  capex_fitout?: number;
  capex_licenses_local?: number;
  depreciation_years?: number;
  equity_contribution?: number;
  loan_grace_months?: number;
  annual_discount_rate?: number;
  working_capital_months?: number;
  debt_amount?: number;
  annual_interest_rate?: number;
  loan_years?: number;
}

export interface Project {
  project_id: string;
  name: string;
  sector: string;
  jurisdiction: string;
  depth_profile: string;
  inputs: ProjectInputs;
  created_at: string;
  updated_at: string;
  run_id?: string;
  snapshot_id?: string;
  data_badge?: "DEMO_DATA" | "OFFICIAL_OPEN_DATA" | "USER_VERIFIED";
  status?: string;
}

export interface MarketLocationRecord {
  record_type: "competitor" | "site_candidate" | "coverage_area" | "market_signal";
  name: string;
  sector: string;
  geography: string;
  coordinates?: { lat: number; lng: number } | null;
  attributes: Record<string, unknown>;
  evidence_refs: string[];
  data_mode: "demo_simulated_external" | "user_verified" | "official_open_data";
  display_badge: string;
  production_admission: "blocked" | "local_only";
  decision_authority: "context_only";
}

export interface ProjectDraft extends Project {
  readiness?: ProjectReadiness;
}

export interface WizardStepStatus {
  step_id:
    | "definition"
    | "revenue_model"
    | "costs"
    | "financing"
    | "assumptions"
    | "sources"
    | "review"
    | "run"
    | string;
  label: string;
  status: "ready" | "needs_input" | "needs_review" | "blocked";
  message: string;
}

export interface ProjectReadiness {
  project_id: string;
  ready_to_run: boolean;
  steps: WizardStepStatus[];
  blockers: Blocker[];
}

export interface Scenario {
  scenario_id: string;
  label?: string;
}

export interface Run {
  run_id: string;
  project_id?: string;
  scenario_id: string;
  snapshot_id?: string;
  status: "completed" | "blocked" | "error";
  created_at: string;
  sovereign_verdict?: string;
  acceptance_status?: string;
  data_badge?: string;
  monte_carlo_probability?: number | null;
}

export interface Snapshot {
  snapshot_id: string;
  immutable: boolean;
  created_at: string;
  snapshot_version: string;
  assembled_at: string;
  content_hash: string;
  integrity_hash: string;
}

export interface SnapshotAssemblyLineageRecord {
  output_key: string;
  envelope_id: string;
  producer_module_id: string;
  producer_contract_id: string;
  producer_contract_version: string;
  message_id: string;
  correlation_id: string;
  audit_ref: string;
  output_hash: string;
}

export interface SnapshotAssemblyMetadata {
  contract_id: "snapshot.assemble.v1" | string;
  snapshot_version?: string;
  assembled_at?: string;
  content_hash: string;
  integrity_hash: string;
  overview_projection_hash?: string;
  report_projection_hash?: string;
  lineage?: SnapshotAssemblyLineageRecord[];
  correlation_map?: Record<string, string>;
  projection_source: "immutable_assembled_snapshot" | string;
}

export interface EvidenceRef {
  evidence_id: string;
  source_id: string;
  title: string;
  url: string;
  snapshot_id: string;
}

export interface DatasetColumnProfile {
  row_count: number;
  non_null_count: number;
  numeric_count?: number;
  missing_count: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  outlier_count?: number;
  inferred_type: "number" | "text" | "mixed" | string;
}

export interface DatasetQualityReview {
  status: "passed" | "warning" | "rejected" | string;
  row_count: number;
  column_count: number;
  duplicate_row_count: number;
  duplicate_ratio: number;
  max_missing_ratio: number;
  columns_with_missing: string[];
  numeric_columns: string[];
  text_columns: string[];
  mixed_type_columns: string[];
  outlier_counts: Record<string, number>;
  reasons: string[];
}

export interface DatasetRecord {
  dataset_id: string;
  source_id: string;
  title: string;
  publisher: string;
  import_method: "manual_csv" | "manual_json" | "manual_table" | string;
  classification: string;
  review_status: DatasetState;
  human_review_decision: string;
  license_snapshot_ref: string;
  terms_hash: string;
  pdpl_check: string;
  attribution: string;
  row_count: number;
  columns: string[];
  preview: Record<string, string | number | null>[];
  notes: {
    notes?: string;
    profile?: Record<string, DatasetColumnProfile>;
    quality_review?: DatasetQualityReview;
    external_fetch_allowed?: boolean;
  };
  created_at: string;
  updated_at: string;
}

export type TransformationOperation =
  | "select_column"
  | "aggregate_average"
  | "aggregate_sum"
  | "filter"
  | "remove_outliers"
  | "normalize"
  | "manual_derivation_note";

export interface TransformationRecord {
  transformation_id: string;
  dataset_id: string;
  operation_type: TransformationOperation | string;
  operation_label: string;
  input_columns: string[];
  filters: Record<string, unknown>;
  aggregation_method: string;
  output_value: string | null;
  output_unit: string;
  review_status: "draft" | "review_required" | "approved" | "rejected" | string;
  review_notes: string;
  lineage: {
    steps?: Array<Record<string, unknown>>;
    source_dataset_id?: string;
    source_profile_ref?: string;
    quality_review?: {
      status: "passed" | "warning" | "rejected" | string;
      reasons: string[];
      operation_type: string;
      input_columns: string[];
      review_status: string;
    };
    external_fetch_enabled?: boolean;
  };
  created_at: string;
  updated_at: string;
}

export interface TransformationLineageRecord {
  lineage_id: string;
  snapshot_id: string;
  run_id: string | null;
  ledger_id: string;
  dataset_id: string;
  transformation_id: string;
  target_type: "assumption" | "sector_criterion" | string;
  target_id: string;
  operation_type: string;
  review_status: string;
  output_value: string | null;
  output_unit: string;
  steps: Array<Record<string, unknown>>;
  external_fetch_enabled: boolean;
}

export interface DatasetQualityGate {
  dataset_id: string;
  source_id: string;
  status: "passed" | "warning" | "rejected" | "failed" | string;
  can_use_for_assumptions: boolean;
  reasons: string[];
  quality_review: DatasetQualityReview;
  checks: {
    source_reviewed: boolean;
    license_snapshot: boolean;
    terms_hash: boolean;
    classification: boolean;
    pdpl_check: boolean;
    attribution: boolean;
    human_review: boolean;
    data_quality_review: boolean;
    external_fetch_enabled: boolean;
  };
}

export interface EvidenceLink {
  evidence_link_id: string;
  project_id: string;
  target_type: "assumption" | "sector_criterion" | string;
  target_id: string;
  assumption_id: string;
  dataset_id: string;
  transformation_id?: string;
  evidence_ref: string;
  transformation_note: string;
  human_review_decision: string;
  created_at: string;
  updated_at: string;
}

export interface EvidenceBindingTarget {
  target_type: "assumption" | "sector_criterion" | string;
  target_id: string;
  label: string;
}

export interface EvidenceLedgerRecord {
  ledger_id: string;
  evidence_link_id: string;
  project_id: string;
  snapshot_id: string;
  run_id: string | null;
  target_type: "assumption" | "sector_criterion" | string;
  target_id: string;
  dataset_id: string;
  dataset_title: string;
  source_id: string;
  source_state: SourceState | string;
  dataset_review_status: DatasetState | string;
  quality_gate_status: "passed" | "failed" | string;
  data_quality_status: "passed" | "warning" | "rejected" | "unknown" | string;
  data_quality_reasons: string[];
  can_support_target: boolean;
  evidence_confidence_score: number;
  evidence_confidence_status: "high" | "medium" | "low" | string;
  evidence_confidence_factors: Record<string, number>;
  evidence_ref: string;
  transformation_id: string;
  transformation_status: string;
  transformation_quality_status: "passed" | "warning" | "rejected" | "not_required" | string;
  transformation_review_reasons: string[];
  transformation_operation: string;
  transformation_output_value: string | null;
  transformation_output_unit: string;
  transformation_note: string;
  human_review_decision: string;
  external_fetch_enabled: boolean;
}

export interface EvidenceGapRecord {
  target_type: "assumption" | "sector_criterion" | string;
  target_id: string;
  label: string;
  reason: string;
}

export interface EvidenceCoverageMatrix {
  coverage_id: string;
  status: "supported" | "needs_evidence" | string;
  supported: number;
  needs_evidence: number;
  targets: Array<EvidenceBindingTarget & { coverage_status: "supported" | "needs_evidence" | "reference_only" | string }>;
  gaps: EvidenceGapRecord[];
}

export interface AssumptionRef {
  assumption_id: string;
  label: string;
  owner: string;
  value: number | string;
}

export interface AssumptionRecord {
  assumption_id: string;
  project_id: string;
  input_key: string;
  label: string;
  value: string;
  unit: string;
  owner: string;
  source_type: "user_input" | "local_default" | "official_open_data" | "manual_review" | string;
  confidence: number;
  review_status: "draft" | "needs_review" | "approved" | "rejected" | string;
  created_at: string;
  updated_at: string;
}

export interface OutputEnvelope {
  output_id: string;
  project_id: string;
  run_id: string;
  scenario_id: string;
  snapshot_id: string;
  owner_module: string;
  contract_id: string;
  algorithm_id: string;
  algorithm_version: string;
  value_type: "observed" | "calculated" | "assumption" | "simulation" | "model_inference" | "narrative";
  value: number | string | null;
  unit: string;
  period: string;
  geography: string;
  evidence_refs: string[];
  assumption_refs: string[];
  formula_ref: string;
  confidence: number | null;
  confidence_basis: string;
  status: OutputStatus;
  as_of: string;
  locale: "ar-SA" | "en";
  audit_ref: string;
}

export interface PersonaOutput {
  persona_id: string;
  metric: string;
  value: number | null;
  status: OutputStatus;
  evidence_refs: string[];
  note: string;
  input_scope: string;
  permitted_input_refs: string[];
}

export interface SovereignVerdict {
  sovereign_verdict: "PRELIMINARY_ONLY" | "REVISE_AND_REASSESS" | "BLOCKED_NOT_READY";
  reason: string;
  critical_truth_visible: boolean;
  determined_by: string;
  no_vote: boolean;
  advisory_consensus_visible_as_verdict: boolean;
}

export interface RemediationEnvelope {
  remediation_id: string;
  trigger_code: string;
  target: string;
  message: string;
  allowed_action: "user_edit_only" | "human_review_only";
  status: "open" | "closed";
}

export interface Blocker {
  code: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
}

export interface SourceRecord {
  source_id: string;
  publisher: string;
  route: string;
  state: SourceState;
  url: string;
  terms_url?: string;
  terms_hash?: string;
  license_snapshot_ref?: string;
  attribution?: string;
  classification?: string;
  pdpl_check?: string;
  nca_check?: string;
  lawful_purpose?: string;
  reviewer?: string;
  reviewer_decision?: string;
  reviewed_at?: string;
  notes?: Record<string, unknown>;
}

export interface SourcePolicy {
  profile_id: string;
  external_fetch_enabled: boolean;
  rule: string;
  enabled_sources: SourceRecord[];
  candidate_sources: SourceRecord[];
  reference_only: SourceRecord[];
  blocked_sources: SourceRecord[];
}

export interface SourceReviewChecklist {
  source_id: string;
  state: SourceState;
  can_enable: boolean;
  external_fetch_enabled_after_approval: boolean;
  items: Array<{
    field: string;
    label: string;
    required_for_enabled: boolean;
    status: "complete" | "missing";
  }>;
}

export interface EvidenceRegister {
  evidence_register_id: string;
  snapshot_id: string;
  source_records: SourceReviewRecord[];
  source_checklists: SourceReviewChecklist[];
  datasets: DatasetRecord[];
  transformations: TransformationRecord[];
  evidence_links: EvidenceLink[];
  quality_gates: DatasetQualityGate[];
  not_ready_reasons: string[];
  external_fetch_enabled: boolean;
}

export interface MonteCarloResult {
  status: "ready" | "not_ready";
  seed: number;
  iterations: number;
  p_pass: number | null;
  p10_profit: number | null;
  p50_profit: number | null;
  p90_profit: number | null;
  distribution_profile: string;
  correlation_ref: string;
  convergence: {
    min_iterations: number;
    actual_iterations: number;
    status: "passed" | "not_ready";
  };
  label_ar: string;
  label_en: string;
  warning: string;
}

export interface ScenarioResult {
  scenario_id: "conservative" | "baseline" | "optimistic" | string;
  startup_cost: number;
  revenue: number;
  variable_total: number;
  gross_profit: number;
  monthly_profit: number;
  annual_cashflow: number;
  ebitda: number;
  ebit: number;
  depreciation_monthly: number;
  net_operating_cashflow: number;
  break_even_units: number;
  funding_gap: number;
  funding_need_after_equity: number;
  contribution_margin: number;
  working_capital_need: number;
  initial_investment: number;
  npv: number;
  irr: number | null;
  payback_months: number | null;
  debt_service_monthly: number | null;
  dscr: number | null;
  operating_model: OperatingModel;
  capex_breakdown: CapexBreakdown;
  opex_breakdown: OpexBreakdown;
  debt_service_profile: DebtServiceProfile;
}

export interface OperatingModel {
  use_operating_capacity: boolean;
  capacity_units_per_day: number;
  operating_days_per_month: number;
  utilization_rate: number;
  monthly_units: number;
  unit_source: "operating_capacity" | "manual_monthly_units" | string;
}

export interface CapexBreakdown {
  capex_equipment: number;
  capex_fitout: number;
  capex_licenses_local: number;
  legacy_startup_cost: number;
  total_capex: number;
  depreciation_years: number;
  depreciation_monthly: number;
}

export interface OpexBreakdown {
  payroll_monthly: number;
  rent_monthly: number;
  utilities_monthly: number;
  marketing_monthly: number;
  maintenance_monthly: number;
  legacy_monthly_fixed_cost: number;
  total_monthly_opex: number;
}

export interface DebtServiceProfile {
  status: "ready" | "not_ready";
  debt_amount: number;
  monthly_payment: number | null;
  annual_debt_service: number | null;
  dscr: number | null;
  loan_grace_months: number;
  warning: string;
}

export interface SensitivityMatrix {
  matrix_id: string;
  x_axis: string;
  y_axis: string;
  cells: Array<{
    demand_factor: number;
    cost_factor: number;
    monthly_profit: number;
    npv: number;
  }>;
}

export interface OperationalSensitivity {
  matrix_id: string;
  utilization_price_cells: Array<{
    utilization_factor: number;
    price_factor: number;
    monthly_profit: number;
    dscr: number | null;
  }>;
  opex_demand_cells: Array<{
    opex_factor: number;
    demand_factor: number;
    ebitda: number;
    funding_need_after_equity: number;
  }>;
}

export interface FinanceResultSet {
  status: "ready" | "not_ready";
  baseline: ScenarioResult | null;
  scenarios: ScenarioResult[];
  sensitivity: SensitivityMatrix | null;
  operational_sensitivity: OperationalSensitivity | null;
  operating_model: OperatingModel | null;
  capex_breakdown: CapexBreakdown | null;
  opex_breakdown: OpexBreakdown | null;
  debt_service_profile: DebtServiceProfile | null;
  monte_carlo: MonteCarloResult;
  assumption_refs: string[];
}

export interface PersonaInputScope {
  persona_id: string;
  permitted_input_refs: string[];
  input_scope: string;
}

export interface DecisionCouncilResult {
  protocol_id: string;
  isolation_order: string[];
  personas: PersonaOutput[];
  verdict: SovereignVerdict;
  no_vote: boolean;
}

export interface SectorTaxonomyRecord {
  sector_id: string;
  sector_name: string;
  arabic_name: string;
  subsectors: string[];
  source_candidates: string[];
}

export interface SectorCriterion {
  criterion_id: string;
  label: string;
  sector_value: string;
  evidence_status: "supported" | "needs_evidence" | "reference_only" | string;
}

export interface SectorCriteriaSet {
  criteria_set_id: string;
  status: "supported" | "needs_evidence" | string;
  criteria: SectorCriterion[];
}

export interface InvestmentSignal {
  signal_id: string;
  label: string;
  value: string;
  basis: string;
  evidence_status: "supported" | "needs_evidence" | "reference_only" | string;
}

export interface InvestmentSignalPack {
  signal_pack_id: string;
  status: "ready" | "needs_evidence" | string;
  signals: InvestmentSignal[];
}

export interface SectorEvidenceMap {
  sector_evidence_map_id: string;
  criteria: Array<{
    criterion_id: string;
    label: string;
    evidence_status: "supported" | "needs_evidence" | "reference_only" | string;
    candidate_source_ids: string[];
    evidence_refs: string[];
  }>;
  evidence_gaps: Array<{
    criterion_id: string;
    label: string;
    reason: string;
    required_action: string;
  }>;
  approved_evidence_link_count: number;
  enabled_sector_source_count: number;
}

export interface SectorIntelligenceResult {
  sector_intelligence_id: string;
  status: "ready" | "needs_input" | string;
  taxonomy_record: {
    primary_sector_id: string;
    primary_sector: string;
    primary_sector_ar: string;
    subsector_id: string;
    activity_classification: string;
    location_scope: string;
    classification_status: string;
  };
  sector_criteria: SectorCriteriaSet;
  investment_signal_pack: InvestmentSignalPack;
  sector_evidence_map: SectorEvidenceMap;
  source_candidates: Array<{
    source_id: string;
    state: SourceState | string;
    publisher: string;
    route: string;
    can_contribute_data_now: boolean;
  }>;
  external_fetch_enabled: boolean;
  not_ready_reasons: string[];
}

export interface ExecutionMilestone {
  phase_id: "setup" | "procurement" | "staffing" | "launch" | "stabilization" | string;
  dependencies: string[];
  owner_role: string;
  estimated_duration_days: number;
  exit_criteria: string[];
}

export interface RiskExecutionConstraint {
  risk_id: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  trigger: string;
  owner_role: string;
}

export interface RiskAdvisorySummary {
  risk_advisory_summary_id: string;
  contract_id: "risk.advisory.summary.v1" | string;
  project_id: string;
  run_id: string;
  snapshot_id: string;
  status: string;
  risk_register_ref: string;
  top_risk_ids: string[];
  blocked_risk_ids: string[];
  execution_constraints: RiskExecutionConstraint[];
  source: string;
  contains_full_risk_register: false;
}

export interface ExecutionPlan {
  execution_plan_id: string;
  status: "ready" | "ready_with_warnings" | "blocked" | "unknown" | string;
  decision_ref: string;
  estimated_total_duration_days: number;
  blocked_by_gates: string[];
  blocked_by_risks: string[];
  execution_constraints: RiskExecutionConstraint[];
  finance_refs: Record<string, number | string | null | undefined>;
  risk_advisory_summary?: RiskAdvisorySummary;
  risk_advisory_refs?: {
    risk_register_ref: string;
    top_risk_ids: string[];
    blocked_risk_ids: string[];
  };
  milestones: ExecutionMilestone[];
}

export interface RiskRecord {
  risk_id: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  likelihood: "low" | "medium" | "high" | string;
  impact: string;
  trigger: string;
  mitigation: string;
  owner_role: string;
  status: "open" | "monitor" | "closed" | string;
}

export interface RiskRegister {
  risk_register_id: string;
  contract_id?: "risk.register.v1" | string;
  project_id?: string;
  run_id?: string;
  snapshot_id?: string;
  status: string;
  readiness_gate_status: string;
  risks: RiskRecord[];
  top_risks: RiskRecord[];
}

export interface ReadinessGate {
  gate_id: string;
  label: string;
  status: "passed" | "warning" | "blocked" | string;
  reasons: string[];
}

export interface ReadinessGateSet {
  gate_set_id: string;
  status: "passed" | "warning" | "blocked" | "unknown" | string;
  passed: number;
  warnings: number;
  blocked: number;
  gates: ReadinessGate[];
}

export type ReviewDecision = "draft_review" | "needs_changes" | "approved_local" | "rejected_local";

export interface DecisionMemo {
  memo_id: string;
  title: string;
  recommendation: string;
  rationale: string;
  review_status: ReviewDecision;
  next_review_action: string;
}

export interface SnapshotReviewRecord {
  review_id: string;
  snapshot_id: string;
  run_id: string;
  project_id: string;
  reviewer: string;
  decision: ReviewDecision;
  notes: string;
  created_at: string;
}

export interface DecisionPack {
  decision_pack_id: string;
  contract_id: "decision.pack.v1" | string;
  decision_pack_hash: string;
  snapshot_id: string;
  run_id: string;
  project_id: string;
  created_at: string;
  immutable_snapshot: boolean;
  memo: DecisionMemo;
  latest_review: SnapshotReviewRecord | null;
  reviews: SnapshotReviewRecord[];
  review_overlay: {
    overlay_id: string;
    base_decision_pack_hash: string;
    review_count: number;
    latest_review_id: string | null;
    overlay_hash: string;
    separate_from_snapshot_hash: boolean;
  } | null;
  finance_highlights: Record<string, number | string | null | undefined>;
  readiness_gates: ReadinessGateSet;
  top_risks: RiskRecord[];
  risk_register: RiskRegister;
  execution_plan: ExecutionPlan;
  sector_intelligence: SectorIntelligenceResult;
  evidence_ledger: EvidenceLedgerRecord[];
  evidence_coverage: EvidenceCoverageMatrix;
  transformation_lineage: TransformationLineageRecord[];
  assumptions: AssumptionRecord[];
  evidence: EvidenceRegister;
  source_governance: SourcePolicy;
  audit_lineage: {
    audit_id: string;
    owner_path: string;
    algorithm_versions: Record<string, string>;
    report_id: string;
  };
  snapshot_assembly: SnapshotAssemblyMetadata;
  external_fetch_enabled: boolean;
  ai_enabled: boolean;
}

export interface AIIntegrationRequest {
  request_id: string;
  project_id: string;
  run_id: string;
  snapshot_id: string;
  input_contract_id: "AIIntegrationInputEnvelope.v1";
  purpose: string;
  prompt_class: "explanation" | "summarization" | "translation" | "draft_narrative" | string;
  prompt_template_id: string;
  prompt_hash: string;
  requested_output_types: string[];
  context_refs: string[];
}

export interface AIIntegrationResult {
  request_id: string;
  project_id: string;
  run_id: string;
  snapshot_id: string;
  status: "disabled_no_provider" | "rejected_governance";
  provider_registry: {
    registry_id: string;
    status: "DISABLED" | "GOVERNED" | "MAINTENANCE" | "READ_ONLY" | "ACTIVE" | string;
    policy: "DENY_ALL" | "ALLOW_WHITELIST" | "GOVERNED" | string;
    providers: Array<Record<string, unknown>>;
    provider_count: number;
    registration_enabled: false;
    external_network_enabled: false;
    registration_decision_owner: "policy_engine" | string;
    security_audit: {
      event_count: number;
      stores_prompt_content: false;
      stores_provider_secrets: false;
      events: Array<Record<string, unknown>>;
    };
  };
  routing: {
    router_id: string;
    status: "disabled_no_provider" | "skipped_governance_blocked";
    provider_id: null;
    model_id: null;
    network_attempted: false;
  };
  prompt_governance: {
    policy_id: string;
    status: "allowed_but_disabled" | "blocked";
    reasons: string[];
    prompt_content_forwarded: false;
  };
  human_review_gate: {
    gate_id: string;
    status: "required_pending" | "not_applicable_blocked";
    required_for_any_future_ai_output: true;
    bypass_allowed: false;
    approved: false;
  };
  output: null;
  audit_event: Record<string, unknown>;
  security_audit_event: Record<string, unknown> | null;
  external_fetch_enabled: false;
  ai_provider_enabled: false;
}

export interface ArchitectureRuntimeComponent {
  state: string;
  [key: string]: unknown;
}

export interface ArchitectureRuntimeCheck {
  check_id: string;
  label: string;
  passed: boolean;
  evidence: string;
}

export interface ArchitectureRuntimeStatus {
  status_id: string;
  profile_id: string;
  generated_at: string;
  projection_type: "read_only_runtime_projection" | string;
  mutability: "read_only_projection" | string;
  allowed_methods: string[];
  forbidden_methods: string[];
  overall_status: "passed" | "failed" | string;
  ports: {
    frontend: number;
    api: number;
  };
  kernel: ArchitectureRuntimeComponent;
  registry: {
    registry_id: string;
    counts: {
      contracts: number;
      sockets: number;
      modules: number;
    };
    contracts: Array<Record<string, unknown>>;
    sockets: Array<Record<string, unknown>>;
    modules: Array<Record<string, unknown>>;
    external_fetch_enabled: false;
  };
  heart_controller: ArchitectureRuntimeComponent & {
    hearts: Array<{
      heart_id: string;
      role: string;
      state: string;
      health: string;
      controlled_by: string;
      activation_reason: string;
    }>;
  };
  bus_controller: ArchitectureRuntimeComponent;
  system_bus: ArchitectureRuntimeComponent;
  socket_contract_layer: ArchitectureRuntimeComponent;
  module_runtime: ArchitectureRuntimeComponent & {
    registered_handlers: string[];
    execution_count: number;
  };
  snapshot_assembly: {
    status: string;
    contract_id: string;
    socket_id: string;
    recalculates: false;
    persists: false;
    external_fetch_enabled: false;
    ai_enabled: false;
    module: Record<string, unknown>;
  };
  ai_integration_shell: {
    module_id: string;
    state: "disabled_governed" | string;
    provider_registry: {
      status: string;
      policy: string;
      providers: Array<Record<string, unknown>>;
      provider_count: number;
      external_network_enabled: false;
      security_audit: {
        event_count: number;
        stores_prompt_content: false;
        stores_provider_secrets: false;
        events: Array<Record<string, unknown>>;
      };
    };
    security_audit: {
      event_count: number;
      stores_prompt_content: false;
      stores_provider_secrets: false;
      events: Array<Record<string, unknown>>;
    };
    external_fetch_enabled: false;
    ai_provider_enabled: false;
  };
  final_aas_acceptance: {
    status: "passed" | "failed" | string;
    passed: number;
    failed: number;
    checks: ArchitectureRuntimeCheck[];
  };
  guards: {
    allows_runtime_mutation: false;
    allows_reboot: false;
    allows_registry_mutation: false;
    allows_provider_policy_mutation: false;
    allows_ai_activation: false;
    allows_module_registration: false;
    allows_heart_mutation: false;
    allows_bus_mutation: false;
    allows_socket_mutation: false;
    product_features_added: false;
    new_engines_added: false;
    external_fetch_enabled: false;
    ai_provider_enabled: false;
    allowed_frontend_port: 5194;
    allowed_api_port: 8794;
  };
}

export type ActionItemSource = "gate" | "risk" | "blocker";

export interface ActionItem {
  action_item_id: string;
  project_id: string;
  source_type: ActionItemSource;
  source_id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  status: "open" | "closed";
  message: string;
  recommended_action: string;
  snapshot_id: string | null;
  run_id: string | null;
  created_from_snapshot_at: string | null;
  notes?: string;
  updated_at?: string | null;
}

export type SourceReviewRecord = SourceRecord;

export interface RunAudit {
  audit_id: string;
  run_id: string;
  snapshot_id: string;
  profile_id: string;
  owner_path: string;
  forbidden_paths: string[];
  output_audit_refs: string[];
  algorithm_versions: Array<[string, string]>;
  source_fetch_enabled: boolean;
  acceptance_status?: "passed" | "failed";
  acceptance_id?: string;
}

export interface AcceptanceTestResult {
  test_id: string;
  title: string;
  status: "passed" | "failed";
  evidence: string;
  snapshot_id: string;
  run_id: string;
}

export interface AcceptancePack {
  acceptance_id: string;
  snapshot_id: string;
  run_id: string;
  status: "passed" | "failed";
  passed: number;
  failed: number;
  tests: AcceptanceTestResult[];
}

export interface ProjectOverview {
  project: Project;
  run: Run;
  snapshot: Snapshot;
  finance: FinanceResultSet;
  decision_council: DecisionCouncilResult;
  decision: SovereignVerdict;
  monte_carlo: MonteCarloResult;
  personas: PersonaOutput[];
  kpis: OutputEnvelope[];
  blockers: Blocker[];
  source_policy: SourcePolicy;
  assumption_book: AssumptionRecord[];
  evidence_register: EvidenceRegister;
  readiness_gates: ReadinessGateSet;
  execution_plan: ExecutionPlan;
  sector_intelligence: SectorIntelligenceResult;
  evidence_ledger: EvidenceLedgerRecord[];
  evidence_coverage: EvidenceCoverageMatrix;
  transformation_lineage: TransformationLineageRecord[];
  risk_register: RiskRegister;
  readiness: ProjectReadiness;
  acceptance: AcceptancePack;
  remediation_envelopes: RemediationEnvelope[];
  audit: RunAudit;
  snapshot_assembly: SnapshotAssemblyMetadata;
}

export interface SnapshotReportSection {
  section_id: string;
  title: string;
  body: string;
}

export interface SnapshotReport {
  report_id: string;
  snapshot_id: string;
  run_id: string;
  project_id: string;
  title: string;
  created_at: string;
  data_badge: string;
  snapshot_assembly: SnapshotAssemblyMetadata;
  summary: {
    sovereign_verdict: string;
    reason: string;
    monte_carlo_status: string;
    monte_carlo_probability: number | null;
    critical_blockers: Blocker[];
  };
  sections: SnapshotReportSection[];
  kpis: OutputEnvelope[];
  finance: FinanceResultSet;
  operating_model: OperatingModel | null;
  capex_breakdown: CapexBreakdown | null;
  opex_breakdown: OpexBreakdown | null;
  debt_service_profile: DebtServiceProfile | null;
  operational_sensitivity: OperationalSensitivity | null;
  scenarios: ScenarioResult[];
  sensitivity: SensitivityMatrix | null;
  decision_council: DecisionCouncilResult;
  personas: PersonaOutput[];
  blockers: Blocker[];
  source_governance: SourcePolicy;
  assumption_book: AssumptionRecord[];
  evidence_register: EvidenceRegister;
  readiness_gates: ReadinessGateSet;
  execution_plan: ExecutionPlan;
  sector_intelligence: SectorIntelligenceResult;
  evidence_ledger: EvidenceLedgerRecord[];
  evidence_coverage: EvidenceCoverageMatrix;
  transformation_lineage: TransformationLineageRecord[];
  risk_register: RiskRegister;
  readiness: ProjectReadiness;
  acceptance: AcceptancePack;
  audit: RunAudit;
}

export interface SnapshotReportView {
  report_id: string;
  title: string;
  snapshot_id: string;
  run_id: string;
  project_id: string;
  snapshot_assembly: SnapshotAssemblyMetadata;
  executive_summary: {
    verdict: string;
    reason: string;
    monte_carlo_probability: number | null;
    critical_blocker_count: number;
  };
  sections: SnapshotReportSection[];
  headline_kpis: OutputEnvelope[];
  scenario_table: ScenarioResult[];
  sensitivity: SensitivityMatrix | null;
  operating_model: OperatingModel | null;
  capex_breakdown: CapexBreakdown | null;
  opex_breakdown: OpexBreakdown | null;
  debt_service_profile: DebtServiceProfile | null;
  operational_sensitivity: OperationalSensitivity | null;
  assumption_book: AssumptionRecord[];
  evidence_register: EvidenceRegister;
  readiness_gates: ReadinessGateSet;
  execution_plan: ExecutionPlan;
  sector_intelligence: SectorIntelligenceResult;
  evidence_ledger: EvidenceLedgerRecord[];
  evidence_coverage: EvidenceCoverageMatrix;
  transformation_lineage: TransformationLineageRecord[];
  risk_register: RiskRegister;
  source_governance: SourcePolicy;
  review_status: ReviewDecision;
  latest_review: SnapshotReviewRecord | null;
  decision_pack_summary: {
    recommendation: string;
    readiness_status: string;
    top_risk_count: number;
    execution_status: string;
  };
  acceptance: AcceptancePack;
  audit: RunAudit;
}

export interface ProjectWorkspace {
  project: Project;
  readiness: ProjectReadiness;
  assumptions: AssumptionRecord[];
  runs: Run[];
  latest_overview: ProjectOverview | null;
  latest_report_view: SnapshotReportView | null;
  latest_review: SnapshotReviewRecord | null;
  action_items: ActionItem[];
  remediation: ProjectRemediation;
}

export interface ProjectRemediation {
  project_id: string;
  source: "latest_snapshot" | "draft_readiness" | "missing_project" | string;
  run_id: string | null;
  snapshot_id: string | null;
  items: RemediationEnvelope[];
  blockers: Blocker[];
}

export interface SnapshotComparison {
  comparison_id: string;
  snapshot_a_id: string;
  snapshot_b_id: string;
  project_id: string;
  recalculated: boolean;
  metric_deltas: Array<{
    output_id: string;
    from: number | string | null;
    to: number | string | null;
    delta: number | null;
    unit: string;
  }>;
  verdict_change: {
    from: string;
    to: string;
    changed: boolean;
  };
  assumption_changes: Array<{
    input_key: string;
    label: string;
    from: string | undefined;
    to: string | undefined;
    review_from: string | undefined;
    review_to: string | undefined;
  }>;
  acceptance_change: {
    from: string | undefined;
    to: string | undefined;
    changed: boolean;
  };
}
