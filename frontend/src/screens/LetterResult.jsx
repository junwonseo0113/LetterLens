import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import IconBadge from "../components/IconBadge";
import Layout from "../components/Layout";
import TracePanel from "../components/TracePanel";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, letterTypeLabel, t } from "../strings";
import { fetchBenefits, uploadLetter } from "../api";
import { speechLang } from "../speech";

function readAloud(text, lang) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 0.9;
  window.speechSynthesis.speak(utterance);
}

export default function LetterResult() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const result = location.state?.result;
  const [benefits, setBenefits] = useState([]);
  const [rescanning, setRescanning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!result) navigate("/home", { replace: true });
  }, [result, navigate]);

  useEffect(() => {
    if (!result) return;
    fetchBenefits(token, language || "en")
      .then((data) => setBenefits((data.results || []).filter((b) => b.status === "likely" || b.status === "possible")))
      .catch(() => {});
  }, [result, token, language]);

  if (!result) return null;

  async function handleRescan(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setRescanning(true);
    setError("");
    try {
      const next = await uploadLetter({ file, language: language || "en", token });
      navigate("/letter-result", { state: { result: next }, replace: true });
    } catch (err) {
      setError(err.message || t(language, "error"));
    } finally {
      setRescanning(false);
    }
  }

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
            {t(language, "scannedJustNow")}
          </div>
        </div>
      </div>

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
          {result.reminder.days_until_deadline} {t(language, "daysLeft")})
        </div>
      )}

      {result.bill_check && (
        <BigButton to="/bill-check" state={{ billCheck: result.bill_check }} variant="danger">
          {t(language, "seeBillCheck")}
        </BigButton>
      )}

      {benefits.length > 0 && (
        <div className="section">
          <h3>{t(language, "viewBenefits")}</h3>
          <div className="ios-list">
            {benefits.map((b) => (
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
        onChange={handleRescan}
      />
      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
      <button type="button" className="big-button dark" onClick={() => fileInputRef.current?.click()}>
        {rescanning ? t(language, "uploading") : `\u{1F4F7} ${t(language, "scanAnother")}`}
      </button>

      <TracePanel trace={result.trace} />
    </Layout>
  );
}
