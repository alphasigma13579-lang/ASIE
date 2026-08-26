import { useMemo, useState } from "react";

export type ProviderStatus = "disabled" | "configured" | "missing_secret" | "live" | "failed";

export type LiveIntelligenceSnapshot = {
  contract_id: "live.intelligence.provider.status.v1";
  external_fetch_enabled: boolean;
  providers: Record<
    string,
    {
      status: ProviderStatus;
      capability: string;
      secret_present: boolean;
      secret_value_exposed: false;
    }
  >;
};

export type PublicEvidence = {
  record_id: string;
  score: number;
  chunk_text: string;
  source_id: string;
  publisher: string;
  authority: "saudi_official" | "international_official";
  source_url: string;
  license_id: string;
  license_ref: string;
  attribution: string;
  sector: string;
  geography: string;
  language: string;
  published_at: string;
  retrieved_at: string;
  content_sha256: string;
  version: number;
  freshness_days: number;
  fresh_until: string;
  expires_at: string;
  unit: string;
  confidence: number;
  evidence_ref: string;
  admission_status: "auto_admitted_official_open";
  data_classification: "public";
  source_of_truth: false;
};

export type PublicEvidenceContext = {
  contract_id: "public-knowledge-evidence.v1";
  status: "ready" | "ready_with_gaps" | "not_ready";
  as_of: string;
  evidence: PublicEvidence[];
  gaps: Array<{ record_id: string; reason: string }>;
  permitted_uses: string[];
  claims_project_success: false;
  claims_funding_acceptance: false;
  source_of_truth: false;
  snapshot_eligible: false;
  requires_separate_assumption_admission_for_finance: true;
};

export type LiveContext = {
  contract_id: "live.intelligence.context.v1";
  project_id: string;
  organization_id: string;
  status: "review_required" | "failed";
  source_candidates: Array<{
    candidate_id: string;
    provider: string;
    title: string;
    url: string;
    summary: string;
    review_status: "review_required";
  }>;
  places: Array<{
    place_id?: string;
    display_name?: unknown;
    formatted_address?: string;
    primary_type?: string;
    business_status?: string;
    google_maps_uri?: string;
  }>;
  knowledge_hits: Array<PublicEvidence & { review_status: "review_required" }>;
  public_evidence_context: PublicEvidenceContext;
  failures: Array<{ provider: string; error_type: string; reason: string }>;
  human_review_required: true;
  eligible_for_controlled_assumptions: false;
  controlled_numbers: unknown[];
  finance_mutated: false;
  snapshot_mutated: false;
  context_hash: string;
};

type Props = {
  providerStatus: LiveIntelligenceSnapshot;
  context?: LiveContext | null;
  loading?: boolean;
  onSearch: (payload: { query: string; location_query: string }) => void;
};

const labels: Record<string, string> = {
  deepseek: "DeepSeek",
  tavily: "Tavily",
  google_maps_platform: "Google Maps",
  pinecone: "Pinecone",
};

const statusText: Record<ProviderStatus, string> = {
  disabled: "معطّل",
  configured: "مهيأ",
  missing_secret: "المفتاح مفقود",
  live: "حي",
  failed: "فشل",
};

