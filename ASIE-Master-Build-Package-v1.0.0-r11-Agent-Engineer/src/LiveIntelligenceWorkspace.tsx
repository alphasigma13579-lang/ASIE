import { useMemo, useState } from "react";
import type { LiveMarketContext } from "./api";
import { customerNarrativeText, customerStatusText, useCustomerLanguage } from "./customerLanguage";

type Props = {
  context?: LiveMarketContext | null;
  loading?: boolean;
  error?: boolean;
  locationReady: boolean;
  onSearch: (payload: { query: string; location_query: string }) => void;
};

function formatSourceDate(value: string | null | undefined, locale: "ar" | "en", fallback: string) {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-SA" : "en-GB", { dateStyle: "medium" }).format(date);
}

export function LiveIntelligenceWorkspace({ context, loading = false, error = false, locationReady, onSearch }: Props) {
  const { locale, direction, text } = useCustomerLanguage();
  const [query, setQuery] = useState("");
  const [locationQuery, setLocationQuery] = useState("");
  const canSearch = locationReady && query.trim().length >= 3 && locationQuery.trim().length >= 2 && !loading;

  const hasEvidence = useMemo(() => Boolean(context && (context.source_candidates.length || context.places.length || context.knowledge_hits.length)), [context]);

  return (
    <section dir={direction} aria-labelledby="live-intelligence-title" className="asie-live-intelligence">
      <header>
        <p>{text("بحث حي محكوم", "Governed live research")}</p>
        <h2 id="live-intelligence-title">
          {text("البحث السوقي والموقع والسياق الوطني", "Market, location, and national-context research")}
        </h2>
        <p>
          {text(
            "النتائج أدلة مرشحة تحتاج مراجعة. لا تُستخدم تلقائيًا كأرقام مالية ولا تُعد قرارًا نهائيًا.",
            "Results are evidence candidates that require review. They are never used automatically as financial figures or treated as a final decision.",
          )}
        </p>
      </header>

      <div role="status" className="capability-notice">
        {text(
          "لا يبدأ البحث إلا بطلبك، ويعرض الأدلة والمنافسين من المصادر المسموح بها فقط. لا يغيّر الحسابات المالية أو قرار المشروع.",
          "Research starts only when you request it and shows evidence and competitors from approved sources only. It does not change financial calculations or the project decision.",
        )}
      </div>

      {!locationReady ? (
        <p role="status" className="capability-notice">
          {text(
            "أكّد موقع المشروع أولًا من الخريطة أعلاه، ثم يمكنك بدء البحث السوقي للموقع نفسه.",
            "Confirm the project location on the map above, then start market research for that same location.",
          )}
        </p>
      ) : null}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (canSearch) onSearch({ query: query.trim(), location_query: locationQuery.trim() });
        }}
      >
        <label>
          {text("ما الذي تريد بحثه؟", "What would you like to research?")}
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={text("مثال: سوق مطاعم الشاورما في الرياض", "Example: shawarma restaurant market in Riyadh")} />
        </label>
        <label>
          {text("الموقع أو نوع الأماكن المطلوبة", "Location or type of places")}
          <input value={locationQuery} onChange={(event) => setLocationQuery(event.target.value)} placeholder={text("مثال: مطاعم شاورما قرب حي الياسمين", "Example: shawarma restaurants near Al Yasmin district")} />
        </label>
        <button type="submit" disabled={!canSearch}>
          {loading ? text("جارٍ جمع المعلومات…", "Gathering information…") : text("ابدأ البحث الحي", "Start live research")}
        </button>
      </form>

      {context && (
        <div className="live-results">
          <div role="status" className="review-required">
            {text("الحالة", "Status")}: {customerStatusText(context.status, locale)}
          </div>

          <section aria-labelledby="sources-title">
            <h3 id="sources-title">{text("مصادر الويب المقترحة", "Suggested web sources")}</h3>
            {context.source_candidates.length === 0 ? (
            <p>{hasEvidence ? text("لا توجد مصادر إضافية لهذا البحث.", "No additional sources were found for this research.") : text("لم تُجمع معلومات قابلة للعرض بعد.", "No displayable information has been gathered yet.")}</p>
            ) : (
              context.source_candidates.map((source) => (
                <article key={source.candidate_id}>
                  <h4>{source.title || text("مصدر بلا عنوان", "Untitled source")}</h4>
                  <p>{customerNarrativeText(source.summary, locale)}</p>
                  <a href={source.url} target="_blank" rel="noreferrer">{text("فتح المصدر", "Open source")}</a>
                  <span>{text("يحتاج مراجعة", "Needs review")}</span>
                </article>
              ))
            )}
          </section>

          <section aria-labelledby="places-title">
            <h3 id="places-title">{text("الأماكن والمنافسون المحتملون", "Places and potential competitors")}</h3>
            <p>{context.places.length} {text("نتيجة مكانية من المصدر المعتمد.", "location results from the approved source.")}</p>
          </section>

          <section aria-labelledby="public-evidence-title">
            <h3 id="public-evidence-title">{text("المعلومات الاقتصادية العامة", "Public economic information")}</h3>
            <p>
              {context.knowledge_hits.length} {text("مصدر موثق حتى", "documented sources as of")} {formatSourceDate(context.public_evidence_context.as_of, locale, text("تاريخ غير متاح", "date unavailable"))}.
              {text("هذه المعلومات إرشادية وتحتاج مراجعة بشرية، ولا تضمن نجاح المشروع أو قبول التمويل.", "This information is for guidance and requires human review. It does not guarantee project success or funding approval.")}
            </p>
            {context.knowledge_hits.length === 0 ? (
              <p>{text("لا توجد معلومات عامة صالحة وحديثة لهذا البحث.", "No valid and current public information is available for this research.")}</p>
            ) : (
              <div className="public-evidence-list">
                {context.knowledge_hits.map((evidence) => (
                  <article key={evidence.display_id} className="public-evidence-card">
                    <h4>{evidence.publisher}</h4>
                    <p><strong>{text("مقتطف من المصدر بلغته الأصلية:", "Source excerpt in its original language:")}</strong></p>
                    <blockquote dir="auto">{evidence.chunk_text}</blockquote>
                    
                    <p><strong>{text("درجة الثقة:", "Confidence:")}</strong> {evidence.confidence === null ? text("غير متاح", "Not available") : `${(evidence.confidence * 100).toFixed(0)}%`}</p>
                    <p><strong>{text("تاريخ الاسترجاع:", "Retrieved:")}</strong> {formatSourceDate(evidence.retrieved_at, locale, text("غير متاح", "Not available"))}</p>
                    <p><strong>{text("صالح حتى:", "Valid until:")}</strong> {formatSourceDate(evidence.fresh_until, locale, text("غير متاح", "Not available"))}</p>
                    <a href={evidence.source_url} target="_blank" rel="noreferrer">
                      {text("فتح المصدر الرسمي", "Open official source")}
                    </a>
                  </article>
                ))}
              </div>
            )}
          </section>

          {context.partial_results_available && (
            <section aria-labelledby="failures-title">
              <h3 id="failures-title">{text("تعذر إكمال جزء من البحث", "Part of the research could not be completed")}</h3>
              <p>{text("تعذر الوصول إلى أحد المصادر مؤقتًا. حُفظت مدخلات البحث ويمكنك إعادة المحاولة لاحقًا؛ لن تُعرض بيانات بديلة.", "One source is temporarily unavailable. Your research inputs are preserved and you can try again later; no substitute data will be shown.")}</p>
            </section>
          )}
        </div>
      )}

      {error ? (
        <p role="alert" className="capability-notice">
          {text("تعذر إكمال البحث مؤقتًا. حُفظت مدخلاتك ويمكنك إعادة المحاولة من هذه الصفحة.", "Research could not be completed temporarily. Your inputs are preserved and you can retry from this page.")}
        </p>
      ) : null}
    </section>
  );
}

export default LiveIntelligenceWorkspace;
