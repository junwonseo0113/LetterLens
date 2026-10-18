import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

export default function TracePanel({ trace }) {
  const { language } = useLanguage();
  if (!trace || trace.length === 0) return null;

  const anyOffline = trace.some((step) => step.offline);

  return (
    <>
      {anyOffline && (
        <div className="offline-badge no-print">
          {"\u{1F4F5}"} {t(language, "offlineModeBadge")}
        </div>
      )}
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
    </>
  );
}
