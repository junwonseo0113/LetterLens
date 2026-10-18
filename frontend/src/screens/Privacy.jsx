import { useState } from "react";
import { Link } from "react-router-dom";
import ErrorBox from "../components/ErrorBox";
import Layout from "../components/Layout";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { deleteMyData, fetchPrivacyInfo } from "../api";
import { useLoad } from "../hooks/useLoad";

// What happens to letters and saved information, plus "Delete my saved
// information". Deleting originals and deleting saved facts are separate:
// originals are never saved, so only saved information can be deleted.
export default function Privacy() {
  const { language } = useLanguage();
  const { token, signOut } = useAuth();
  const info = useLoad(() => fetchPrivacyInfo(), []);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState(null);

  async function handleDelete() {
    setBusy(true);
    setError(null);
    try {
      await deleteMyData(token);
      setDeleted(true);
      signOut();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout title={t(language, "privacyTitle")} backTo={token ? "/home" : "/"}>
      <section className="card">
        <h2>{t(language, "privacyPhotoTitle")}</h2>
        <p>{t(language, "privacyPhotoBody")}</p>
        <p>{t(language, "noticeNotVerification")}</p>
        <p>
          <strong>{t(language, "noticeKeepOriginals")}</strong>
        </p>
      </section>

      <section className="card">
        <h2>{t(language, "privacyProcessorsTitle")}</h2>
        {info.data?.sample_mode ? (
          <p>{t(language, "noticeSample")}</p>
        ) : (
          <>
            <p>
              {t(language, "noticeOci")}
              {info.data?.oci_region && ` (${info.data.oci_region})`}
            </p>
            <p className="review-source">{t(language, "privacyOracleNote")}</p>
          </>
        )}
      </section>

      <section className="card">
        <h2>{t(language, "privacySavedTitle")}</h2>
        <p>{t(language, "privacySavedBody")}</p>
      </section>

      <section className="card">
        <h2>{t(language, "privacyDeleteTitle")}</h2>
        <p className="review-source">{t(language, "privacyOriginalsNote")}</p>
        {deleted ? (
          <p className="notice-ok" role="status">
            {t(language, "privacyDeleted")}
          </p>
        ) : !token ? (
          <p>
            <Link to="/sign-in">{t(language, "privacySignInToDelete")}</Link>
          </p>
        ) : (
          <>
            <p>{t(language, "privacyDeleteBody")}</p>
            <p className="review-source">{t(language, "privacyBackupNote")}</p>
            <label className="notice-checkbox">
              <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
              {t(language, "privacyDeleteConfirm")}
            </label>
            {error && <ErrorBox title={t(language, "errDelete")} error={error} onRetry={handleDelete} />}
            <button
              type="button"
              className="big-button danger"
              disabled={!confirmed || busy}
              onClick={handleDelete}
            >
              {t(language, "privacyDeleteButton")}
            </button>
          </>
        )}
      </section>
    </Layout>
  );
}
