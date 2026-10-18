import { Link } from "react-router-dom";
import BigButton from "../components/BigButton";
import ErrorBox from "../components/ErrorBox";
import Layout from "../components/Layout";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { documentText, numberLabel, t } from "../strings";
import { documentLabel } from "../applicationFields";
import { fetchBenefits, fetchMspChecklist, fetchReminders } from "../api";
import { useLoad } from "../hooks/useLoad";

const MSP_PROGRAMS = new Set(["QMB", "QI", "MSP"]);
const QUALIFIES = new Set(["likely", "possible"]);
const SNAP_APPLY_DOCS = ["snapDocId", "snapDocAddress", "snapDocIncome", "snapDocExpenses", "snapDocMedical"];

// status "have" | "partial" | "missing"; falls back to the done boolean
// (treated as "have"/"missing") for checklists that don't pass a status.
const STATUS_ICON = { have: "✅", partial: "🟡", missing: "⬜" };

function Checklist({ items }) {
  return (
    <ul style={{ listStyle: "none", paddingLeft: 0, margin: 0 }}>
      {items.map(({ key, done, status, label }) => (
        <li key={key} style={{ padding: "4px 0" }}>
          {STATUS_ICON[status] || (done ? "✅" : "⬜")} {label}
        </li>
      ))}
    </ul>
  );
}

// LetterLens can't file SNAP, so say so plainly and give the real next step:
// renew with HRA by the deadline, or apply through ACCESS HRA.
function SnapSection({ snap, renewal }) {
  const { language } = useLanguage();
  if (!snap && !renewal) return null;

  let body;
  if (renewal) {
    const items = (
      renewal.packet?.items ?? renewal.checklist.map((item) => ({ item, satisfied: false, status: "missing" }))
    ).map((p, i) => ({ key: i, done: p.satisfied, status: p.status, label: documentText(language, p.item) }));
    body = (
      <>
        <p>{t(language, "snapRenewalNext", { date: renewal.deadline })}</p>
        <Checklist items={items} />
      </>
    );
  } else if (QUALIFIES.has(snap.status)) {
    body = (
      <>
        <p>{t(language, "snapApplyNext")}</p>
        <Checklist items={SNAP_APPLY_DOCS.map((key) => ({ key, done: false, label: t(language, key) }))} />
      </>
    );
  } else if (snap.status === "missing_info") {
    body = (
      <>
        <p>{t(language, "snapNeedsInfo")}</p>
        <BigButton to="/benefits#questions" variant="secondary">
          {t(language, "missingInfoCta")}
        </BigButton>
      </>
    );
  } else {
    return null; // "not likely right now" -- nothing to apply for
  }

  return (
    <section>
      <h3>{t(language, "snapTitle")}</h3>
      <div className="card">
        <p className="review-source" style={{ marginTop: 0 }}>
          {t(language, "snapUnsupported")}
        </p>
        {body}
      </div>
    </section>
  );
}

export default function ApplicationPack() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const reminders = useLoad(() => fetchReminders(token), [token]);
  const benefits = useLoad(() => fetchBenefits(token, language || "en"), [token, language]);
  const mspChecklist = useLoad(() => fetchMspChecklist(token), [token]);

  const results = benefits.data?.results || [];
  const likelyPrograms = results.filter((b) => QUALIFIES.has(b.status));
  const mspLikely = results.some((b) => MSP_PROGRAMS.has(b.program) && QUALIFIES.has(b.status));
  const snap = results.find((b) => b.program === "SNAP");
  const snapRenewal = (reminders.data || []).find((r) => r.program === "SNAP");
  const otherReminders = (reminders.data || []).filter((r) => r.program !== "SNAP");
  const loading = reminders.loading || benefits.loading || mspChecklist.loading;

  return (
    <Layout title={t(language, "applicationPackTitle")} backTo="/benefits">
      {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}
      {benefits.error && (
        <ErrorBox title={t(language, "errLoadBenefits")} error={benefits.error} onRetry={benefits.reload} />
      )}
      {reminders.error && (
        <ErrorBox title={t(language, "errLoadDeadlines")} error={reminders.error} onRetry={reminders.reload} />
      )}

      {mspLikely && (
        <section>
          <h3>{t(language, "mspChecklistTitle")}</h3>
          {mspChecklist.error && (
            <ErrorBox
              title={t(language, "errLoadChecklist")}
              error={mspChecklist.error}
              onRetry={mspChecklist.reload}
            />
          )}
          {mspChecklist.data && (
            <div className="card">
              <Checklist
                items={mspChecklist.data.items.map((item) => ({
                  key: item.key,
                  done: item.status === "already_have",
                  label: documentLabel(item, language),
                }))}
              />
              <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)", margin: "10px 0" }}>
                {t(language, "msp45DayNote")}
              </p>
              <BigButton to="/apply">{t(language, "applyCta")}</BigButton>
            </div>
          )}
        </section>
      )}

      {!benefits.error && !reminders.error && <SnapSection snap={snap} renewal={snapRenewal} />}

      {otherReminders.length > 0 && (
        <section>
          <h3>{t(language, "checklist")}</h3>
          {otherReminders.map((r) => (
            <div key={r.id} className="card" style={{ marginBottom: 12 }}>
              <div className="benefit-card-header">
                <strong>{r.program}</strong>
                {r.packet && (
                  <span className={`badge ${r.packet.all_satisfied ? "likely" : "possible"}`}>
                    {r.packet.satisfied_count}/{r.packet.total_count} {t(language, "documentsReady")}
                  </span>
                )}
              </div>
              <Checklist
                items={(
                  r.packet?.items ?? r.checklist.map((item) => ({ item, satisfied: false, status: "missing" }))
                ).map((p, i) => ({
                  key: i,
                  done: p.satisfied,
                  status: p.status,
                  label: documentText(language, p.item),
                }))}
              />
            </div>
          ))}
        </section>
      )}

      {likelyPrograms.length > 0 && (
        <section>
          <h3>
            {t(language, "english")} / {t(language, "translated")}
          </h3>
          {likelyPrograms.map((b) => (
            <div key={b.program} className="card" style={{ marginBottom: 12 }}>
              <strong>{b.program}</strong>
              <table className="kv-table">
                <tbody>
                  {Object.entries(b.numbers_used).map(([key, value]) => (
                    <tr key={key}>
                      <td>{numberLabel(language, key)}</td>
                      <td>{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </section>
      )}

      {!loading && !mspLikely && !snap && !snapRenewal && otherReminders.length === 0 && (
        <div className="card">
          <p>{t(language, "snapNeedsInfo")}</p>
          <Link to="/benefits">{t(language, "goToBenefits")}</Link>
        </div>
      )}
    </Layout>
  );
}
