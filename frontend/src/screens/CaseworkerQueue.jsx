import { useCallback, useEffect, useState } from "react";
import { approveApplication, fetchReviewQueue, requestMoreInfo } from "../api";
import { displayValue, documentLabel, label } from "../applicationFields";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

// Staff screen, English or Chinese (caseworkers at community
// organizations often work in both). Demo-grade access: one shared key
// (CASEWORKER_KEY on the backend, VITE_CASEWORKER_KEY here).
const DEFAULT_KEY = import.meta.env.VITE_CASEWORKER_KEY || "demo-caseworker";

function QueueItem({ application, onApprove, onRequestInfo, language }) {
  const [note, setNote] = useState("");
  const missing = application.documents.filter((d) => application.review_reason.includes(d.key));
  const name = application.fields.find((f) => f.key === "full_name")?.value;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="benefit-card-header">
        <h2 style={{ margin: 0 }}>{name || t(language, "cwApplication", { id: application.id })}</h2>
        <span className="badge possible">{application.covers.join(" + ")}</span>
      </div>

      <h3 style={{ marginTop: 12 }}>{t(language, "cwMissingDocs")}</h3>
      <ul>
        {missing.map((d) => (
          <li key={d.key}>{documentLabel(d, language)}</li>
        ))}
      </ul>

      <details>
        <summary>{t(language, "cwAnswers")}</summary>
        <table className="kv-table">
          <tbody>
            {application.fields.map((f) => (
              <tr key={f.key}>
                <td>{label(f, language)}</td>
                <td>
                  {displayValue(f, language)}
                  {f.source && <span className="review-source"> ({t(language, `source_${f.source}`)})</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      <textarea
        className="text-input"
        rows={2}
        placeholder={t(language, "cwNotePlaceholder")}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        style={{ marginTop: 12 }}
      />
      <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
        <button type="button" className="big-button" onClick={() => onApprove(application.id, note)}>
          {t(language, "cwApprove")}
        </button>
        <button
          type="button"
          className="big-button secondary"
          disabled={!note.trim()}
          onClick={() => onRequestInfo(application.id, note)}
        >
          {t(language, "cwRequestInfo")}
        </button>
      </div>
    </div>
  );
}

export default function CaseworkerQueue() {
  const { language: appLanguage } = useLanguage();
  const [language, setLanguage] = useState(appLanguage === "zh" ? "zh" : "en");
  const [key, setKey] = useState(DEFAULT_KEY);
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    fetchReviewQueue(key)
      .then((items) => {
        setQueue(items);
        setError("");
      })
      .catch((err) => {
        setQueue(null);
        setError(err.message);
      });
  }, [key]);

  useEffect(load, [load]);

  async function act(action) {
    try {
      await action();
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app-shell">
      <div className="segmented" role="group" style={{ maxWidth: 200 }}>
        {[
          ["en", "English"],
          ["zh", "中文"],
        ].map(([code, name]) => (
          <button
            key={code}
            type="button"
            className={language === code ? "active" : ""}
            onClick={() => setLanguage(code)}
          >
            {name}
          </button>
        ))}
      </div>
      <h1>{t(language, "cwTitle")}</h1>
      <p>{t(language, "cwIntro")}</p>

      <div className="section">
        <label htmlFor="cw-key">
          <h3>{t(language, "cwKey")}</h3>
        </label>
        <input id="cw-key" className="text-input" value={key} onChange={(e) => setKey(e.target.value)} />
      </div>

      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
      {queue && queue.length === 0 && <p>{t(language, "cwEmpty")}</p>}
      {queue?.map((application) => (
        <QueueItem
          key={application.id}
          application={application}
          language={language}
          onApprove={(id, note) => act(() => approveApplication(key, id, note))}
          onRequestInfo={(id, note) => act(() => requestMoreInfo(key, id, note))}
        />
      ))}

      <button type="button" className="big-button secondary" onClick={load}>
        {t(language, "cwRefresh")}
      </button>
    </div>
  );
}
