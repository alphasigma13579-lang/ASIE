import { useMemo, useState } from "react";

export type InterviewQuestion = {
  question_id: string;
  field: string;
  label_ar: string;
  kind: string;
  required: boolean;
  choices?: string[];
};

export type ProductInterviewSession = {
  interview_id: string;
  status: "in_progress" | "ready_for_review" | "approved";
  questions: InterviewQuestion[];
  current_question_id: string | null;
  answers: Record<string, { status: string; value: unknown }>;
  ai_owns_numbers: false;
};

type Props = {
  session: ProductInterviewSession;
  onAnswer: (questionId: string, value: unknown) => Promise<void> | void;
  onSkip: (questionId: string) => Promise<void> | void;
  onReview: () => Promise<void> | void;
};

const CHOICE_LABELS: Record<string, string> = {
  food_service: "الأغذية والمشروبات",
  retail: "التجزئة",
  services: "الخدمات",
  manufacturing: "التصنيع",
  general: "قطاع عام",
  neighborhood: "الحي",
  city: "المدينة",
  region: "المنطقة",
  saudi_arabia: "المملكة",
  gcc: "الخليج",
  manual: "إدخال يدوي",
  csv: "ملف CSV",
  xlsx: "ملف Excel",
  pdf: "ملف PDF",
  no_data_sanad: "لا أملك بيانات — يساعدني سند",
};

export function ProductAIInterview({ session, onAnswer, onSkip, onReview }: Props) {
  const question = useMemo(
    () => session.questions.find((row) => row.question_id === session.current_question_id) ?? null,
    [session.current_question_id, session.questions],
  );
  const [value, setValue] = useState<string>("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!question || (question.required && !value.trim())) return;
    setBusy(true);
    try {
      const normalized = question.kind === "money_or_unknown" || question.kind === "number_or_unknown"
        ? Number(value)
        : value;
      await onAnswer(question.question_id, normalized);
      setValue("");
    } finally {
      setBusy(false);
    }
  }

  if (session.status === "ready_for_review" || !question) {
    return (
      <section className="asie-card" dir="rtl" aria-labelledby="product-interview-review-title">
        <p className="eyebrow">مرشد تأسيس المشروع</p>
        <h2 id="product-interview-review-title">اكتملت الأسئلة الجوهرية</h2>
        <p>
          راجع الاحتياجات والبنود المقترحة قبل إرسالها إلى مخطط المدخلات الديناميكي. لا يعتمد سند أي رقم مالي نيابةً عنك.
        </p>
        <button type="button" className="primary-button" onClick={onReview}>
          مراجعة الاحتياجات المقترحة
        </button>
      </section>
    );
  }

  return (
    <section className="asie-card product-ai-interview" dir="rtl" aria-labelledby="product-interview-title">
      <header>
        <p className="eyebrow">مقابلة سند للمشروع</p>
        <h2 id="product-interview-title">{question.label_ar}</h2>
        <p>
          {question.required ? "إجابة مطلوبة لإكمال مسار المشروع." : "يمكن تجاوز هذا السؤال."}
        </p>
      </header>

      {question.choices?.length ? (
        <div className="choice-grid" role="group" aria-label={question.label_ar}>
          {question.choices.map((choice) => (
            <button
              type="button"
              key={choice}
              className={value === choice ? "choice-card is-selected" : "choice-card"}
              onClick={() => setValue(choice)}
            >
              {CHOICE_LABELS[choice] ?? choice}
            </button>
          ))}
        </div>
      ) : (
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          inputMode={question.kind.includes("number") || question.kind.includes("money") ? "decimal" : "text"}
          aria-label={question.label_ar}
        />
      )}

      <footer className="action-row">
        {!question.required && (
          <button type="button" className="secondary-button" disabled={busy} onClick={() => onSkip(question.question_id)}>
            تجاوز
          </button>
        )}
        <button type="button" className="primary-button" disabled={busy || !value.trim()} onClick={submit}>
          اعتماد الإجابة والمتابعة
        </button>
      </footer>

      <small>الذكاء الاصطناعي يقترح ويشرح فقط؛ الأرقام المالية لا تصبح معتمدة إلا بعد مراجعتك ومرورها عبر Approved Input Manifest.</small>
    </section>
  );
}
