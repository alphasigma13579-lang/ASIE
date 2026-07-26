import { getActiveOrganizationId, getSessionToken, handleUnauthorized } from "./session";

export const DIB_UI_LIVE_API_WIRING_ID = "DIB-LIVE-002J-UI-LIVE-API-WIRING-v1";
export const DIB_SESSION_CONTINUITY_UI_ID = "DIB-COMPLETION-PACKAGE-A-SESSION-CONTINUITY-v1";

async function requestDibJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  const token = getSessionToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const organizationId = getActiveOrganizationId();
  if (organizationId) headers["X-ASIE-Organization-Id"] = organizationId;
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401 && token) handleUnauthorized();
  const payload = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(payload.error ?? `تعذر الاتصال بواجهة DIB (${response.status})`);
  }
  return payload;
}

export type DIBItemState =
  | "UNKNOWN"
  | "NOT_APPLICABLE"
  | "USER_PROVIDED"
  | "FILE_IMPORTED"
  | "AI_SUGGESTED"
  | "MARKET_ESTIMATED"
  | "EVIDENCE_VERIFIED"
  | "HUMAN_APPROVED"
  | "REJECTED"
  | "INTENTIONAL_ZERO";

export interface DIBRouteRef {
  method: string;
  path: string;
  purpose?: string;
  mounting?: string;
  source_api?: string;
}

export interface DIBStatusPayload {
  api_id?: string;
  mounting_id?: string;
  local_gateway_integration_id?: string;
  session_continuity_id?: string;
  status: string;
  route_count: number;
  routes: DIBRouteRef[];
  external_fetch_enabled: boolean;
  ai_provider_enabled: boolean;
  finance_wiring_enabled: boolean;
  snapshot_wiring_enabled: boolean;
  [key: string]: unknown;
}

export interface DIBSessionRecord {
  session_id: string;
  project_id: string;
  status: string;
  project_profile: Record<string, unknown>;
  current_blueprint_id?: string | null;
  approved_manifest_id?: string | null;
  validation_gate_id?: string | null;
  current_blueprint?: DIBBlueprintPayload;
  approved_manifest?: DIBApprovedManifestPayload;
  validation_gate?: DIBValidationGatePayload;
  created_at?: string;
  updated_at?: string;
  external_fetch_enabled: boolean;
  ai_provider_enabled: boolean;
  finance_wiring_enabled: boolean;
  snapshot_wiring_enabled: boolean;
  [key: string]: unknown;
}

export interface DIBSessionQueryResponse {
  sessions: DIBSessionRecord[];
  latest_session?: DIBSessionRecord | null;
  resume_available: boolean;
  project_id: string;
  session_continuity_id?: string;
  finance_wiring_enabled: boolean;
  snapshot_wiring_enabled: boolean;
  [key: string]: unknown;
}

export interface DIBBlueprintItem {
  item_id?: string;
  input_key: string;
  label: string;
  value?: number | string | null;
  unit?: string;
  value_state: DIBItemState;
  value_source?: string;
  source_type?: string;
  confidence?: number;
  evidence_refs?: string[];
  review_status?: string;
  required?: boolean;
  reason?: string;
  revision?: number;
  [key: string]: unknown;
}

export interface DIBBlueprintPayload {
  contract_id: "dynamic.input.blueprint.v1" | "dib.draft.revision.v1" | string;
  blueprint_id: string;
  project_id: string;
  items: DIBBlueprintItem[];
  revision?: number;
  created_at?: string;
  [key: string]: unknown;
}

export interface DIBApprovedManifestPayload {
  contract_id: "approved.input.manifest.v1" | string;
  manifest_id: string;
  project_id: string;
  blueprint_id: string;
  status: "approved" | "blocked" | string;
  items: DIBBlueprintItem[];
  normalized_inputs?: Record<string, number>;
  blockers?: Array<{ code: string; severity: string; message: string }>;
  [key: string]: unknown;
}

