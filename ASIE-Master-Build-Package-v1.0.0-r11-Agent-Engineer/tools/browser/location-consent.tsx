import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { CustomerLanguageProvider } from "../../src/customerLanguage";
import { LocationConsentInput, type ConfirmedCoordinates } from "../../src/LocationConsentInput";
import "../../src/styles.css";
import "../../src/asie-reference-theme.css";
import "../../src/asie-complete-surface.css";

function Fixture() {
  const [scope, setScope] = useState(0);
  const [mounted, setMounted] = useState(true);
  const [confirmed, setConfirmed] = useState<ConfirmedCoordinates[]>([]);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  return (
    <main style={{ maxWidth: 700, margin: "auto", padding: 16 }}>
      {mounted ? <LocationConsentInput key={scope} onConfirm={(value) => {
        setConfirmed((values) => [...values, value]);
        setLatitude(String(value.latitude));
        setLongitude(String(value.longitude));
      }} /> : null}
      <div className="location-fields">
        <label className="field"><span>خط العرض اليدوي</span><input type="number" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} /></label>
        <label className="field"><span>خط الطول اليدوي</span><input type="number" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} /></label>
      </div>
      <button type="button" onClick={() => setScope((value) => value + 1)}>تغيير السياق للاختبار</button>
      <output role="note" data-testid="confirmed">{JSON.stringify(confirmed)}</output>
      <button type="button" onClick={() => setMounted((value) => !value)}>تبديل المكون للاختبار</button>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(\n  <StrictMode><CustomerLanguageProvider><Fixture /></CustomerLanguageProvider></StrictMode>\n);
