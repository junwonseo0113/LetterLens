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
import { benefitTone } from "../benefitTone";
import { speechLang } from "../speech";

const MSP_PROGRAMS = new Set(["QMB", "QI", "MSP"]);

function readAloud(text, lang) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 0.9;
  window.speechSynthesis.speak(utterance);
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

  const canApplyMsp = benefits.some(
    (b) => MSP_PROGRAMS.has(b.program) && (b.status === "likely" || b.status === "possible"),
  );

  const relevant = benefits.filter((b) => b.status === "likely" || b.status === "possible");
  const notNow = benefits.filter((b) => b.status !== "likely" && b.status !== "possible");

  return (
    <Layout title={t(language, "benefitsFoundTitle")} backTo="/home">
      {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}

      {!loading && relevant.length > 0 && (
        <div className="section">
          <h3>{t(language, "likelyBenefitsLabel")}</h3>
          {relevant.map((b) => (
            <div className="benefit-card2" key={b.program} style={{ marginBottom: 16 }}>
              <div className={`benefit-band tone-${benefitTone(b.program)}`}>
                <IconBadge kind={b.program} size={40} />
                <h2>{b.program}</h2>
                <span className={`badge ${b.status}`}>{t(language, STATUS_KEY[b.status])}</span>
              </div>

              <div className="benefit-body">
                {b.annual_value > 0 && (
                  <>
                    <p className="benefit-amount">${formatMoney(b.annual_value)}</p>
                    <p className="benefit-amount-sub">
                      {t(language, "annualValue")} &middot; ${formatMoney(b.monthly_value)}{" "}
                      {t(language, "monthlyValue")}
                    </p>
                  </>
                )}

                <p>{b.explanation}</p>

                <button
                  type="button"
                  className="speak-pill"
                  onClick={() => readAloud(b.explanation, speechLang(language))}
                >
                  {"\u{1F50A}"} {t(language, "readAloud")}
                </button>

                {b.myth_busting_lines?.map((line, i) => (
                  <p key={i} className="myth-line">
                    {"\u{1F4A1}"} {line}
                  </p>
                ))}

                {b.warnings?.map((w, i) => (
                  <p key={i} className="warning-line">
                    {"⚠"} {w}
                  </p>
                ))}

                <details>
                  <summary>
                    {t(language, "why")} / {t(language, "numbersUsed")}
                  </summary>
                  <p>{b.rule_applied}</p>
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
                  <p>
                    {t(language, "confidence")}: {confidenceLabel(language, b.confidence)}
                  </p>
                </details>

                <p className="disclaimer">{b.disclaimer}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && notNow.length > 0 && (
        <div className="section">
          <h3>{t(language, "notNowLabel")}</h3>
          <div className="ios-list">
            {notNow.map((b) => (
              <details key={b.program} className="nav-row-details">
                <summary className="nav-row">
                  <IconBadge kind={b.program} size={32} />
                  <span style={{ flex: 1 }}>{b.program}</span>
                  <span className="status-text not_now">{t(language, STATUS_KEY[b.status])}</span>
                </summary>
                <div className="nav-row-details-body">
                  <p>{b.explanation}</p>
                  <p className="review-source">{b.rule_applied}</p>
                </div>
              </details>
            ))}
          </div>
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

      <TracePanel trace={trace} />
    </Layout>
  );
}
