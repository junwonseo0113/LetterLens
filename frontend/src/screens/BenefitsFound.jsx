import { useEffect, useState } from "react";
import BigButton from "../components/BigButton";
import IconBadge from "../components/IconBadge";
import Layout from "../components/Layout";
import TracePanel from "../components/TracePanel";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, confidenceLabel, numberLabel, t } from "../strings";
import { formatMoney } from "../format";
import { fetchBenefits } from "../api";

const MSP_PROGRAMS = new Set(["QMB", "QI", "MSP"]);

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

  return (
    <Layout title={t(language, "benefitsFoundTitle")} backTo="/home">
      {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}

      {!loading &&
        benefits.map((b) => (
          <div className="card benefit-card" key={b.program}>
            <div className="benefit-card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <IconBadge kind={b.program} size={36} />
                <h2 style={{ margin: 0 }}>{b.program}</h2>
              </div>
              <span className={`status-text ${b.status}`}>{t(language, STATUS_KEY[b.status])}</span>
            </div>

            {b.annual_value > 0 && (
              <p>
                <strong>${formatMoney(b.annual_value)}</strong> {t(language, "annualValue")} ($
                {formatMoney(b.monthly_value)} {t(language, "monthlyValue")})
              </p>
            )}

            <p>{b.explanation}</p>

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
        ))}

      {canApplyMsp && (
        <div className="section">
          <BigButton to="/apply">{t(language, "applyCta")}</BigButton>
          <p className="review-source" style={{ margin: "6px 4px 0" }}>
            {t(language, "applyCtaHelp")}
          </p>
        </div>
      )}

      <BigButton to="/application-pack" variant="secondary">
        {t(language, "seeApplicationPack")}
      </BigButton>
      <BigButton to="/caseworker-card" variant="secondary">
        {t(language, "seeCaseworkerCard")}
      </BigButton>

      <TracePanel trace={trace} />
    </Layout>
  );
}
