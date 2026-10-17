import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";

export default function BillCheckResult() {
  const { language } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const billCheck = location.state?.billCheck;

  useEffect(() => {
    if (!billCheck) navigate("/home", { replace: true });
  }, [billCheck, navigate]);

  if (!billCheck) return null;

  return (
    <Layout title={t(language, "billCheckTitle")} backTo="/home">
      <p>
        <strong>{billCheck.provider}</strong>
      </p>

      {!billCheck.has_flagged && <p>{t(language, "noChargesFlagged")}</p>}

      {billCheck.has_flagged && (
        <>
          <div className="flagged">
            <h2>{t(language, "flaggedCharges")}</h2>
            <ul>
              {billCheck.flagged_line_items.map((item, i) => (
                <li key={i}>
                  {item.description} &mdash; ${item.amount.toFixed(2)} ({item.category})
                  <br />
                  <small>{item.reason}</small>
                </li>
              ))}
            </ul>
          </div>

          {billCheck.dispute_letter && (
            <section>
              <h2>{t(language, "disputeLetter")}</h2>
              <h3>{t(language, "english")}</h3>
              <pre className="letter-text">{billCheck.dispute_letter.english}</pre>
              <h3>{t(language, "translated")}</h3>
              <pre className="letter-text">{billCheck.dispute_letter.translated}</pre>
            </section>
          )}
        </>
      )}
    </Layout>
  );
}