export function LiveIntelligenceWorkspace({ providerStatus, context, loading = false, onSearch }: Props) {
  const [query, setQuery] = useState("");
  const [locationQuery, setLocationQuery] = useState("");
  const canSearch = query.trim().length >= 3 && locationQuery.trim().length >= 2 && !loading;

  const providerRows = useMemo(() => Object.entries(providerStatus.providers), [providerStatus.providers]);

  return (
    <section dir="rtl" aria-labelledby="live-intelligence-title" className="asie-live-intelligence">
      <header>
        <p>ذكاء حي محكوم</p>
        <h2 id="live-intelligence-title">البحث السوقي والموقع والتوافق الوطني</h2>
        <p>
          النتائج أدلة مرشحة تحتاج مراجعة. لا تُستخدم تلقائيًا كأرقام مالية ولا تُعد قرارًا نهائيًا.
        </p>
      </header>

      <div className="provider-grid" aria-label="حالة المزوّدين">
        {providerRows.map(([providerId, provider]) => (
          <article key={providerId} className={`provider-card provider-${provider.status}`}>
            <strong>{labels[providerId] ?? providerId}</strong>
            <span>{statusText[provider.status]}</span>
            <small>{provider.capability}</small>
          </article>
        ))}
      </div>

      {!providerStatus.external_fetch_enabled && (
        <div role="status" className="capability-notice">
          الاتصال الخارجي معطّل حاليًا. لن تُعرض النتائج على أنها حية حتى يتم تفعيل سياسة الشبكة واجتياز التحقق.
        </div>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (canSearch) onSearch({ query: query.trim(), location_query: locationQuery.trim() });
        }}
      >
        <label>
          ما الذي تريد بحثه؟
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="مثال: سوق مطاعم الشاورما في الرياض" />
        </label>
        <label>
          الموقع أو نوع الأماكن المطلوبة
          <input value={locationQuery} onChange={(event) => setLocationQuery(event.target.value)} placeholder="مثال: مطاعم شاورما قرب حي الياسمين" />
        </label>
        <button type="submit" disabled={!canSearch}>
          {loading ? "جارٍ جمع الأدلة…" : "ابدأ البحث الحي"}
        </button>
      </form>

      {context && (
        <div className="live-results">
          <div role="status" className="review-required">
            الحالة: {context.status === "review_required" ? "تحتاج مراجعة بشرية" : "لم تتوفر نتائج قابلة للمراجعة"}
          </div>

          <section aria-labelledby="sources-title">
            <h3 id="sources-title">مصادر الويب المرشحة</h3>
            {context.source_candidates.length === 0 ? (
              <p>لا توجد مصادر.</p>
            ) : (
              context.source_candidates.map((source) => (
                <article key={source.candidate_id}>
                  <h4>{source.title || "مصدر بلا عنوان"}</h4>
                  <p>{source.summary}</p>
                  <a href={source.url} target="_blank" rel="noreferrer">فتح المصدر</a>
                  <span>يحتاج مراجعة</span>
                </article>
              ))
            )}
          </section>

          <section aria-labelledby="places-title">
            <h3 id="places-title">الأماكن والمنافسون المحتملون</h3>
            <p>{context.places.length} نتيجة مكانية. تُحفظ هوية المكان فقط وفق سياسة الاستخدام.</p>
          </section>

          <section aria-labelledby="public-evidence-title">
            <h3 id="public-evidence-title">الأدلة الاقتصادية العامة</h3>
            <p>
              {context.knowledge_hits.length} دليل موثق حتى {context.public_evidence_context.as_of}.
              هذه الأدلة إرشادية وتحتاج مراجعة بشرية، ولا تضمن نجاح المشروع أو قبول التمويل.
            </p>
            {context.knowledge_hits.length === 0 ? (
              <p>لا توجد أدلة عامة صالحة وحديثة لهذا البحث.</p>
            ) : (
              <div className="public-evidence-list">
                {context.knowledge_hits.map((evidence) => (
                  <article key={evidence.record_id} className="public-evidence-card">
                    <h4>{evidence.publisher}</h4>
                    <p>{evidence.chunk_text}</p>
                    <p><strong>المنطقة:</strong> {evidence.geography}</p>
                    <p><strong>القطاع:</strong> {evidence.sector}</p>
                    <p><strong>الوحدة:</strong> {evidence.unit}</p>
                    <p><strong>الثقة:</strong> {(evidence.confidence * 100).toFixed(0)}%</p>
                    <p><strong>تاريخ الجلب:</strong> {evidence.retrieved_at}</p>
                    <p><strong>صالح حتى:</strong> {evidence.fresh_until}</p>
                    <a href={evidence.source_url} target="_blank" rel="noreferrer">
                      فتح المصدر الرسمي
                    </a>
                  </article>
                ))}
              </div>
            )}
          </section>

          {context.failures.length > 0 && (
            <section aria-labelledby="failures-title">
              <h3 id="failures-title">مزوّدون لم يستجيبوا</h3>
              {context.failures.map((failure) => (
                <p key={`${failure.provider}-${failure.error_type}`}>{failure.provider}: {failure.error_type}</p>
              ))}
            </section>
          )}
        </div>
      )}
    </section>
  );
}

export default LiveIntelligenceWorkspace;
