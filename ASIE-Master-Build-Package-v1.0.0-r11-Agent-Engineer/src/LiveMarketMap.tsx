import { MapPinned, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  reverseGeocode,
  searchMarketCompetitors,
  type GoogleLocationResult,
  type MarketCompetitor,
} from "./api";
import "./live-market-map.css";

type LiveMarketMapProps = {
  projectId?: string;
  sector?: string;
  locationLabel?: string;
  latitude?: number | null;
  longitude?: number | null;
};

type RequestState = "idle" | "loading" | "ready" | "unavailable";
type BrowserMapsApi = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => unknown;
    Marker: new (options: Record<string, unknown>) => unknown;
  };
};

let browserMapsPromise: Promise<BrowserMapsApi | null> | null = null;

function loadBrowserMaps(): Promise<BrowserMapsApi | null> {
  const browserKey = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY as string | undefined;
  if (!browserKey) return Promise.resolve(null);
  if (browserMapsPromise) return browserMapsPromise;

  browserMapsPromise = new Promise((resolve) => {
    const existing = (window as Window & { google?: BrowserMapsApi }).google;
    if (existing?.maps) {
      resolve(existing);
      return;
    }
    const script = document.createElement("script");
    script.async = true;
    script.defer = true;
    script.src = "https://maps.googleapis.com/maps/api/js?libraries=marker&key=" + encodeURIComponent(browserKey);
    script.onload = () => resolve((window as Window & { google?: BrowserMapsApi }).google ?? null);
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
  return browserMapsPromise;
}

function confirmedCoordinate(value: number | null | undefined, minimum: number, maximum: number) {
  return typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= maximum;
}

function competitorName(competitor: MarketCompetitor) {
  return competitor.displayName?.text || competitor.formattedAddress || "منشأة مسجلة في المصدر";
}

export function LiveMarketMap({ projectId, sector, locationLabel, latitude, longitude }: LiveMarketMapProps) {
  const [state, setState] = useState<RequestState>("idle");
  const [address, setAddress] = useState<GoogleLocationResult | null>(null);
  const [competitors, setCompetitors] = useState<MarketCompetitor[]>([]);
  const [mapUnavailable, setMapUnavailable] = useState(false);
  const mapElement = useRef<HTMLDivElement | null>(null);

  const hasConfirmedLocation =
    confirmedCoordinate(latitude, -90, 90) && confirmedCoordinate(longitude, -180, 180);
  const canRefresh = Boolean(projectId && sector?.trim() && hasConfirmedLocation);

  useEffect(() => {
    if (state !== "ready" || !mapElement.current || !hasConfirmedLocation) return;
    let disposed = false;
    loadBrowserMaps().then((google) => {
      if (disposed) return;
      if (!google?.maps) {
        setMapUnavailable(true);
        return;
      }
      const center = { lat: latitude as number, lng: longitude as number };
      const map = new google.maps.Map(mapElement.current as HTMLElement, {
        center,
        zoom: 14,
        mapId: import.meta.env.VITE_GOOGLE_MAP_ID as string | undefined,
        disableDefaultUI: false,
        gestureHandling: "cooperative",
      });
      new google.maps.Marker({ map, position: center, title: "موقع المشروع المؤكد" });
      competitors.forEach((competitor) => {
        const competitorLocation = competitor.location;
        if (!confirmedCoordinate(competitorLocation?.latitude, -90, 90) || !confirmedCoordinate(competitorLocation?.longitude, -180, 180)) return;
        new google.maps.Marker({
          map,
          position: { lat: competitorLocation.latitude, lng: competitorLocation.longitude },
          title: competitorName(competitor),
        });
      });
    });
    return () => {
      disposed = true;
    };
  }, [state, competitors, hasConfirmedLocation, latitude, longitude]);

  async function refreshMarketContext() {
    if (!canRefresh || !projectId || !sector || latitude === null || latitude === undefined || longitude === null || longitude === undefined) return;
    setState("loading");
    setMapUnavailable(false);
    try {
      const [addressResponse, competitorsResponse] = await Promise.all([
        reverseGeocode({ project_id: projectId, latitude, longitude }),
        searchMarketCompetitors({
          project_id: projectId,
          query: sector,
          latitude,
          longitude,
          radius_meters: 3000,
        }),
      ]);
      setAddress(addressResponse.result.results[0] ?? null);
      setCompetitors(competitorsResponse.competitors);
      setState("ready");
    } catch {
      setAddress(null);
      setCompetitors([]);
      setState("unavailable");
    }
  }

  return (
    <article className="live-market-map" aria-label="خريطة المنافسين للموقع المؤكد">
      <header className="live-market-map__heading">
        <div>
          <MapPinned size={20} aria-hidden="true" />
          <div>
            <span>المنافسة في النطاق</span>
            <strong>خريطة ومنافسون من المصدر المسموح بعد طلبك</strong>
          </div>
        </div>
        <small>لا تحفظ المنصة موقع الجهاز الخام</small>
      </header>

      <p className="live-market-map__context">
        {locationLabel || "الموقع غير مسمى بعد"} · {sector || "التصنيف مطلوب"}
      </p>

      <button
        type="button"
        className="live-market-map__refresh"
        disabled={!canRefresh || state === "loading"}
        onClick={refreshMarketContext}
      >
        <RefreshCw size={16} aria-hidden="true" />
        {state === "loading" ? "جارٍ تحديث سياق السوق…" : "تحديث المنافسين للموقع المؤكد"}
      </button>

      {!canRefresh ? (
        <p className="live-market-map__notice" role="status">
          ثبّت موقع المشروع والتصنيف أولاً. لا يبدأ أي طلب للخدمة أو تحميل للخريطة قبل ذلك.
        </p>
      ) : null}

      {state === "unavailable" ? (
        <p className="live-market-map__notice live-market-map__notice--unavailable" role="alert">
          الخدمة الخارجية متوقفة مؤقتًا. حُفظت مدخلاتك، ويمكنك إعادة المحاولة لاحقًا. لا توجد بيانات بديلة أو تجريبية هنا.
        </p>
      ) : null}

      {state === "ready" ? (
        <div className="live-market-map__results">
          <p className="live-market-map__source">
            {address?.formattedAddress || locationLabel || "الموقع المؤكد"} · المصدر: Google Maps/Places عند التفعيل
          </p>
          <div ref={mapElement} className="live-market-map__canvas" aria-label="خريطة Google للموقع والمنافسين" />
          {mapUnavailable ? (
            <p className="live-market-map__notice" role="status">
              تعذر تحميل سطح الخريطة في المتصفح؛ تبقى نتائج المصدر أدناه متاحة ولا يجري استبدالها بمحاكاة.
            </p>
          ) : null}
          <section className="live-market-map__list" aria-label="المنافسون من المصدر">
            <h3>المنشآت المطابقة في نطاق البحث</h3>
            {competitors.length ? (
              <ul>
                {competitors.map((competitor) => (
                  <li key={competitor.id}>
                    <div>
                      <strong>{competitorName(competitor)}</strong>
                      <span>{competitor.primaryType || "تصنيف غير معلن"} · {competitor.businessStatus || "حالة غير معلنة"}</span>
                      {competitor.formattedAddress ? <small>{competitor.formattedAddress}</small> : null}
                    </div>
                    {competitor.googleMapsUri ? (
                      <a href={competitor.googleMapsUri} target="_blank" rel="noreferrer">
                        فتح في Google Maps
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p>لم يعثر المصدر على منشآت مطابقة في نطاق البحث الحالي.</p>
            )}
          </section>
        </div>
      ) : null}
    </article>
  );
}
