import { MapPinned, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  reverseGeocode,
  searchMarketCompetitors,
  type GoogleLocationResult,
  type MarketCompetitor,
} from "./api";
import { useCustomerLanguage } from "./customerLanguage";
import "./live-market-map.css";

type LiveMarketMapProps = {
  projectId?: string;
  sector?: string;
  sectorLabel?: string;
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
  const browserMapsEnabled = import.meta.env.VITE_ASIE_LIVE_BROWSER_MAPS_ENABLED === "true";
  if (!browserMapsEnabled || !browserKey) return Promise.resolve(null);
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

function competitorName(competitor: MarketCompetitor, fallback: string) {
  return competitor.displayName?.text || competitor.formattedAddress || fallback;
}

function distanceKilometers(
  originLatitude: number,
  originLongitude: number,
  destinationLatitude: number,
  destinationLongitude: number,
) {
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
  const latitudeDelta = toRadians(destinationLatitude - originLatitude);
  const longitudeDelta = toRadians(destinationLongitude - originLongitude);
  const originRadians = toRadians(originLatitude);
  const destinationRadians = toRadians(destinationLatitude);
  const value = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(originRadians) * Math.cos(destinationRadians) * Math.sin(longitudeDelta / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
}

export function LiveMarketMap({ projectId, sector, sectorLabel, locationLabel, latitude, longitude }: LiveMarketMapProps) {
  const { locale, text } = useCustomerLanguage();
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
      new google.maps.Marker({ map, position: center, title: text("موقع المشروع المؤكد", "Confirmed project location") });
      competitors.forEach((competitor) => {
        const competitorLocation = competitor.location;
        if (!competitorLocation || !confirmedCoordinate(competitorLocation.latitude, -90, 90) || !confirmedCoordinate(competitorLocation.longitude, -180, 180)) return;
        new google.maps.Marker({
          map,
          position: { lat: competitorLocation.latitude, lng: competitorLocation.longitude },
          title: competitorName(competitor, text("منشأة من المصدر", "Source-listed business")),
        });
      });
    });
    return () => {
      disposed = true;
    };
  }, [state, competitors, hasConfirmedLocation, latitude, longitude, text]);

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
    <article className="live-market-map" aria-label={text("خريطة المنافسين للموقع المؤكد", "Competitor map for the confirmed location")}>
      <header className="live-market-map__heading">
        <div>
          <MapPinned size={20} aria-hidden="true" />
          <div>
            <span>{text("المنافسة في النطاق", "Competition nearby")}</span>
            <strong>{text("خريطة ومنافسون من المصدر المعتمد بعد طلبك", "Map and competitors from the approved source after your request")}</strong>
          </div>
        </div>
        <small>{text("لا تحفظ المنصة موقع الجهاز الخام", "The platform does not store the device’s raw location")}</small>
      </header>

      <p className="live-market-map__context">
        {locationLabel || text("الموقع غير مسمى بعد", "Location is not named yet")} · {sectorLabel || text("التصنيف مطلوب", "Category is required")}
      </p>

      <button
        type="button"
        className="live-market-map__refresh"
        disabled={!canRefresh || state === "loading"}
        onClick={refreshMarketContext}
      >
        <RefreshCw size={16} aria-hidden="true" />
        {state === "loading" ? text("جارٍ تحديث معلومات السوق…", "Updating market information…") : text("البحث عن منافسين قرب الموقع", "Find competitors near this location")}
      </button>

      {!canRefresh ? (
        <p className="live-market-map__notice" role="status">
          {text("أكد موقع المشروع وحدد القطاع أولاً. لن يبدأ البحث قبل ذلك.", "Confirm the project location and sector first. Research will not start before then.")}
        </p>
      ) : null}

      {state === "unavailable" ? (
        <p className="live-market-map__notice live-market-map__notice--unavailable" role="alert">
          {text("تعذر الوصول إلى مصدر الخرائط مؤقتًا. يمكنك إعادة المحاولة لاحقًا؛ لن تُعرض بيانات بديلة.", "The map source is temporarily unavailable. You can try again later; no substitute data will be shown.")}
        </p>
      ) : null}

      {state === "ready" ? (
        <div className="live-market-map__results">
          <p className="live-market-map__source">
            {address?.formattedAddress || locationLabel || text("الموقع المؤكد", "Confirmed location")} · {text("المصدر: خدمة الخرائط المعتمدة", "Source: approved mapping service")}
          </p>
          <div ref={mapElement} className="live-market-map__canvas" aria-label={text("خريطة الموقع والمنافسين", "Project and competitor map")} />
          {mapUnavailable ? (
            <p className="live-market-map__notice" role="status">
              {text("تعذر تحميل الخريطة في المتصفح؛ تبقى نتائج المصدر أدناه متاحة ولن تُستبدل ببيانات تجريبية.", "The browser map could not be loaded; the source results below remain available and will not be replaced with demo data.")}
            </p>
          ) : null}
          <section className="live-market-map__list" aria-label={text("المنافسون من المصدر", "Competitors from the source")}>
            <h3>{text("المنشآت المطابقة في نطاق البحث", "Matching businesses in the search area")}</h3>
            {competitors.length ? (
              <ul>
                {competitors.map((competitor) => (
                  <li key={competitor.id}>
                    <div>
                      <strong>{competitorName(competitor, text("منشأة من المصدر", "Source-listed business"))}</strong>
                      <span>
                        {competitor.location && typeof latitude === "number" && typeof longitude === "number"
                          ? `${new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", { maximumFractionDigits: 1 }).format(distanceKilometers(latitude, longitude, competitor.location.latitude, competitor.location.longitude))} ${text("كم تقريبًا", "km approximately")}`
                          : text("المسافة غير متاحة", "Distance unavailable")}
                      </span>
                      {competitor.formattedAddress ? <small>{competitor.formattedAddress}</small> : null}
                    </div>
                    {competitor.googleMapsUri ? (
                      <a href={competitor.googleMapsUri} target="_blank" rel="noreferrer">
                        {text("فتح الموقع على الخريطة", "Open location on map")}
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p>{text("لم يعثر المصدر على منشآت مطابقة في نطاق البحث الحالي.", "The source found no matching businesses in the current search area.")}</p>
            )}
          </section>
        </div>
      ) : null}
    </article>
  );
}
