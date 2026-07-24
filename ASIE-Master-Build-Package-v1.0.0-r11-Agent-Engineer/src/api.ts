import type {
  Project,
  ProjectInputs,
  ProjectReadiness,
  ProjectRemediation,
  ProjectWorkspace,
  ProjectOverview,
  Run,
  RunAudit,
  SnapshotReport,
  SnapshotReportView,
  SnapshotComparison,
  SourceReviewChecklist,
  SourcePolicy,
  AssumptionRecord,
  ActionItem,
  AcceptancePack,
  ArchitectureRuntimeStatus,
  DatasetQualityGate,
  DatasetRecord,
  DecisionPack,
  EvidenceLink,
  EvidenceCoverageMatrix,
  EvidenceLedgerRecord,
  EvidenceRegister,
  ReviewDecision,
  SectorTaxonomyRecord,
  SnapshotReviewRecord,
  SourceReviewRecord,
  TransformationLineageRecord,
  TransformationRecord,
} from "./contracts";
import { getActiveOrganizationId, getSessionToken, handleUnauthorized } from "./session";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  const token = getSessionToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const organizationId = getActiveOrganizationId();
  if (organizationId) headers["X-ASIE-Organization-Id"] = organizationId;
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401 && token) {
    // The server rejected a token we hold: it expired or was revoked.
    handleUnauthorized();
  }
  const payload = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(payload.error ?? `تعذر الاتصال بخدمة ASIE المحلية (${response.status})`);
  }
  return payload;
}

export interface AuthUser {
  user_id: string;
  display_name: string;
  email: string;
  platform_role: string | null;
}

export interface Membership {
  organization_id: string;
  organization_name?: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
  memberships: Membership[];
  organization?: { organization_id: string; name: string };
  external_access_enabled: boolean;
}

export interface MeResponse {
  user_id: string;
  platform_role: string | null;
  memberships: Membership[];
  external_access_enabled: boolean;
}

export interface FundingProfile {
  profile_id: string;
  [key: string]: unknown;
}

export interface SectorProfile {
  profile_id?: string;
  sector_id?: string;
  [key: string]: unknown;
}