export interface DIBValidationGatePayload {
  contract_id: "manifest.validation.v1" | string;
  gate_id: string;
  manifest_id?: string;
  status: "passed" | "blocked" | string;
  blockers?: Array<{ code: string; severity: string; message: string }>;
  [key: string]: unknown;
}

export interface DIBPersistedEntity<TPayload> {
  payload: TPayload;
  payload_hash?: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface DIBEventRecord {
  event_id: string;
  session_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  payload_hash: string;
  created_at: string;
  payload?: Record<string, unknown>;
}

export async function fetchDIBStatus(): Promise<DIBStatusPayload> {
  const response = await requestDibJson<{ dib_api?: DIBStatusPayload; status?: DIBStatusPayload }>("/api/dib/status");
  return response.dib_api ?? response.status ?? (response as unknown as DIBStatusPayload);
}

export async function startDIBSession(projectProfile: Record<string, unknown>): Promise<DIBSessionRecord> {
  const response = await requestDibJson<{ session: DIBSessionRecord }>("/api/dib/sessions", {
    method: "POST",
    body: JSON.stringify({ project_profile: projectProfile }),
  });
  return response.session;
}

export async function fetchDIBSessionsForProject(projectId: string): Promise<DIBSessionRecord[]> {
  const response = await requestDibJson<DIBSessionQueryResponse>(
    `/api/dib/sessions?project_id=${encodeURIComponent(projectId)}`
  );
  return response.sessions;
}

export async function fetchLatestDIBSessionForProject(projectId: string): Promise<DIBSessionRecord | null> {
  const response = await requestDibJson<DIBSessionQueryResponse>(
    `/api/dib/sessions?project_id=${encodeURIComponent(projectId)}&limit=1`
  );
  return response.latest_session ?? response.sessions[0] ?? null;
}

export async function fetchDIBSession(sessionId: string): Promise<DIBSessionRecord> {
  const response = await requestDibJson<{ session: DIBSessionRecord }>(`/api/dib/sessions/${sessionId}`);
  return response.session;
}

export async function saveDIBBlueprint(
  sessionId: string,
  payload: {
    source?: string;
    intake_payload?: { file_name: string; rows: Array<Record<string, unknown>> };
    existing_items?: DIBBlueprintItem[];
    blueprint?: DIBBlueprintPayload;
  }
): Promise<DIBPersistedEntity<DIBBlueprintPayload>> {
  const response = await requestDibJson<{ blueprint: DIBPersistedEntity<DIBBlueprintPayload> }>(
    `/api/dib/sessions/${sessionId}/blueprints`,
    { method: "POST", body: JSON.stringify(payload) }
  );
  return response.blueprint;
}

export async function saveDIBApprovedManifest(
  sessionId: string,
  manifest?: DIBApprovedManifestPayload
): Promise<DIBPersistedEntity<DIBApprovedManifestPayload>> {
  const response = await requestDibJson<{ approved_manifest: DIBPersistedEntity<DIBApprovedManifestPayload> }>(
    `/api/dib/sessions/${sessionId}/approved-manifests`,
    { method: "POST", body: JSON.stringify(manifest ? { manifest } : {}) }
  );
  return response.approved_manifest;
}

export async function saveDIBValidationGate(
  sessionId: string,
  gate?: DIBValidationGatePayload
): Promise<DIBPersistedEntity<DIBValidationGatePayload>> {
  const response = await requestDibJson<{ validation_gate: DIBPersistedEntity<DIBValidationGatePayload> }>(
    `/api/dib/sessions/${sessionId}/validation-gates`,
    { method: "POST", body: JSON.stringify(gate ? { gate } : {}) }
  );
  return response.validation_gate;
}

export async function fetchDIBEvents(sessionId: string): Promise<DIBEventRecord[]> {
  const response = await requestDibJson<{ events: DIBEventRecord[] }>(`/api/dib/sessions/${sessionId}/events`);
  return response.events;
}

export async function closeDIBSession(sessionId: string): Promise<DIBSessionRecord> {
  const response = await requestDibJson<{ session: DIBSessionRecord }>(`/api/dib/sessions/${sessionId}/close`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return response.session;
}
