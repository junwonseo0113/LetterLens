import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import IconBadge from "../components/IconBadge";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, letterTypeLabel, t } from "../strings";
import { fetchBenefits, fetchLetters, fetchOnQmb, fetchReminders, setOnQmb, uploadLetter } from "../api";
import { benefitTone } from "../benefitTone";

const CATEGORY_TYPES = [
  "ssa_benefit_letter",
  "hra_renewal_notice",
  "medicare_notice",
  "medical_bill",
  "bank_statement",
  "other",
];

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
  const [benefits, setBenefits] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [onQmb, setOnQmbState] = useState(false);
  const [qmbSaving, setQmbSaving] = useState(false);

  useEffect(() => {
    fetchLetters(token).then(setLetters).catch(() => {});
    fetchReminders(token).then(setReminders).catch(() => {});
    fetchBenefits(token, language || "en")
      .then((data) => setBenefits(data.results || []))
      .catch(() => {});
    fetchOnQmb(token)
      .then((data) => {
        // Ignore this if the user already toggled the switch themselves
        // while this request was in flight -- their action is newer truth
        // than whatever the server had when the request was sent.
        if (!qmbUserTouchedRef.current) setOnQmbState(data.on_qmb);
      })
      .catch(() => {});
  }, [token, language]);

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

  // With zero letters uploaded, the rules engine still runs against an
  // empty profile -- and a $0-income household trivially clears every
  // income ceiling, so it would otherwise show as "likely qualifies" for
  // SNAP before any real data exists. Only show results once there's at
  // least one letter backing them.
  const relevantBenefits =
    letters.length === 0 ? [] : benefits.filter((b) => b.status === "likely" || b.status === "possible");

  return (
    <div className="app-shell">
      <AppHeader />

      <div className="section">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <button type="button" className="scan-bar" onClick={() => fileInputRef.current?.click()}>
          <span className="scan-bar-label">{uploading ? t(language, "uploading") : t(language, "scanPrompt")}</span>
          <span className="scan-bar-icon" aria-hidden="true">{"\u{1F4F7}"}</span>
        </button>
        {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
      </div>

      <div className="section">
        <h3>{t(language, "frequentLetters")}</h3>
        <div className="category-grid">
          {CATEGORY_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              className="category-card"
              onClick={() => fileInputRef.current?.click()}
            >
              <IconBadge kind={type} size={32} />
              {letterTypeLabel(language, type)}
            </button>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-head-row">
          <h3>{t(language, "viewBenefits")}</h3>
          <Link className="see-all-link" to="/benefits">
            {t(language, "seeAll")} {"›"}
          </Link>
        </div>
        {relevantBenefits.length > 0 ? (
          <div className="benefit-tile-row">
            {relevantBenefits.map((b) => (
              <Link key={b.program} to="/benefits" className={`benefit-tile tone-${benefitTone(b.program)}`}>
                <div>
                  <div className="benefit-tile-title">{b.program}</div>
                  <div className="benefit-tile-sub">{t(language, STATUS_KEY[b.status])}</div>
                </div>
                <IconBadge kind={b.program} size={28} />
              </Link>
            ))}
          </div>
        ) : (
          <div className="ios-list">
            <Link to="/benefits" className="nav-row">
              {t(language, "viewBenefits")}
              <span className="nav-row-chevron">{"›"}</span>
            </Link>
          </div>
        )}
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

      <div className="section">
        <div className="ios-list">
          <Link to="/apply/status" className="nav-row">
            {t(language, "viewApplication")}
            <span className="nav-row-chevron">{"›"}</span>
          </Link>
        </div>
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
                <span style={{ flex: 1 }}>{letterTypeLabel(language, l.letter_type)}</span>
                <span style={{ color: "var(--color-muted)" }}>
                  {new Date(l.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <button type="button" className="sign-out-row" onClick={signOut}>
        {t(language, "signOut")}
      </button>
    </div>
  );
}
