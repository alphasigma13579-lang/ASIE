import { ArrowLeft, MapPinned, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { buildLiveMarketContext, type LiveMarketContext } from "./api";
import { useCustomerLanguage } from "./customerLanguage";
import { LiveIntelligenceWorkspace } from "./LiveIntelligenceWorkspace";
import { LiveMarketMap } from "./LiveMarketMap";

type LiveCockpitProps = {
  projectName?: string;
  sector?: string;
  primarySectorId?: string;
  location?: string;
  locationLabel?: string;
  projectId?: string;
  latitude?: number | null;
  longitude?: number | null;
  snapshotId?: string | null;
  signals?: StudySignals;
  onContinue?: () => void;
};

type StudySignals = {
  monthlyProfit?: number | null;
  paybackMonths?: number | null;
  fundingGap?: number | null;
  feasibilityProbability?: number | null;
  monthlyUnits?: number | null;
};

export function LiveCockpit({
  projectName,
  sector,
  primarySectorId,
  location,
  locationLabel,
  projectId,
  latitude,
  longitude,
  onContinue,
}: LiveCockpitProps) {
  const { text } = useCustomerLanguage();
  const [liveContext, setLiveContext] = useState<LiveMarketContext | null>(null);
  const [liveResearchLoading, setLiveResearchLoading] = useState(false);
  const [liveResearchUnavailable, setLiveResearchUnavailable] = useState(false);
  const contextRevisionRef = useRef(0);
  const liveResearchReady = Boolean(
    projectId
      && typeof latitude === "number" && Number.isFinite(latitude)
      && typeof longitude === "number" && Number.isFinite(longitude),
  );
  const marketContextKey = [projectId ?? "", primarySectorId ?? "", latitude ?? "", longitude ?? ""].join("|");

  useEffect(() => {
    contextRevisionRef.current += 1;
    setLiveContext(null);
    setLiveResearchUnavailable(false);
    setLiveResearchLoading(false);
  }, [marketContextKey]);

  async function searchLiveMarket(payload: { query: string; location_query: string }) {
    if (!projectId || liveResearchLoading) return;
    const requestRevision = contextRevisionRef.current;
    setLiveResearchUnavailable(false);
    setLiveResearchLoading(true);
    try {
      const result = await buildLiveMarketContext({
        project_id: projectId,
        query: payload.query,
        location_query: payload.location_query,
        sector_id: primarySectorId || "general",
      });
      if (contextRevisionRef.current === requestRevision) setLiveContext(result);
    } catch {
      if (contextRevisionRef.current === requestRevision) {
        setLiveContext(null);
        setLiveResearchUnavailable(true);
      }
    } finally {
      if (contextRevisionRef.current === requestRevision) setLiveResearchLoading(false);
    }
  }

  return (
    <section className="live-cockpit live-cockpit--r3" aria-label={text("معلومات السوق والفرص", "Market intelligence and opportunities")}>
      <header className="cockpit-intro">
        <div>
          <p className="eyebrow"><Sparkles size={15} aria-hidden="true" /> {text("معلومات مرتبطة بمشروعك", "Information linked to your project")}</p>
          <h2>{text("استكشف السوق والمنافسين", "Explore the market and competitors")}</h2>
          <p>
            {text(
              "تظهر هنا النتائج الحية فقط عند طلبها وربطها بموقع مشروع مؤكد. تعرض المنصة المصدر بوضوح، ولا تستخدم هذه المعلومات لتغيير الحسابات أو إصدار قرار نيابة عنك.",
              "Only live results requested for a confirmed project location appear here. The platform identifies each source and never uses this information to change calculations or make a decision on your behalf.",
            )}
          </p>
        </div>
        <span className={liveResearchReady ? "live-status live-status--ready" : "live-status"}>
          <MapPinned size={16} aria-hidden="true" />
          {liveResearchReady ? text("الموقع مؤكد", "Location confirmed") : text("الموقع يحتاج تأكيدًا", "Location needs confirmation")}
        </span>
      </header>

      <section className="market-context-strip" aria-label={text("سياق البحث", "Search context")}>
        <div><span>{text("المشروع", "Project")}</span><strong>{projectName || text("مشروع غير محدد", "Project not specified")}</strong></div>
        <div><span>{text("القطاع", "Sector")}</span><strong>{sector || text("قطاع غير محدد", "Sector not specified")}</strong></div>
        <div><span>{text("الموقع", "Location")}</span><strong>{locationLabel || location || text("موقع غير محدد", "Location not specified")}</strong></div>
      </section>

      {!liveResearchReady ? (
        <article className="panel market-location-required">
          <MapPinned size={22} aria-hidden="true" />
          <div>
            <h3>{text("أكمل موقع المشروع لبدء البحث الحي", "Complete the project location to start live research")}</h3>
            <p>{text("أكد الموقع من بيانات المشروع، ثم عد إلى هذه الصفحة لعرض الخريطة والبحث عن المنافسين.", "Confirm the location in project details, then return here to view the map and search for competitors.")}</p>
          </div>
        </article>
      ) : null}

      <div className="cockpit-grid cockpit-grid--r3">
        <LiveMarketMap
          projectId={projectId}
          sector={sector}
          locationLabel={locationLabel || location}
          latitude={latitude}
          longitude={longitude}
        />
        <LiveIntelligenceWorkspace
          context={liveContext}
          loading={liveResearchLoading}
          error={liveResearchUnavailable}
          locationReady={liveResearchReady}
          onSearch={searchLiveMarket}
        />
      </div>

      {onContinue ? (
        <div className="cockpit-continue">
          <div>
            <strong>{text("انتهيت من مراجعة السوق", "Market review complete")}</strong>
            <span>{text("انتقل إلى القرار المحفوظ وراجعه مع أدلته.", "Continue to the saved decision and review it with its evidence.")}</span>
          </div>
          <button className="primary-button" type="button" onClick={onContinue}>
            {text("الانتقال إلى القرار", "Continue to decision")} <ArrowLeft size={17} aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </section>
  );
}
