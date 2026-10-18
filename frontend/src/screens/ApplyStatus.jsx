import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import ErrorBox from "../components/ErrorBox";
import Layout from "../components/Layout";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { fetchCurrentApplication } from "../api";
import { useLoad } from "../hooks/useLoad";
import { DOC_STATUS_KEY, documentLabel } from "../applicationFields";

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
  // Only LOOK at the application -- never start one here (someone who came
  // for SNAP mustn't end up with an MSP application).
  const { loading, data: application, error, reload } = useLoad(() => fetchCurrentApplication(token), [token]);

  useEffect(() => {
    if (application?.status === "draft") navigate("/apply", { replace: true });
  }, [application, navigate]);

  if (loading || error || application?.status === "draft") {
    return (
      <Layout backTo="/home">
        {loading && <p className="spinner-wrap">{t(language, "loading")}</p>}
        {error && <ErrorBox title={t(language, "errLoadApplication")} error={error} onRetry={reload} />}
      </Layout>
    );
  }

  if (!application) {
    return (
      <Layout title={t(language, "statusTitle")} backTo="/home">
        <div className="card">
          <h2>{t(language, "noApplicationTitle")}</h2>
          <p>{t(language, "noApplicationBody")}</p>
        </div>
        <BigButton to="/benefits">{t(language, "goToBenefits")}</BigButton>
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
          {/* Missing documents vs. ones provided but not yet checked in person. */}
          <p>
            {application.missing_documents.length > 0
              ? t(language, "needsReviewBody")
              : t(language, "needsReviewUnverified")}
          </p>
          <ul style={{ listStyle: "none", paddingLeft: 0 }}>
            {application.documents
              .filter((d) => application.review_reason.includes(d.key))
              .map((d) => (
                <li key={d.key}>
                  {"⬜"} {documentLabel(d, language)}{" "}
                  <span className="review-source">({t(language, DOC_STATUS_KEY[d.status])})</span>
                </li>
              ))}
          </ul>
          {application.unverified_documents.length > 0 && (
            <p className="review-source">{t(language, "docUnverifiedNote")}</p>
          )}
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