export interface ReleaseRecord {
  [key: string]: unknown;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return requestJson<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function localBootstrap(payload: {
  email: string;
  display_name: string;
  password: string;
  organization_name: string;
}): Promise<LoginResponse & { organization: { organization_id: string; name: string } }> {
  return requestJson("/api/auth/local-bootstrap", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout(): Promise<void> {
  await requestJson("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
}

export async function fetchMe(): Promise<MeResponse> {
  return requestJson<MeResponse>("/api/auth/me");
}

export async function requestPasswordRecovery(email: string): Promise<{
  accepted: boolean;
  recovery_token: string | null;
  external_delivery_enabled: boolean;
}> {
  return requestJson("/api/auth/password-recovery/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function completePasswordRecovery(recoveryToken: string, newPassword: string): Promise<{ ok?: boolean }> {
  return requestJson("/api/auth/password-recovery/complete", {
    method: "POST",
    body: JSON.stringify({ recovery_token: recoveryToken, new_password: newPassword }),
  });
}

export async function createOrganization(name: string): Promise<{ organization_id: string; name: string }> {
  const response = await requestJson<{ organization: { organization_id: string; name: string } }>("/api/organizations", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  return response.organization;
}

export async function addMembership(organizationId: string, userId: string, role: string): Promise<unknown> {
  const response = await requestJson<{ membership: unknown }>(`/api/organizations/${organizationId}/memberships`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role }),
  });
  return response.membership;
}

export async function fetchFundingProfiles(): Promise<FundingProfile[]> {
  const response = await requestJson<{ profiles: FundingProfile[] }>("/api/funding-profiles");
  return response.profiles;
}

export async function fetchSectorProfiles(): Promise<SectorProfile[]> {
  const response = await requestJson<{ profiles: SectorProfile[] }>("/api/sector-profiles");
  return response.profiles;
}

export async function fetchReleaseRecord(snapshotId: string): Promise<ReleaseRecord> {
  return requestJson<ReleaseRecord>(`/api/snapshots/${snapshotId}/release`);
}

/**
 * Open or download a snapshot-bound document with the session token attached.
 * Plain <a href> navigation cannot send the Authorization header, so every
 * document surface goes through this helper: HTML projections open in a new
 * tab from a blob URL, binary exports download as attachments.
 */
export async function openSnapshotDocument(snapshotId: string, suffix: string, mode: "open" | "download"): Promise<void> {
  const headers: Record<string, string> = {};
  const token = getSessionToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(`/api/snapshots/${snapshotId}/${suffix}`, { headers });
  if (!response.ok) {
    let message = `تعذر فتح المستند (${response.status})`;
    try {
      const payload = (await response.json()) as { error?: string };
      if (payload.error) message = payload.error;
    } catch {
      // Non-JSON error body; keep the status-based message.
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  if (mode === "download") {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `asie-funder-report-${snapshotId}.${suffix.split(".").pop()}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } else {
    window.open(url, "_blank", "noopener");
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export interface CreateProjectPayload {
  name: string;
  sector: string;
  jurisdiction: string;
  depth_profile: string;
  inputs: ProjectInputs;
}

export async function fetchArchitectureRuntimeStatus(): Promise<ArchitectureRuntimeStatus> {
  return requestJson<ArchitectureRuntimeStatus>("/api/architecture/runtime-status");
}

export async function fetchSourcePolicy(): Promise<SourcePolicy> {
  return requestJson<SourcePolicy>("/api/source-policy");
}

export async function fetchSources(): Promise<SourceReviewRecord[]> {
  const response = await requestJson<{ sources: SourceReviewRecord[] }>("/api/sources");
  return response.sources;
}

export async function fetchSourceWorkbench(): Promise<{
  sources: SourceReviewRecord[];
  checklists: SourceReviewChecklist[];
  external_fetch_enabled: boolean;
}> {
  return requestJson("/api/sources");
}

export async function fetchSectorTaxonomy(): Promise<SectorTaxonomyRecord[]> {
  const response = await requestJson<{ taxonomy: SectorTaxonomyRecord[] }>("/api/sector-taxonomy");
  return response.taxonomy;
}

export async function fetchDatasets(): Promise<DatasetRecord[]> {
  const response = await requestJson<{ datasets: DatasetRecord[] }>("/api/datasets");
  return response.datasets;
}

export async function createDataset(payload: Partial<DatasetRecord> & { rows?: Record<string, unknown>[] }): Promise<DatasetRecord> {
  const response = await requestJson<{ dataset: DatasetRecord }>("/api/datasets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.dataset;
}

export async function manualImportDataset(
  payload: Partial<DatasetRecord> & { rows?: Record<string, unknown>[]; csv_text?: string }
): Promise<DatasetRecord> {
  const response = await requestJson<{ dataset: DatasetRecord }>("/api/datasets/manual-import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.dataset;
}

export async function fileImportDataset(payload: {
  file_name: string;
  file_type?: string;
  file_base64?: string;
  csv_text?: string;
  source_id?: string;
  title?: string;
  publisher?: string;
  review_status?: string;
}): Promise<DatasetRecord> {
  const response = await requestJson<{ dataset: DatasetRecord }>("/api/datasets/file-import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.dataset;
}

export async function reviewDataset(datasetId: string, payload: Partial<DatasetRecord>): Promise<DatasetRecord> {
  const response = await requestJson<{ dataset: DatasetRecord }>(`/api/datasets/${datasetId}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.dataset;
}

export async function fetchDatasetQualityGate(datasetId: string): Promise<DatasetQualityGate> {
  return requestJson<DatasetQualityGate>(`/api/datasets/${datasetId}/quality-gate`);
}

export async function fetchDatasetTransformations(datasetId: string): Promise<TransformationRecord[]> {
  const response = await requestJson<{ transformations: TransformationRecord[] }>(
    `/api/datasets/${datasetId}/transformations`
  );
  return response.transformations;
}

export async function createDatasetTransformation(
  datasetId: string,
  payload: Partial<TransformationRecord>
): Promise<TransformationRecord> {
  const response = await requestJson<{ transformation: TransformationRecord }>(
    `/api/datasets/${datasetId}/transformations`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  return response.transformation;
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  const response = await requestJson<{ project: Project }>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.project;
}

export async function fetchProjects(): Promise<Project[]> {
  const response = await requestJson<{ projects: Project[] }>("/api/projects");
  return response.projects;
}

export async function updateProject(projectId: string, payload: Partial<CreateProjectPayload>): Promise<Project> {
  const response = await requestJson<{ project: Project }>(`/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return response.project;
}

export async function fetchProjectReadiness(projectId: string): Promise<ProjectReadiness> {
  return requestJson<ProjectReadiness>(`/api/projects/${projectId}/readiness`);
}

export async function fetchProjectAssumptions(projectId: string): Promise<AssumptionRecord[]> {
  const response = await requestJson<{ assumptions: AssumptionRecord[] }>(`/api/projects/${projectId}/assumptions`);
  return response.assumptions;
}

export async function createProjectAssumption(
  projectId: string,
  payload: Partial<AssumptionRecord>
): Promise<AssumptionRecord> {
  const response = await requestJson<{ assumption: AssumptionRecord }>(`/api/projects/${projectId}/assumptions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.assumption;
}

export async function runProject(projectId: string): Promise<ProjectOverview> {
  const response = await requestJson<{ overview: ProjectOverview }>(`/api/projects/${projectId}/runs`, {
    method: "POST",
    body: JSON.stringify({ scenario_id: "baseline" }),
  });
  return response.overview;
}

export async function fetchRunOverview(runId: string): Promise<ProjectOverview> {
  return requestJson<ProjectOverview>(`/api/runs/${runId}/overview`);
}

export async function fetchProjectRuns(projectId: string): Promise<Run[]> {
  const response = await requestJson<{ runs: Run[] }>(`/api/projects/${projectId}/runs`);
  return response.runs;
}

export async function fetchProjectWorkspace(projectId: string): Promise<ProjectWorkspace> {
  return requestJson<ProjectWorkspace>(`/api/projects/${projectId}/workspace`);
}

export async function fetchProjectEvidenceRegister(projectId: string): Promise<EvidenceRegister> {
  return requestJson<EvidenceRegister>(`/api/projects/${projectId}/evidence-register`);
}

export async function fetchProjectEvidenceLedger(projectId: string): Promise<{
  evidence_register: EvidenceRegister;
  evidence_ledger: EvidenceLedgerRecord[];
  evidence_coverage: EvidenceCoverageMatrix;
  transformation_lineage: TransformationLineageRecord[];
}> {
  return requestJson(`/api/projects/${projectId}/evidence-ledger`);
}

export async function fetchProjectTransformationLineage(projectId: string): Promise<{
  transformations: TransformationRecord[];
  transformation_lineage: TransformationLineageRecord[];
}> {
  return requestJson(`/api/projects/${projectId}/transformation-lineage`);
}

export async function fetchProjectEvidenceCoverage(projectId: string): Promise<EvidenceCoverageMatrix> {
  const response = await requestJson<{ evidence_coverage: EvidenceCoverageMatrix }>(
    `/api/projects/${projectId}/evidence-coverage`
  );
  return response.evidence_coverage;
}

export async function createEvidenceLink(
  projectId: string,
  payload: Pick<
    EvidenceLink,
    "dataset_id" | "evidence_ref" | "transformation_note" | "human_review_decision"
  > &
    Partial<Pick<EvidenceLink, "assumption_id" | "target_type" | "target_id" | "transformation_id">>
): Promise<EvidenceLink> {
  const response = await requestJson<{ evidence_link: EvidenceLink }>(`/api/projects/${projectId}/evidence-links`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.evidence_link;
}

export async function fetchProjectRemediation(projectId: string): Promise<ProjectRemediation> {
  return requestJson<ProjectRemediation>(`/api/projects/${projectId}/remediation`);
}

export async function fetchProjectActionItems(projectId: string): Promise<ActionItem[]> {
  const response = await requestJson<{ action_items: ActionItem[] }>(`/api/projects/${projectId}/action-items`);
  return response.action_items;
}

export async function updateProjectActionItem(
  projectId: string,
  actionItemId: string,
  payload: { status: "open" | "closed"; notes?: string }
): Promise<ActionItem> {
  const response = await requestJson<{ action_item: ActionItem }>(
    `/api/projects/${projectId}/action-items/${actionItemId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
  return response.action_item;
}

export async function fetchRunAudit(runId: string): Promise<RunAudit> {
  return requestJson<RunAudit>(`/api/runs/${runId}/audit`);
}

export async function fetchRunAcceptance(runId: string): Promise<AcceptancePack> {
  return requestJson<AcceptancePack>(`/api/runs/${runId}/acceptance`);
}

export async function fetchSnapshotReport(snapshotId: string): Promise<SnapshotReport> {
  return requestJson<SnapshotReport>(`/api/snapshots/${snapshotId}/report`);
}

export async function fetchSnapshot(snapshotId: string): Promise<ProjectOverview> {
  return requestJson<ProjectOverview>(`/api/snapshots/${snapshotId}`);
}

export async function compareSnapshots(snapshotAId: string, snapshotBId: string): Promise<SnapshotComparison> {
  return requestJson<SnapshotComparison>("/api/snapshots/compare", {
    method: "POST",
    body: JSON.stringify({ snapshot_a_id: snapshotAId, snapshot_b_id: snapshotBId }),
  });
}

export async function fetchSnapshotReportView(snapshotId: string): Promise<SnapshotReportView> {
  return requestJson<SnapshotReportView>(`/api/snapshots/${snapshotId}/report-view`);
}

export async function fetchDecisionPack(snapshotId: string): Promise<DecisionPack> {
  return requestJson<DecisionPack>(`/api/snapshots/${snapshotId}/decision-pack`);
}

export async function fetchSnapshotReviews(snapshotId: string): Promise<SnapshotReviewRecord[]> {
  const response = await requestJson<{ reviews: SnapshotReviewRecord[] }>(`/api/snapshots/${snapshotId}/reviews`);
  return response.reviews;
}

export async function createSnapshotReview(
  snapshotId: string,
  payload: { reviewer: string; decision: ReviewDecision; notes: string }
): Promise<SnapshotReviewRecord> {
  const response = await requestJson<{ review: SnapshotReviewRecord }>(`/api/snapshots/${snapshotId}/reviews`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.review;
}

export async function updateSourceReview(
  sourceId: string,
  payload: Partial<SourceReviewRecord>
): Promise<SourceReviewRecord> {
  const response = await requestJson<{ source: SourceReviewRecord }>(`/api/sources/${sourceId}/review`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return response.source;
}
