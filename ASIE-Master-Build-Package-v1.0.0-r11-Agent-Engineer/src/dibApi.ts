import type { BlueprintItem, Project } from "./contracts";
import type { MarketEvidencePack } from "./contracts.dib";
import { getActiveOrganizationId, getSessionToken, handleUnauthorized } from "./session";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
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
  if (!response.ok) throw new Error(payload.error ?? `DIB request failed (${response.status})`);
  return payload;
}

function identity(prefix: string): string {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}:${suffix}`;
}

export async function buildMarketEvidencePack(
  project: Project,
  item: BlueprintItem,
  candidateSamples: Array<Record<string, unknown>> = []
): Promise<MarketEvidencePack> {
  const contextBuildId = identity("dib-market-context");
  const queryId = identity("market-query");
  const geography = [
    project.inputs.location_country ?? project.jurisdiction,
    project.inputs.location_region,
    project.inputs.location_city,
    project.inputs.location_district,
  ]
    .filter(Boolean)
    .join(" / ");
  const specification = String(
    item.market_query?.specification ??
      `${item.label ?? item.input_key}; ${item.category ?? "market_assumption"}; ${geography || "Saudi Arabia"}`
  );

  const component = {
    component_id: item.item_id ?? `item:${project.project_id}:${item.input_key}`,
    kind: "market_query",
    value: {
      query_id: queryId,
      item_id: item.item_id ?? `item:${project.project_id}:${item.input_key}`,
      specification,
      geography: geography || "Saudi Arabia",
      category: item.category ?? "market_assumption",
      unit: item.unit ?? "SAR",
      candidate_samples: candidateSamples,
      source_refs: item.evidence_refs ?? [],
    },
    source: candidateSamples.length ? "user_or_dataset_candidates" : "governed_local_simulation",
    freshness: new Date().toISOString(),
    geography: geography || "Saudi Arabia",
    sector: project.sector || project.inputs.primary_sector_id || "unknown",
    confidence: candidateSamples.length >= 5 ? "medium" : "low",
    lineage: [
      `project:${project.project_id}`,
      `blueprint-item:${item.item_id ?? item.input_key}`,
      "market.query.request.v1",
    ],
    review: "PENDING",
  };

  const response = await requestJson<{
    context?: {
      component_manifest?: Array<{ kind: string; value: MarketEvidencePack }>;
    };
    error?: string;
  }>("/api/intelligence/pre-runs", {
    method: "POST",
    body: JSON.stringify({
      project_id: project.project_id,
      context_build_id: contextBuildId,
      idempotency_key: identity("idem"),
      geography: geography || "Saudi Arabia",
      sector: project.sector || project.inputs.primary_sector_id || "unknown",
      components: [component],
    }),
  });

  const pack = response.context?.component_manifest?.find(
    (row) => row.kind === "market_evidence_pack"
  )?.value;
  if (!pack || pack.contract_id !== "market.evidence.pack.v1") {
    throw new Error(response.error ?? "market_evidence_pack_missing");
  }
  return pack;
}

export async function importDIBFile(payload: {
  file_name: string;
  file_type: string;
  file_base64?: string;
  csv_text?: string;
  pdf_text?: string;
  title?: string;
  publisher?: string;
  mapping_specs: Array<Record<string, unknown>>;
}): Promise<Record<string, unknown>> {
  const response = await requestJson<{ dataset: Record<string, unknown> }>(
    "/api/datasets/file-import",
    {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        source_id: "src_user_local_upload",
        review_status: "review_required",
        human_review_decision: "",
        classification: "user_confidential_local",
        attribution: "User-provided local file",
        pdpl_check: "local_user_controlled",
        license_snapshot_ref: "user-provided",
        terms_hash: "user-provided-local",
      }),
    }
  );
  return response.dataset;
}
