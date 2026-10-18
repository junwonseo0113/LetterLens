import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import IconBadge from "../components/IconBadge";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { fetchLetters, fetchOnQmb, fetchReminders, setOnQmb, uploadLetter } from "../api";

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
  const { token, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const pastLettersRef = useRef(null);
  const qmbUserTouchedRef = useRef(false);
  const [letters, setLetters] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [onQmb, setOnQmbState] = useState(false);
  const [qmbSaving, setQmbSaving] = useState(false);

  useEffect(() => {
    fetchLetters(token).then(setLetters).catch(() => {});
    fetchReminders(token).then(setReminders).catch(() => {});
    fetchOnQmb(token)
      .then((data) => {
        // Ignore this if the user already toggled the switch themselves
        // while this request was in flight -- their action is newer truth
        // than whatever the server had when the request was sent.
        if (!qmbUserTouchedRef.current) setOnQmbState(data.on_qmb);
      })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    if (location.state?.scrollTo === "past-letters") {
      pastLettersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [location.state]);

  async function handleQmbToggle(event) {
    const next = event.target.checked;
    qmbUserTouchedRef.current = true;
    setOnQmbState(next);
    setQmbSaving(true);
    try {
      await setOnQmb(token, next);
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
      const result = await uploadLetter({ file, language: language || "en", token });
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

      <div className="section">
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

        <BigButton to="/apply/status" variant="secondary">
          {t(language, "viewApplication")}
        </BigButton>
      </div>

      <div className="section">
        <h3>{t(language, "upcomingDeadlines")}</h3>
        {reminders.length === 0 ? (
          <p>{t(language, "noDeadlines")}</p>
        ) : (
          <div className="ios-list">
            {reminders.map((r) => (
              <div key={r.id} className="reminder-item">
                <IconBadge kind={r.program} size={36} />
                <span style={{ flex: 1 }}>
                  {r.program}
                  {r.packet && (
                    <>
                      {" "}
                      &middot; {r.packet.satisfied_count}/{r.packet.total_count}{" "}
                      {t(language, "documentsReady")}
                    </>
                  )}
                </span>
                <span>
                  {r.overdue ? t(language, "overdue") : `${r.days_until_deadline} ${t(language, "daysLeft")}`}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section">
        <div className="ios-switch-row">
          <span className="ios-switch-label">{t(language, "qmbToggleLabel")}</span>
          <label className="ios-switch">
            <input type="checkbox" checked={onQmb} onChange={handleQmbToggle} disabled={qmbSaving} />
            <span className="ios-switch-track" />
            <span className="ios-switch-thumb" />
          </label>
        </div>
        <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)", margin: "6px 0 0 4px" }}>
          {t(language, "qmbToggleHelp")}
        </p>
      </div>

      <div className="section" ref={pastLettersRef} id="past-letters">
        <h3>{t(language, "pastLetters")}</h3>
        {letters.length === 0 ? (
          <p>{t(language, "noLettersYet")}</p>
        ) : (
          <div className="ios-list">
            {letters.map((l) => (
              <div key={l.id} className="letter-list-item">
                <IconBadge kind={l.letter_type} size={36} />
                <span style={{ flex: 1 }}>{LETTER_TYPE_LABEL[l.letter_type] || l.letter_type}</span>
                <span style={{ color: "var(--color-muted)" }}>
                  {new Date(l.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <button type="button" className="link-button" onClick={signOut}>
        {t(language, "signOut")}
      </button>
    </div>
  );
}
