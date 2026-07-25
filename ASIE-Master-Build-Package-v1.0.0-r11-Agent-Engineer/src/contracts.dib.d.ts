import "./contracts";

declare module "./contracts" {
  interface BlueprintItem {
    finance_key?: string;
    required?: boolean;
    market_query?: Record<string, unknown>;
    evidence_pack?: MarketEvidencePack | null;
    review_decision?: "PENDING" | "approved" | "rejected" | string;
    import_source?: Record<string, unknown> | null;
  }

  interface ProjectInputs {
    blueprint_id?: string;
    blueprint_revision_id?: string;
    blueprint_revision?: number;
    blueprint_revisions?: DIBRevision[];
    approved_input_manifest?: ClientApprovedInputManifest;
    approved_input_manifests?: ClientApprovedInputManifest[];
    template_id?: string;
    interview_answers?: Record<string, unknown>;
    start_type?: "idea_only" | "data_intake" | "mixed" | string;
  }
}

export interface MarketEvidencePack {
  evidence_pack_id: string;
  contract_id: "market.evidence.pack.v1";
  query_id: string;
  project_id: string;
  item_id: string;
  specification: string;
  geography: string;
  category: string;
  unit: string;
  samples: Array<{
    sample_id: string;
    value: number;
    unit: string;
    weight: number;
    source_ref: string;
    date: string;
  }>;
  p25: number;
  p75: number;
  weighted_median: number;
  sample_count: number;
  outlier_report: Record<string, unknown>;
  confidence: string;
  data_mode: "user_or_dataset_samples" | "demo_simulated_external" | string;
  evidence_refs: string[];
  review_decision: "PENDING" | "approved" | "rejected" | string;
  selected_value: number | null;
  created_at: string;
  content_hash: string;
  external_fetch_enabled: false;
  ai_provider_used: false;
  decision_authority: "candidate_assumption_only";
}

export interface DIBRevision {
  contract_id: "blueprint.revision.v1";
  blueprint_id: string;
  project_id: string;
  template_id: string;
  revision_id: string;
  revision: number;
  parent_revision_id: string | null;
  start_type: string;
  items: import("./contracts").BlueprintItem[];
  interview_answers: Record<string, unknown>;
  created_at: string;
  content_hash: string;
}

export interface ClientApprovedInputManifest {
  contract_id: "approved.input.manifest.v1";
  manifest_id: string;
  project_id: string;
  version: number;
  status: "approved" | "blocked";
  blueprint_id: string;
  blueprint_revision_id: string;
  template_id: string;
  items: import("./contracts").BlueprintItem[];
  normalized_inputs: Record<string, unknown>;
  blockers: Array<{ code: string; severity: string; message: string }>;
  created_at: string;
  content_hash: string;
}
