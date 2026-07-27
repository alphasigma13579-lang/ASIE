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

export type LiveContext = {
  contract_id: "live.intelligence.context.v1";
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
  knowledge_hits: Array<{
    record_id?: string;
    score?: number;
    chunk_text?: string;
    source_url?: string;
    source_id?: string;
    evidence_ref?: string;
    review_status?: string;
  }>;
  failures: Array<{ provider: string; error_type: string; reason: string }>;
  human_review_required: true;
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

          <section aria-labelledby="vision-title">
            <h3 id="vision-title">معرفة رؤية 2030</h3>
            <p>{context.knowledge_hits.length} مقطع مسترجع من الفهرس المعرفي.</p>
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
