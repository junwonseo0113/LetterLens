import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";
import { fetchLetters, fetchReminders, setOnQmb, uploadLetter } from "../api";

const USER_ID = "demo";

const LETTER_TYPE_LABEL = {
  ssa_benefit_letter: "SSA",
  bank_statement: "Bank",
  hra_renewal_notice: "HRA",
  medical_bill: "Medical bill",
  medicare_notice: "Medicare",
  other: "Letter",
};

export default function Home() {
  const { language } = useLanguage();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [letters, setLetters] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [onQmb, setOnQmbState] = useState(false);
  const [qmbSaving, setQmbSaving] = useState(false);

  useEffect(() => {
    fetchLetters(USER_ID).then(setLetters).catch(() => {});
    fetchReminders(USER_ID).then(setReminders).catch(() => {});
  }, []);

  async function handleQmbToggle(event) {
    const next = event.target.checked;
    setOnQmbState(next);
    setQmbSaving(true);
    try {
      await setOnQmb(USER_ID, next);
    } catch {
      setOnQmbState(!next); // revert on failure
    } finally {
      setQmbSaving(false);
    }
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    setError("");
    try {
      const result = await uploadLetter({ file, language: language || "en", userId: USER_ID });
      navigate("/letter-result", { state: { result } });
    } catch (err) {
      setError(err.message || t(language, "error"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="app-shell">
      <h1>{t(language, "appName")}</h1>
      <div className="airmail-rule" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <BigButton onClick={() => fileInputRef.current?.click()}>
        {uploading ? t(language, "uploading") : `\u{1F4F7} ${t(language, "takePhoto")}`}
      </BigButton>
      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}

      <BigButton to="/benefits" variant="secondary">
        {t(language, "viewBenefits")}
      </BigButton>

      <section>
        <h2>{t(language, "upcomingDeadlines")}</h2>
        {reminders.length === 0 && <p>{t(language, "noDeadlines")}</p>}
        {reminders.map((r) => (
          <div key={r.id} className="reminder-item">
            <span>
              {r.program}
              {r.packet && (
                <>
                  {" "}
                  &middot; {r.packet.satisfied_count}/{r.packet.total_count} {t(language, "documentsReady")}
                </>
              )}
            </span>
            <span>
              {r.overdue ? t(language, "overdue") : `${r.days_until_deadline} ${t(language, "daysLeft")}`}
            </span>
          </div>
        ))}
      </section>

      <section className="card">
        <label style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 20 }}>
          <input
            type="checkbox"
            checked={onQmb}
            onChange={handleQmbToggle}
            disabled={qmbSaving}
            style={{ width: 28, height: 28 }}
          />
          {t(language, "qmbToggleLabel")}
        </label>
        <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)", margin: "8px 0 0" }}>
          {t(language, "qmbToggleHelp")}
        </p>
      </section>

      <section>
        <h2>{t(language, "pastLetters")}</h2>
        {letters.length === 0 && <p>{t(language, "noLettersYet")}</p>}
        {letters.map((l) => (
          <div key={l.id} className="letter-list-item">
            <span>{LETTER_TYPE_LABEL[l.letter_type] || l.letter_type}</span>
            <span style={{ color: "var(--color-muted)" }}>
              {new Date(l.created_at).toLocaleDateString()}
            </span>
          </div>
        ))}
      </section>
    </div>
  );
}
