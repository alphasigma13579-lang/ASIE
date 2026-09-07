import { useEffect, useId, useRef, useState } from "react";
import { useCustomerLanguage } from "./customerLanguage";
import "./location-consent.css";

export type ConfirmedCoordinates = Readonly<{ latitude: number; longitude: number }>;
type Candidate = ConfirmedCoordinates & { accuracy: number };
type LocationError = "secure_connection_required" | "unsupported" | "permission_denied" | "timed_out" | "unavailable";
type State =
  | { kind: "idle" | "pending" | "cancelled" | "confirmed" }
  | { kind: "candidate"; candidate: Candidate }
  | { kind: "error"; reason: LocationError };

export function LocationConsentInput({ onConfirm }: { onConfirm: (value: ConfirmedCoordinates) => void }) {
  const { text } = useCustomerLanguage();
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
        setState({ kind: "error", reason: "secure_connection_required" });
        return;
      }
      if (!navigator.geolocation) {
        setState({ kind: "error", reason: "unsupported" });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (request !== generation.current) return;
          generation.current += 1;
          const { latitude, longitude, accuracy } = position.coords;
          if (![latitude, longitude, accuracy].every(Number.isFinite)
            || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180 || accuracy < 0) {
            setState({ kind: "error", reason: "unavailable" });
            return;
          }
          setState({ kind: "candidate", candidate: { latitude, longitude, accuracy } });
        },
        (error) => {
          if (request !== generation.current) return;
          generation.current += 1;
          const reason: LocationError = error.code === 1
            ? "permission_denied"
            : error.code === 3
              ? "timed_out"
              : "unavailable";
          setState({ kind: "error", reason });
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
      );
    } catch {
      if (request !== generation.current) return;
      generation.current += 1;
      setState({ kind: "error", reason: "unavailable" });
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

  const errorText = state.kind !== "error" ? "" : {
    secure_connection_required: text("يتطلب تحديد الموقع اتصالًا آمنًا. يمكنك إدخال الموقع يدويًا.", "Location access requires a secure connection. You can enter the location manually."),
    unsupported: text("هذا المتصفح لا يدعم تحديد الموقع. يمكنك إدخال الموقع يدويًا.", "This browser does not support location access. You can enter the location manually."),
    permission_denied: text("لم تسمح بالوصول إلى موقع الجهاز. يمكنك إدخال الموقع يدويًا.", "Location permission was not granted. You can enter the location manually."),
    timed_out: text("انتهت مهلة تحديد الموقع. يمكنك إعادة المحاولة أو إدخال الموقع يدويًا.", "Location detection timed out. Try again or enter the location manually."),
    unavailable: text("تعذر تحديد موقع الجهاز. يمكنك إعادة المحاولة أو إدخال الموقع يدويًا.", "The device location could not be determined. Try again or enter the location manually."),
  }[state.reason];

  const status = state.kind === "pending"
    ? text("بانتظار إذنك ونتيجة تحديد الموقع. يمكنك إلغاء الطلب أو استخدام الإدخال اليدوي.", "Waiting for your permission and location result. You can cancel or use manual entry.")
    : state.kind === "candidate"
      ? text("تم تحديد موقع مؤقت. راجع الإحداثيات والدقة ثم أكد استخدامها لمشروعك.", "A temporary location was found. Review its coordinates and accuracy, then confirm it for your project.")
      : state.kind === "confirmed"
        ? text("تم نقل الإحداثيات إلى حقول الموقع؛ يمكنك تعديلها يدويًا.", "The coordinates were added to the location fields; you can edit them manually.")
        : state.kind === "cancelled"
          ? text("أُلغي استخدام موقع الجهاز؛ لن تُعتمد أي نتيجة متأخرة.", "Device location use was cancelled; no late result will be accepted.")
          : errorText;

  return (
    <section className="location-consent" aria-label={text("تحديد موقع المشروع بموافقتك", "Set project location with your permission")}>
      <p id={descriptionId}>
        {text(
          "تحديد موقع الجهاز اختياري. لن تُنقل إحداثياته إلى المشروع قبل تأكيدك. تأكد أن الموقع يمثل مشروعك، وحدد المنطقة والمدينة من الحقول أدناه.",
          "Device location is optional. Its coordinates are not added to the project until you confirm them. Make sure the location represents your project, then select the region and city below.",
        )}
      </p>
      <div className="button-row">
        <button type="button" ref={requestButton} className="secondary-action"
          aria-describedby={descriptionId} onClick={requestPosition}>
          {state.kind === "pending" || state.kind === "candidate" ? text("إعادة طلب موقعي", "Request my location again") : text("تحديد موقعي بإذني", "Use my location with permission")}
        </button>
        {state.kind === "pending" || state.kind === "candidate" ? (
          <button type="button" onClick={cancel}>{text("إلغاء استخدام موقع الجهاز", "Cancel device location")}</button>
        ) : null}
      </div>
      <p role="status" aria-live="polite" aria-atomic="true">{status}</p>
      {state.kind === "candidate" ? (
        <div>
          <dl className="location-consent__coordinates">
            <div><dt>{text("خط العرض المقترح", "Suggested latitude")}</dt><dd><bdi dir="ltr">{state.candidate.latitude.toFixed(6)}</bdi></dd></div>
            <div><dt>{text("خط الطول المقترح", "Suggested longitude")}</dt><dd><bdi dir="ltr">{state.candidate.longitude.toFixed(6)}</bdi></dd></div>
            <div><dt>{text("الدقة التقريبية", "Approximate accuracy")}</dt><dd>{Math.ceil(state.candidate.accuracy)} {text("متر", "metres")}</dd></div>
          </dl>
          <button type="button" className="secondary-action" onClick={confirm}>{text("تأكيد هذا الموقع للمشروع", "Confirm this project location")}</button>
        </div>
      ) : null}
    </section>
  );
}
