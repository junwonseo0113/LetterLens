import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BigButton from "../components/BigButton";
import IconBadge from "../components/IconBadge";
import Layout from "../components/Layout";
import TracePanel from "../components/TracePanel";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, confidenceLabel, numberLabel, t } from "../strings";
import { formatMoney } from "../format";
import { fetchBenefits } from "../api";
import { speechLang } from "../speech";

const MSP_PROGRAMS = new Set(["QMB", "QI", "MSP"]);
// Same tints as the benefit tiles on Home, so a program reads as the same
// thing on both screens.
const TILE_TONE = { QMB: "pink", MSP: "pink", QI: "pink", "Extra Help": "yellow", SNAP: "green" };

function isEligible(b) {
  return b.status === "likely" || b.status === "possible" || b.status === "already_enrolled";
}

function readAloud(text, lang) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 0.9;
  window.speechSynthesis.speak(utterance);
}

// "Why / numbers used" -- collapsed by default so the card leads with the
// plain-language answer, not the rule text.
function WhyDetails({ benefit, language }) {
  return (
    <details className="benefit-why">
      <summary>
        {t(language, "why")} / {t(language, "numbersUsed")}
        <span className="benefit-why-chevron" aria-hidden="true">
          {"›"}
        </span>
      </summary>
      <p>{benefit.rule_applied}</p>
      <table className="kv-table">
        <tbody>
          {Object.entries(benefit.numbers_used).map(([key, value]) => (
            <tr key={key}>
              <td>{numberLabel(language, key)}</td>
              <td>{String(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="benefit-why-confidence">
        {t(language, "confidence")}: {confidenceLabel(language, benefit.confidence)}
      </p>
    </details>
  );
}

function Notes({ benefit }) {
  return (
    <>
      {benefit.warnings?.map((w, i) => (
        <p key={`w${i}`} className="benefit-note warn">
          {w}
        </p>
      ))}
      {benefit.myth_busting_lines?.map((line, i) => (
        <p key={`m${i}`} className="benefit-note tip">
          {line}
        </p>
      ))}
    </>
  );
}

function EligibleCard({ benefit, language }) {
  return (
    <article className={`benefit-card-v2 tone-${TILE_TONE[benefit.program] || "blue"}`}>
      <header className="benefit-card-v2-head">
        <IconBadge kind={benefit.program} size={48} />
        <div>
          <h2>{benefit.program}</h2>
          <span className={`badge ${benefit.status}`}>{t(language, STATUS_KEY[benefit.status])}</span>
        </div>
      </header>

      {benefit.annual_value > 0 && (
        <p className="benefit-value">
          <strong>${formatMoney(benefit.annual_value)}</strong>
          <span>
            {t(language, "annualValue")} · ${formatMoney(benefit.monthly_value)} {t(language, "monthlyValue")}
          </span>
        </p>
      )}

      <div className="benefit-card-v2-body">
        <p className="benefit-explanation">{benefit.explanation}</p>
        <button
          type="button"
          className="listen-pill"
          onClick={() => readAloud(benefit.explanation, speechLang(language))}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 9.5v5h4l5 4v-13l-5 4H4z" />
            <path d="M16.5 9a4 4 0 010 6" />
          </svg>
          {t(language, "readAloud")}
        </button>
        <Notes benefit={benefit} />
        <WhyDetails benefit={benefit} language={language} />
      </div>
    </article>
  );
}

// Programs the user doesn't qualify for right now: one compact row each,
// tap to open the explanation. Keeps the screen from being a wall of
// near-identical "you don't qualify" paragraphs.
function NotNowRow({ benefit, language }) {
  return (
    <details className="benefit-row">
      <summary>
        <IconBadge kind={benefit.program} size={36} />
        <span className="benefit-row-name">{benefit.program}</span>
        <span className={`status-text ${benefit.status}`}>{t(language, STATUS_KEY[benefit.status])}</span>
        <span className="benefit-row-chevron" aria-hidden="true">
          {"›"}
        </span>
      </summary>
      <div className="benefit-row-body">
        <p className="benefit-explanation">{benefit.explanation}</p>
        <Notes benefit={benefit} />
        <WhyDetails benefit={benefit} language={language} />
      </div>
    </details>
  );
}

export default function BenefitsFound() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const requestKey = `${token}:${language}`;
  // Which request the shown data belongs to; loading until it matches.
  const [loaded, setLoaded] = useState({ key: null, benefits: [], trace: [] });
  const loading = loaded.key !== requestKey;
  const { benefits, trace } = loaded;

  useEffect(() => {
    fetchBenefits(token, language || "en")
      .then((data) => setLoaded({ key: requestKey, benefits: data.results, trace: data.trace }))
      .catch(() => setLoaded({ key: requestKey, benefits: [], trace: [] }));
  }, [token, language, requestKey]);

  const eligible = benefits.filter(isEligible);
  const notNow = benefits.filter((b) => !isEligible(b));
  const disclaimers = [...new Set(benefits.map((b) => b.disclaimer).filter(Boolean))];
  const canApplyMsp = benefits.some(
    (b) => MSP_PROGRAMS.has(b.program) && (b.status === "likely" || b.status === "possible"),
  );

  return (
    <Layout title={t(language, "benefitsFoundTitle")} backTo="/home">
      {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}

      {!loading && eligible.length > 0 && (
        <div className="section benefit-stack">
          <h3>{t(language, "benefitsForYou")}</h3>
          {eligible.map((b) => (
            <EligibleCard key={b.program} benefit={b} language={language} />
          ))}
        </div>
      )}

      {canApplyMsp && (
        <div className="section">
          <BigButton to="/apply">{t(language, "applyCta")}</BigButton>
          <p className="review-source" style={{ margin: "6px 4px 0" }}>
            {t(language, "applyCtaHelp")}
          </p>
        </div>
      )}

      {!loading && notNow.length > 0 && (
        <div className="section">
          <h3>{t(language, "benefitsNotNow")}</h3>
          <div className="ios-list">
            {notNow.map((b) => (
              <NotNowRow key={b.program} benefit={b} language={language} />
            ))}
          </div>
        </div>
      )}

      <div className="section">
        <div className="ios-list">
          <Link to="/application-pack" className="nav-row">
            {t(language, "seeApplicationPack")}
            <span className="nav-row-chevron">{"›"}</span>
          </Link>
          <Link to="/caseworker-card" className="nav-row">
            {t(language, "seeCaseworkerCard")}
            <span className="nav-row-chevron">{"›"}</span>
          </Link>
        </div>
      </div>

      {disclaimers.map((d) => (
        <p key={d} className="benefit-footnote">
          {d}
        </p>
      ))}

      <TracePanel trace={trace} />
    </Layout>
  );
}
