import { useCallback, useEffect, useState } from "react";
import { approveApplication, fetchReviewQueue, requestMoreInfo } from "../api";
import { displayValue } from "../applicationFields";

// Staff screen, English only. Demo-grade access: one shared key
// (CASEWORKER_KEY on the backend, VITE_CASEWORKER_KEY here).
const DEFAULT_KEY = import.meta.env.VITE_CASEWORKER_KEY || "demo-caseworker";

function QueueItem({ application, onApprove, onRequestInfo }) {
  const [note, setNote] = useState("");
  const missing = application.documents.filter((d) => application.review_reason.includes(d.key));
  const name = application.fields.find((f) => f.key === "full_name")?.value;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="benefit-card-header">
        <h2 style={{ margin: 0 }}>{name || `Application #${application.id}`}</h2>
        <span className="badge possible">{application.covers.join(" + ")}</span>
      </div>

      <h3 style={{ marginTop: 12 }}>Missing documents</h3>
      <ul>
        {missing.map((d) => (
          <li key={d.key}>{d.label_en}</li>
        ))}
      </ul>

      <details>
        <summary>Answers</summary>
        <table className="kv-table">
          <tbody>
            {application.fields.map((f) => (
              <tr key={f.key}>
                <td>{f.label_en}</td>
                <td>
                  {displayValue(f, "en")}
                  {f.source && <span className="review-source"> ({f.source.replaceAll("_", " ")})</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      <textarea
        className="text-input"
        rows={2}
        placeholder="Note to the applicant (required to request info)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        style={{ marginTop: 12 }}
      />
      <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
        <button type="button" className="big-button" onClick={() => onApprove(application.id, note)}>
          Approve &amp; send
        </button>
        <button
          type="button"
          className="big-button secondary"
          disabled={!note.trim()}
          onClick={() => onRequestInfo(application.id, note)}
        >
          Request info
        </button>
      </div>
    </div>
  );
}

export default function CaseworkerQueue() {
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
      <h1>Caseworker review</h1>
      <p>Applications the app couldn't send on its own because documents are missing.</p>

      <div className="section">
        <label htmlFor="cw-key">
          <h3>Caseworker key</h3>
        </label>
        <input id="cw-key" className="text-input" value={key} onChange={(e) => setKey(e.target.value)} />
      </div>

      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
      {queue && queue.length === 0 && <p>Nothing waiting for review.</p>}
      {queue?.map((application) => (
        <QueueItem
          key={application.id}
          application={application}
          onApprove={(id, note) => act(() => approveApplication(key, id, note))}
          onRequestInfo={(id, note) => act(() => requestMoreInfo(key, id, note))}
        />
      ))}

      <button type="button" className="big-button secondary" onClick={load}>
        Refresh
      </button>
    </div>
  );
}
