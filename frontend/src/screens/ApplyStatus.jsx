import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import Layout from "../components/Layout";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { errorText, startApplication } from "../api";
import { documentLabel } from "../applicationFields";

function Timeline({ steps }) {
  return (
    <ol className="timeline">
      {steps.map((step, i) => (
        <li key={i} className={step.done ? "done" : ""}>
          <span className="timeline-dot" aria-hidden="true" />
          <div>
            <div>{step.label}</div>
            {step.detail && <div className="review-source">{step.detail}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function ApplyStatus() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    startApplication(token)
      .then((app) => {
        if (app.status === "draft") return navigate("/apply", { replace: true });
        setApplication(app);
      })
      .catch((err) => setError(errorText(err, language)));
  }, [token, language, navigate]);

  if (!application) {
    return (
      <Layout backTo="/home">
        <p className="spinner-wrap">{error || t(language, "loading")}</p>
      </Layout>
    );
  }

  const covers = application.covers.join(" + ");

  return (
    <Layout title={t(language, "statusTitle")} backTo="/home">
      {application.status === "submitted" && (
        <>
          <div className="card status-hero success">
            <div className="status-hero-icon">{"✅"}</div>
            <h2>
              {covers} &middot; {t(language, "statusSubmitted")}
            </h2>
            <p>
              {t(language, "confirmationNumber")}: <strong>{application.confirmation_number}</strong>
            </p>
          </div>
          <Timeline
            steps={[
              {
                label: t(language, "timelineSubmitted"),
                detail: new Date(application.submitted_at).toLocaleDateString(),
                done: true,
              },
              { label: t(language, "timelineAgency"), done: false },
              {
                label: t(language, "timelineDecision", { days: application.decision_notice_days }),
                done: false,
              },
            ]}
          />
        </>
      )}

      {application.status === "needs_review" && (
        <div className="card status-hero">
          <div className="status-hero-icon">{"\u{1F9D1}\u{200D}\u{1F4BC}"}</div>
          <h2>{t(language, "statusNeedsReview")}</h2>
          <p>{t(language, "needsReviewBody")}</p>
          <ul style={{ listStyle: "none", paddingLeft: 0 }}>
            {application.documents
              .filter((d) => application.review_reason.includes(d.key))
              .map((d) => (
                <li key={d.key}>
                  {"⬜"} {documentLabel(d, language)}
                </li>
              ))}
          </ul>
        </div>
      )}

      {application.status === "info_requested" && (
        <>
          <div className="card status-hero warn">
            <div className="status-hero-icon">{"\u{1F4DD}"}</div>
            <h2>{t(language, "statusInfoRequested")}</h2>
            <p>
              <strong>{t(language, "caseworkerSays")}:</strong> {application.reviewer_note}
            </p>
          </div>
          <BigButton to="/apply/review">{t(language, "fixAndResend")}</BigButton>
        </>
      )}

      {application.reviewer_note && application.status === "submitted" && (
        <p className="review-source">
          {t(language, "caseworkerSays")}: {application.reviewer_note}
        </p>
      )}

      <p className="disclaimer">{t(language, "simulatedNote")}</p>
    </Layout>
  );
}
