import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";

export default function TracePanel({ trace }) {
  const { language } = useLanguage();
  if (!trace || trace.length === 0) return null;

  return (
    <details className="card">
      <summary>{t(language, "howProcessed")}</summary>
      <div style={{ marginTop: 8 }}>
        {trace.map((step, i) => (
          <div className="trace-step" key={i}>
            <span>{step.name}</span>
            <span className="trace-step-meta">
              <span className={`badge ${step.service.includes("AI") ? "ai" : "no-ai"}`}>
                {step.service}
              </span>
              <span className="trace-step-duration">{step.duration_ms} ms</span>
            </span>
          </div>
        ))}
      </div>
    </details>
  );
}
