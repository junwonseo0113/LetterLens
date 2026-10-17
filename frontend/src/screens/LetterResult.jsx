import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import Layout from "../components/Layout";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";

export default function LetterResult() {
  const { language } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result;

  useEffect(() => {
    if (!result) navigate("/home", { replace: true });
  }, [result, navigate]);

  if (!result) return null;

  return (
    <Layout backTo="/home">
      <h2>{t(language, "explanation")}</h2>
      <p>{result.explanation}</p>

      <h2>{t(language, "actionItems")}</h2>
      <ul>
        {result.action_items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>

      {result.deadline && (
        <p>
          <strong>{t(language, "deadline")}:</strong> {result.deadline}
        </p>
      )}

      {result.reminder && (
        <div className="card">
          <strong>{result.reminder.program}</strong> &mdash; {result.reminder.deadline} (
          {result.reminder.days_until_deadline} {t(language, "daysLeft")})
        </div>
      )}

      {result.bill_check && (
        <BigButton to="/bill-check" state={{ billCheck: result.bill_check }} variant="danger">
          {t(language, "seeBillCheck")}
        </BigButton>
      )}

      <BigButton to="/benefits">{t(language, "viewBenefits")}</BigButton>
    </Layout>
  );
}
