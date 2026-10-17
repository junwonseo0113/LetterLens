import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";
import { fetchLetters, fetchReminders, uploadLetter } from "../api";

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

  useEffect(() => {
    fetchLetters(USER_ID).then(setLetters).catch(() => {});
    fetchReminders(USER_ID).then(setReminders).catch(() => {});
  }, []);

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
