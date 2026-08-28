import { useEffect, useId, useRef, useState } from "react";
import "./location-consent.css";

export type ConfirmedCoordinates = Readonly<{ latitude: number; longitude: number }>;
type Candidate = ConfirmedCoordinates & { accuracy: number };
type State =
  | { kind: "idle" | "pending" | "cancelled" | "confirmed" }
  | { kind: "candidate"; candidate: Candidate }
  | { kind: "error"; message: string };

const unavailable = "تعذر تحديد موقع الجهاز. يمكنك إعادة المحاولة أو إدخال الإحداثيات يدويًا.";

export function LocationConsentInput({ onConfirm }: { onConfirm: (value: ConfirmedCoordinates) => void }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const generation = useRef(0);
  const requestButton = useRef<HTMLButtonElement>(null);
  const descriptionId = useId();

  useEffect(() => () => { generation.current += 1; }, []);

  function cancel() {
    generation.current += 1;
    setState({ kind: "cancelled" });
    requestButton.current?.focus();
  }

  function requestPosition() {
    const request = ++generation.current;
    setState({ kind: "pending" });
    try {
      if (!window.isSecureContext) {
        setState({ kind: "error", message: "يتطلب تحديد موقع الجهاز اتصالًا آمنًا HTTPS. يمكنك إدخال الإحداثيات يدويًا." });
        return;
      }
      if (!navigator.geolocation) {
        setState({ kind: "error", message: "هذا المتصفح لا يدعم تحديد الموقع. يمكنك إدخال الإحداثيات يدويًا." });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (request !== generation.current) return;
          generation.current += 1;
          const { latitude, longitude, accuracy } = position.coords;
          if (![latitude, longitude, accuracy].every(Number.isFinite)
            || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180 || accuracy < 0) {
            setState({ kind: "error", message: unavailable });
            return;
          }
          setState({ kind: "candidate", candidate: { latitude, longitude, accuracy } });
        },
        (error) => {
          if (request !== generation.current) return;
          generation.current += 1;
          const message = error.code === 1
            ? "لم تسمح بالوصول إلى موقع الجهاز. يظل الإدخال اليدوي متاحًا دون أي قيود."
            : error.code === 3
              ? "انتهت مهلة تحديد الموقع. يمكنك إعادة المحاولة أو إدخال الإحداثيات يدويًا."
              : unavailable;
          setState({ kind: "error", message });
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
      );
    } catch {
      if (request !== generation.current) return;
      generation.current += 1;
      setState({ kind: "error", message: unavailable });
    }
  }

  function confirm() {
    if (state.kind !== "candidate") return;
    generation.current += 1;
    const { latitude, longitude } = state.candidate;
    setState({ kind: "confirmed" });
    onConfirm({ latitude, longitude });
    requestButton.current?.focus();
  }

  const status = state.kind === "pending"
    ? "بانتظار إذنك ونتيجة تحديد الموقع. يمكنك إلغاء الطلب أو استخدام الإدخال اليدوي."
    : state.kind === "candidate"
      ? "تم تحديد موقع مؤقت. راجع الإحداثيات والدقة ثم أكد استخدامها لمشروعك."
      : state.kind === "confirmed"
        ? "تم نقل الإحداثيات إلى حقول الموقع؛ يمكنك تعديلها يدويًا."
        : state.kind === "cancelled"
          ? "أُلغي استخدام موقع الجهاز؛ لن تُعتمد أي نتيجة متأخرة."
          : state.kind === "error" ? state.message : "";

  return (
    <section className="location-consent" aria-label="تحديد موقع المشروع بموافقتك">
      <p id={descriptionId}>
        تحديد موقع الجهاز اختياري. لن تُنقل إحداثياته إلى نموذج المشروع قبل تأكيدك.
        تأكد أن الموقع يمثل مشروعك، وحدد المنطقة والمدينة من الحقول أدناه.
      </p>
      <div className="button-row">
        <button type="button" ref={requestButton} className="secondary-action"
          aria-describedby={descriptionId} onClick={requestPosition}>
          {state.kind === "pending" || state.kind === "candidate" ? "إعادة طلب موقعي" : "تحديد موقعي بإذني"}
        </button>
        {state.kind === "pending" || state.kind === "candidate" ? (
          <button type="button" onClick={cancel}>إلغاء استخدام موقع الجهاز</button>
        ) : null}
      </div>
      <p role="status" aria-live="polite" aria-atomic="true">{status}</p>
      {state.kind === "candidate" ? (
        <div>
          <dl className="location-consent__coordinates">
            <div><dt>خط العرض المقترح</dt><dd><bdi dir="ltr">{state.candidate.latitude.toFixed(6)}</bdi></dd></div>
            <div><dt>خط الطول المقترح</dt><dd><bdi dir="ltr">{state.candidate.longitude.toFixed(6)}</bdi></dd></div>
            <div><dt>الدقة التقريبية</dt><dd>{Math.ceil(state.candidate.accuracy)} متر</dd></div>
          </dl>
          <button type="button" className="secondary-action" onClick={confirm}>تأكيد الإحداثيات لموقعي</button>
        </div>
      ) : null}
    </section>
  );
}
