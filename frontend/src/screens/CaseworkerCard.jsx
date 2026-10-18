import { useEffect, useState } from "react";
import BigButton from "../components/BigButton";
import Layout from "../components/Layout";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { STATUS_KEY, UI_STRINGS, numberLabel, t } from "../strings";
import { fetchBenefits } from "../api";

export default function CaseworkerCard() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const [benefits, setBenefits] = useState([]);

  useEffect(() => {
    fetchBenefits(token, language || "en")
      .then((data) => setBenefits(data.results))
      .catch(() => {});
  }, [token, language]);

  return (
    <Layout backTo="/benefits">
      <div className="no-print">
        <BigButton onClick={() => window.print()}>{t(language, "print")}</BigButton>
      </div>

      <h1>
        {UI_STRINGS.en.caseworkerCardTitle} / {t(language, "caseworkerCardTitle")}
      </h1>

      {benefits.map((b) => (
        <div key={b.program} className="card" style={{ marginBottom: 12 }}>
          <h2>
            {b.program} &mdash; {UI_STRINGS.en[STATUS_KEY[b.status]]} / {t(language, STATUS_KEY[b.status])}
          </h2>
          <p>
            <em>EN:</em> {b.rule_applied_en}
          </p>
          {language && language !== "en" && (
            <p>
              <em>{language.toUpperCase()}:</em> {b.rule_applied}
            </p>
          )}
          <table className="kv-table">
            <tbody>
              {Object.entries(b.numbers_used).map(([key, value]) => (
                <tr key={key}>
                  <td>
                    {numberLabel("en", key)}
                    {language && language !== "en" && ` / ${numberLabel(language, key)}`}
                  </td>
                  <td>{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            <em>{(language || "en").toUpperCase()}:</em> {b.explanation}
          </p>
        </div>
      ))}

      <p className="disclaimer">
        {UI_STRINGS.en.disclaimer} / {t(language, "disclaimer")}
      </p>
    </Layout>
  );
}
