import { useMemo, useState } from "react";
import type { LiveMarketContext } from "./api";

type Props = {
  context?: LiveMarketContext | null;
  loading?: boolean;
  error?: boolean;
  locationReady: boolean;
  onSearch: (payload: { query: string; location_query: string }) => void;
};

export function LiveIntelligenceWorkspace({ context, loading = false, error = false, locationReady, onSearch }: Props) {
  const [query, setQuery] = useState("");
  const [locationQuery, setLocationQuery] = useState("");
  const canSearch = locationReady && query.trim().length >= 3 && locationQuery.trim().length >= 2 && !loading;

  const hasEvidence = useMemo(() => Boolean(context && (context.source_candidates.length || context.places.length || context.knowledge_hits.length)), [context]);

  return (
    <section dir="rtl" aria-labelledby="live-intelligence-title" className="asie-live-intelligence">
      <header>
        <p>ذكاء حي محكوم</p>
        <h2 id="live-intelligence-title">البحث السوقي والموقع والتوافق الوطني</h2>
        <p>
          النتائج أدلة مرشحة تحتاج مراجعة. لا تُستخدم تلقائيًا كأرقام مالية ولا تُعد قرارًا نهائيًا.
        </p>
      </header>

      <div role="status" className="capability-notice">
        لا يبدأ البحث إلا بطلبك، ويعرض الأدلة والمنافسين من المصادر المسموح بها فقط. لا يغيّر الحسابات المالية أو قرار المشروع.
      </div>

      {!locationReady ? (
        <p role="status" className="capability-notice">
          أكّد موقع المشروع أولًا من الخريطة أعلاه، ثم يمكنك بدء البحث السوقي للموقع نفسه.
        </p>
      ) : null}

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
            <p>{hasEvidence ? "لا توجد مصادر إضافية لهذا البحث." : "لم تُجمع أدلة قابلة للعرض بعد."}</p>
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
              {context.knowledge_hits.length} دليل موثق حتى {context.public_evidence_context.as_of || "تاريخ غير متاح"}.
              هذه الأدلة إرشادية وتحتاج مراجعة بشرية، ولا تضمن نجاح المشروع أو قبول التمويل.
            </p>
            {context.knowledge_hits.length === 0 ? (
              <p>لا توجد أدلة عامة صالحة وحديثة لهذا البحث.</p>
            ) : (
              <div className="public-evidence-list">
                {context.knowledge_hits.map((evidence) => (
                  <article key={evidence.display_id} className="public-evidence-card">
                    <h4>{evidence.publisher}</h4>
                    <p>{evidence.chunk_text}</p>
                    <p><strong>المنطقة:</strong> {evidence.geography}</p>
                    <p><strong>القطاع:</strong> {evidence.sector}</p>
                    <p><strong>الوحدة:</strong> {evidence.unit}</p>
                    <p><strong>الثقة:</strong> {evidence.confidence === null ? "غير متاح" : `${(evidence.confidence * 100).toFixed(0)}%`}</p>
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

          {context.partial_results_available && (
            <section aria-labelledby="failures-title">
              <h3 id="failures-title">تعذر إكمال جزء من البحث</h3>
              <p>تعذر الوصول إلى إحدى الخدمات مؤقتًا. حُفظت مدخلات البحث ويمكنك إعادة المحاولة لاحقًا؛ لا تُعرض بيانات بديلة أو افتراضية.</p>
            </section>
          )}
        </div>
      )}

      {error ? (
        <p role="alert" className="capability-notice">
          تعذر إكمال البحث مؤقتًا بسبب توقف خدمة خارجية. يمكنك إعادة المحاولة ما دمت في هذه الصفحة.
        </p>
      ) : null}
    </section>
  );
}

export default LiveIntelligenceWorkspace;
