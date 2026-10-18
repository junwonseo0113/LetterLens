import { useEffect, useRef } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import BigButton from "../components/BigButton";
import CameraIcon from "../components/CameraIcon";
import ErrorBox from "../components/ErrorBox";
import IconBadge from "../components/IconBadge";
import Layout from "../components/Layout";
import { SampleNote } from "../components/SampleBadge";
import TracePanel from "../components/TracePanel";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, extractedFieldLabel, letterTypeLabel, t } from "../strings";
import { fetchBenefits, fetchLetter } from "../api";
import { formatMoney } from "../format";
import { speechLang } from "../speech";
import { useLetterUpload } from "../hooks/useLetterUpload";
import { useLoad } from "../hooks/useLoad";

const MONEY_FIELDS = new Set(["gross_monthly_benefit", "part_b_deduction", "net_payment", "ending_balance"]);

function readAloud(text, lang) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 0.9;
  window.speechSynthesis.speak(utterance);
}

function formatField(key, value, language) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "boolean") return t(language, value ? "yes" : "no");
  if (MONEY_FIELDS.has(key) && typeof value === "number") return `$${formatMoney(value)}`;
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return value
      .map((item) =>
        typeof item === "object" ? `${item.description}: $${formatMoney(item.amount)}` : String(item),
      )
      .join("; ");
  }
  return String(value);
}

export default function LetterResult() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const { letterId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const rescan = useLetterUpload({ replace: true });

  // Just uploaded: the result arrives with the navigation. Reopened from the
  // letter list (or after a refresh): load it by id -- the server only
  // returns it to its owner.
  const passed = location.state?.result;
  const usePassed = passed && (!letterId || String(passed.letter_id) === letterId);
  const loaded = useLoad(
    () => (usePassed || !letterId ? Promise.resolve(null) : fetchLetter(token, letterId, language || "en")),
    [token, letterId, language, usePassed],
  );
  const result = usePassed ? passed : loaded.data;

  const benefits = useLoad(
    () => (result ? fetchBenefits(token, language || "en") : Promise.resolve(null)),
    [token, language, Boolean(result)],
  );
  const likely = (benefits.data?.results || []).filter((b) => b.status === "likely" || b.status === "possible");

  useEffect(() => {
    if (!letterId && !passed) navigate("/home", { replace: true });
  }, [letterId, passed, navigate]);

  if (!result) {
    return (
      <Layout backTo="/home">
        {loaded.loading && <p className="spinner-wrap">{t(language, "loading")}</p>}
        {loaded.error && (
          <ErrorBox
            title={t(language, "errLoadLetter")}
            error={loaded.error}
            onRetry={loaded.error.status === 404 ? undefined : loaded.reload}
          />
        )}
      </Layout>
    );
  }

  const fieldRows = Object.entries(result.extracted_fields || {})
    .map(([key, value]) => [key, formatField(key, value, language)])
    .filter(([, shown]) => shown !== null);

  return (
    <Layout backTo="/home">
      <h1>{t(language, "yourLetter")}</h1>

      <div className="card" style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <IconBadge kind={result.letter_type} size={44} />
        <div>
          <div style={{ fontWeight: 700, fontSize: "var(--font-size-base)" }}>
            {letterTypeLabel(language, result.letter_type)}
          </div>
          <div style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)" }}>
            {usePassed
              ? t(language, "scannedJustNow")
              : result.created_at && new Date(result.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {result.is_sample && <SampleNote textKey="sampleLetterNote" />}

      <div className="section">
        <h3>{t(language, "explanation")}</h3>
        <div className="card">
          <p style={{ margin: 0 }}>{result.explanation}</p>
          <button
            type="button"
            className="big-button dark"
            style={{
              width: "auto",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 18px",
              fontSize: "var(--font-size-sm)",
              marginTop: 12,
            }}
            onClick={() => readAloud(result.explanation, speechLang(language))}
          >
            {"\u{1F50A}"} {t(language, "readAloud")}
          </button>
        </div>
      </div>

      <div className="section">
        <h3>{t(language, "actionItems")}</h3>
        <ul>
          {result.action_items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </div>

      {result.deadline && (
        <p>
          <strong>{t(language, "deadline")}:</strong> {result.deadline}
        </p>
      )}

      {result.reminder && (
        <div className="card">
          <strong>{result.reminder.program}</strong> &mdash; {result.reminder.deadline} (
          {result.reminder.overdue
            ? t(language, "overdue")
            : `${result.reminder.days_until_deadline} ${t(language, "daysLeft")}`}
          )
        </div>
      )}

      {fieldRows.length > 0 && (
        <div className="section">
          <h3>{t(language, "extractedInfoTitle")}</h3>
          <div className="card">
            <table className="kv-table">
              <tbody>
                {fieldRows.map(([key, shown]) => (
                  <tr key={key}>
                    <td>{extractedFieldLabel(language, key)}</td>
                    <td>{shown}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result.bill_check && (
        <BigButton to="/bill-check" state={{ billCheck: result.bill_check }} variant="danger">
          {t(language, "seeBillCheck")}
        </BigButton>
      )}

      {likely.length > 0 && (
        <div className="section">
          <h3>{t(language, "viewBenefits")}</h3>
          <div className="ios-list">
            {likely.map((b) => (
              <div key={b.program} className="reminder-item">
                <IconBadge kind={b.program} size={36} />
                <span style={{ flex: 1, fontWeight: 700 }}>{b.program}</span>
                <span className={`status-text ${b.status}`}>{t(language, STATUS_KEY[b.status])}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <BigButton to="/benefits" variant="secondary">
        {t(language, "viewBenefits")}
      </BigButton>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={rescan.onFileChange}
      />
      {rescan.error && (
        <ErrorBox
          title={t(language, "errUpload")}
          error={rescan.error}
          onRetry={rescan.retry}
          onDismiss={rescan.dismiss}
        />
      )}
      <button
        type="button"
        className="big-button dark"
        style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
        disabled={rescan.uploading}
        onClick={() => fileInputRef.current?.click()}
      >
        {rescan.uploading ? (
          t(language, "uploading")
        ) : (
          <>
            <CameraIcon size={20} /> {t(language, "scanAnother")}
          </>
        )}
      </button>

      {result.trace?.length > 0 && <TracePanel trace={result.trace} />}
    </Layout>
  );
}
