import { useEffect, useState, type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { fetchMe } from "./api";
import { customerErrorText, useCustomerLanguage } from "./customerLanguage";

type GateState = "checking" | "allowed" | "denied" | "failed";

export function EngineeringSurfaceGate({ children }: { children: ReactNode }) {
  const { locale, direction, text } = useCustomerLanguage();
  const [state, setState] = useState<GateState>("checking");
  const [failure, setFailure] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchMe()
      .then((identity) => {
        if (!cancelled) setState(identity.platform_role === "platform_admin" ? "allowed" : "denied");
      })
      .catch((reason) => {
        if (!cancelled) {
          setFailure(reason);
          setState("failed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "allowed") return <>{children}</>;

  return (
    <main id="main-content" className="admin-shell" dir={direction}>
      <section className="admin-login engineering-surface-gate" aria-live="polite">
        <ShieldAlert size={28} aria-hidden="true" />
        <h1>
          {state === "checking"
            ? text("جارٍ التحقق من الصلاحية", "Checking access")
            : text("هذه الصفحة مخصصة لإدارة المنصة", "This page is restricted to platform administration")}
        </h1>
        <p>
          {state === "checking"
            ? text("لحظات من فضلك.", "One moment, please.")
            : state === "failed"
              ? customerErrorText(failure, locale)
              : text(
                  "لا تظهر أدوات الفحص والهندسة في مساحة العميل. يمكنك العودة إلى لوحة المشروع.",
                  "Engineering and diagnostic tools are not shown in the customer workspace. You can return to the project dashboard."
                )}
        </p>
        {state !== "checking" ? (
          <a className="primary-button" href="#dashboard">
            {text("العودة إلى لوحة المشروع", "Return to project dashboard")}
          </a>
        ) : null}
      </section>
    </main>
  );
}
