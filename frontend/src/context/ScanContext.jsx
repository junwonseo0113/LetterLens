import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import ErrorBox from "../components/ErrorBox";
import { fetchPrivacyInfo, readLetter } from "../api";
import { shrinkImage } from "../shrinkImage";
import { t } from "../strings";
import { ScanContext } from "./contexts";
import { useAuth } from "./useAuth";
import { useLanguage } from "./useLanguage";

const NOTICE_KEY = "letterlens_scan_notice_ok";

// One scan flow for every camera button:
//   notice (what happens to the photo) -> pick photo -> read (cancellable)
//   -> draft held in memory -> /letters/review, where the user confirms.
// The photo (File), its shrunk copy and its preview URL are released when
// reading succeeds or is cancelled; after a failure they're kept only so
// "Try again" can resend, and released on "Close".
export function ScanProvider({ children }) {
  const { language } = useLanguage();
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef(null);
  const fileRef = useRef(null);
  const controllerRef = useRef(null);
  const previewRef = useRef(null);
  const [phase, setPhase] = useState("idle"); // idle | notice | reading | error
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState(null); // in memory only -- never stored
  // undefined = still checking which processors are in use; null = couldn't tell.
  const [info, setInfo] = useState(undefined);
  const [dontShow, setDontShow] = useState(false);

  const release = useCallback(() => {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = null;
    fileRef.current = null;
    controllerRef.current = null;
    setPreview(null);
  }, []);

  // Leaving the app entirely: release anything still held.
  useEffect(() => () => {
    controllerRef.current?.abort();
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
  }, []);

  async function read() {
    const file = fileRef.current;
    if (!file) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    setPhase("reading");
    setError(null);
    try {
      const small = await shrinkImage(file);
      const result = await readLetter({
        file: small,
        name: file.name,
        language: language || "en",
        token,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      release();
      setPhase("idle");
      setDraft(result);
      navigate("/letters/review");
    } catch (err) {
      if (controller.signal.aborted || err.name === "AbortError") return; // cancelled: already released
      setError(err);
      setPhase("error"); // keep the photo so "Try again" can resend it
    }
  }

  function pickFile() {
    inputRef.current?.click();
  }

  function startScan() {
    if (phase === "reading") return;
    setDraft(null); // a new scan replaces any unsaved one
    if (localStorage.getItem(NOTICE_KEY) === "1") {
      pickFile();
      return;
    }
    setPhase("notice");
    setInfo(undefined);
    fetchPrivacyInfo()
      .then(setInfo)
      .catch(() => setInfo(null));
  }

  function acceptNotice() {
    if (dontShow) localStorage.setItem(NOTICE_KEY, "1");
    setPhase("idle");
    pickFile();
  }

  function onFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = ""; // drop the input's own reference to the file
    if (!file) return;
    release();
    fileRef.current = file;
    previewRef.current = URL.createObjectURL(file);
    setPreview(previewRef.current);
    read();
  }

  function cancel() {
    controllerRef.current?.abort();
    release();
    setPhase("idle");
  }

  function dismissError() {
    release();
    setError(null);
    setPhase("idle");
  }

  const value = {
    startScan,
    scanning: phase === "reading",
    // Only reachable on the review screen: leaving it drops the unsaved scan
    // from view, and the next scan replaces it.
    draft: location.pathname === "/letters/review" ? draft : null,
    clearDraft: () => setDraft(null),
  };

  return (
    <ScanContext.Provider value={value}>
      {children}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={onFileChange}
      />

      {phase === "notice" && (
        <div className="scan-overlay" role="dialog" aria-modal="true" aria-labelledby="scan-notice-title">
          <div className="scan-sheet">
            <h2 id="scan-notice-title">{t(language, "noticeTitle")}</h2>
            <ul className="notice-list">
              {/* Wait until we know; if we can't tell, assume the photo goes to Oracle. */}
              {info === undefined ? (
                <li>{t(language, "loading")}</li>
              ) : (
                <li>{t(language, info?.sample_mode ? "noticeSample" : "noticeOci")}</li>
              )}
              <li>{t(language, "noticeDiscard")}</li>
              <li>{t(language, "noticeRetained")}</li>
              <li>{t(language, "noticeNotVerification")}</li>
              <li>{t(language, "noticeKeepOriginals")}</li>
            </ul>
            <Link to="/privacy" onClick={() => setPhase("idle")}>
              {t(language, "privacyLink")}
            </Link>
            <label className="notice-checkbox">
              <input type="checkbox" checked={dontShow} onChange={(e) => setDontShow(e.target.checked)} />
              {t(language, "noticeDontShow")}
            </label>
            <div className="question-buttons">
              <button type="button" className="big-button" onClick={acceptNotice} disabled={info === undefined}>
                {t(language, "noticeContinue")}
              </button>
              <button type="button" className="big-button secondary" onClick={() => setPhase("idle")}>
                {t(language, "cancel")}
              </button>
            </div>
          </div>
        </div>
      )}

      {phase === "reading" && (
        <div className="scan-overlay" role="status">
          <div className="scan-sheet scan-progress">
            {preview && <img src={preview} alt="" className="scan-preview" />}
            <p className="question-text">{t(language, "readingLetter")}</p>
            <button type="button" className="big-button secondary" onClick={cancel}>
              {t(language, "cancel")}
            </button>
          </div>
        </div>
      )}

      {phase === "error" && (
        <div className="scan-overlay">
          <div className="scan-sheet">
            {preview && <img src={preview} alt="" className="scan-preview" />}
            <ErrorBox title={t(language, "errUpload")} error={error} onRetry={read} onDismiss={dismissError} />
          </div>
        </div>
      )}
    </ScanContext.Provider>
  );
}
