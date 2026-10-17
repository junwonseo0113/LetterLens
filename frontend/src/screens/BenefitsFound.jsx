import { useEffect, useState } from "react";
import BigButton from "../components/BigButton";
import Layout from "../components/Layout";
import TracePanel from "../components/TracePanel";
import { useLanguage } from "../context/LanguageContext";
import { STATUS_KEY, t } from "../strings";
import { formatMoney } from "../format";
import { fetchBenefits } from "../api";

const USER_ID = "demo";

export default function BenefitsFound() {
  const { language } = useLanguage();
  const [benefits, setBenefits] = useState([]);
  const [trace, setTrace] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchBenefits(USER_ID, language || "en")
      .then((data) => {
        setBenefits(data.results);
        setTrace(data.trace);
      })
      .finally(() => setLoading(false));
  }, [language]);

  return (
    <Layout title={t(language, "benefitsFoundTitle")} backTo="/home">
      {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}

      {!loading &&
        benefits.map((b) => (
          <div className="card benefit-card" key={b.program}>
            <div className="benefit-card-header">
              <h2 style={{ margin: 0 }}>{b.program}</h2>
              <span className={`badge ${b.status}`}>{t(language, STATUS_KEY[b.status])}</span>
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
                      <td>{key}</td>
                      <td>{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>
                {t(language, "confidence")}: {b.confidence}
              </p>
            </details>

            <p className="disclaimer">{b.disclaimer}</p>
          </div>
        ))}

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
