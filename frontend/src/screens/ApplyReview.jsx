import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import CameraIcon from "../components/CameraIcon";
import Layout from "../components/Layout";
import SignaturePad from "../components/SignaturePad";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { addDocument, answerField, errorText, startApplication, submitApplication } from "../api";
import { displayValue, documentLabel, label } from "../applicationFields";

const EDITABLE = new Set(["draft", "info_requested"]);
const DOC_STATUS_KEY = {
  from_letter: "docFromLetter",
  photographed: "docPhotographed",
  signed: "docSigned",
  missing: "docMissing",
};

function FieldRow({ field, onSave }) {
  const { language } = useLanguage();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  async function save(event) {
    event.preventDefault();
    try {
      await onSave(field.key, draft);
      setEditing(false);
      setError("");
    } catch (err) {
      setError(errorText(err, language));
    }
  }

  return (
    <div className="review-row">
      <div style={{ flex: 1 }}>
        <div className="review-label">{label(field, language)}</div>
        {editing ? (
          <form onSubmit={save}>
            <input className="text-input" autoFocus value={draft} onChange={(e) => setDraft(e.target.value)} />
            {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
            <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
              <button type="submit" className="link-button">{t(language, "save")}</button>
              <button type="button" className="link-button" onClick={() => setEditing(false)}>
                {t(language, "cancel")}
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="review-value">{displayValue(field, language)}</div>
            {field.source && <div className="review-source">{t(language, `source_${field.source}`)}</div>}
          </>
        )}
      </div>
      {!editing && (
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setDraft(field.value ?? "");
            setEditing(true);
          }}
        >
          {t(language, "edit")}
        </button>
      )}
    </div>
  );
}

function DocumentRow({ doc, onPhoto }) {
  const { language } = useLanguage();
  const inputRef = useRef(null);
  const ok = doc.status !== "missing";
  return (
    <div className="review-row">
      <span style={{ flex: 1 }}>
        {ok ? "✅" : "⬜"} {documentLabel(doc, language)}
      </span>
      {doc.status === "missing" && doc.key !== "signed_application" ? (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) onPhoto(doc.key, file);
            }}
          />
          <button
            type="button"
            className="link-button"
            style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            onClick={() => inputRef.current?.click()}
          >
            <CameraIcon size={16} /> {t(language, "addPhoto")}
          </button>
        </>
      ) : (
        <span className={`badge ${ok ? "likely" : "missing_info"}`}>{t(language, DOC_STATUS_KEY[doc.status])}</span>
      )}
    </div>
  );
}

export default function ApplyReview() {
  const { language } = useLanguage();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [signature, setSignature] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    startApplication(token)
      .then((app) => {
        if (!EDITABLE.has(app.status)) return navigate("/apply/status", { replace: true });
        if (app.next_question) return navigate("/apply", { replace: true });
        setApplication(app);
      })
      .catch((err) => setError(errorText(err, language)));
  }, [token, language, navigate]);

  async function saveField(key, value) {
    setApplication(await answerField(token, application.id, key, value));
  }

  async function addPhoto(key, file) {
    try {
      setApplication(await addDocument(token, application.id, key, file));
    } catch (err) {
      setError(errorText(err, language));
    }
  }

  async function handleSubmit() {
    setBusy(true);
    setError("");
    try {
      await submitApplication(token, application.id, signature);
      navigate("/apply/status");
    } catch (err) {
      setError(errorText(err, language));
      setBusy(false);
    }
  }

  if (!application) {
    return (
      <Layout backTo="/benefits">
        <p className="spinner-wrap">{error || t(language, "loading")}</p>
      </Layout>
    );
  }

  return (
    <Layout title={t(language, "reviewTitle")} backTo="/benefits">
      <p>
        {application.covers.join(" + ")} &middot; {t(language, "reviewIntro")}
      </p>

      {application.status === "info_requested" && application.reviewer_note && (
        <div className="card notice warn">
          <strong>{t(language, "caseworkerSays")}:</strong> {application.reviewer_note}
        </div>
      )}

      <section>
        <div className="card ios-list-card">
          {application.fields.map((field) => (
            <FieldRow key={field.key} field={field} onSave={saveField} />
          ))}
        </div>
      </section>

      <section>
        <h3>{t(language, "documentsTitle")}</h3>
        <div className="card ios-list-card">
          {application.documents.map((doc) => (
            <DocumentRow key={doc.key} doc={doc} onPhoto={addPhoto} />
          ))}
        </div>
        {application.missing_documents.length > 0 && (
          <p className="review-source" style={{ margin: "8px 4px 0" }}>
            {"\u{1F9D1}\u{200D}\u{1F4BC}"} {t(language, "missingDocsNote")}
          </p>
        )}
      </section>

      <section className="card">
        <SignaturePad onChange={setSignature} />
        <p style={{ marginTop: 12 }}>{t(language, "attest")}</p>
        {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
        <BigButton onClick={handleSubmit} disabled={busy || !signature}>
          {busy ? t(language, "sending") : t(language, "yesSubmit")}
        </BigButton>
      </section>

      <p className="disclaimer">{t(language, "simulatedNote")}</p>
    </Layout>
  );
}
