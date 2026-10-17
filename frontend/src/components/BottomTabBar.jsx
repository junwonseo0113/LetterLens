import { useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";
import { uploadLetter } from "../api";

const USER_ID = "demo";

function TabIcon({ icon, active }) {
  const color = active ? "var(--color-primary)" : "var(--color-muted)";
  if (icon === "home") {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path
          d="M4 11L12 4l8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1v-8z"
          stroke={color}
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (icon === "letters") {
    return (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="5" width="18" height="14" rx="2" stroke={color} strokeWidth="1.8" />
        <path d="M3 7l9 6 9-6" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  // benefits
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="8" width="18" height="12" rx="2" stroke={color} strokeWidth="1.8" />
      <path d="M3 12h18" stroke={color} strokeWidth="1.8" />
      <path d="M12 4v4M9 6h6" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export default function BottomTabBar() {
  const { language } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    try {
      const result = await uploadLetter({ file, language: language || "en", userId: USER_ID });
      navigate("/letter-result", { state: { result } });
    } catch {
      // Home's own upload button surfaces detailed errors; the tab bar's
      // scan shortcut fails quietly rather than showing a toast here.
    } finally {
      setUploading(false);
    }
  }

  function goToLetters() {
    navigate("/home", { state: { scrollTo: "past-letters" } });
  }

  const isHome = location.pathname === "/home" && !location.state?.scrollTo;
  const isBenefits = location.pathname === "/benefits";

  return (
    <nav className="tab-bar no-print">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <button className="tab-bar-item" type="button" onClick={() => navigate("/home")}>
        <TabIcon icon="home" active={isHome} />
        <span style={{ color: isHome ? "var(--color-primary)" : "var(--color-muted)" }}>
          {t(language, "tabHome")}
        </span>
      </button>

      <button className="tab-bar-item" type="button" onClick={goToLetters}>
        <TabIcon icon="letters" active={false} />
        <span style={{ color: "var(--color-muted)" }}>{t(language, "tabLetters")}</span>
      </button>

      <button
        className="tab-bar-scan"
        type="button"
        disabled={uploading}
        aria-label={t(language, "takePhoto")}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? "…" : "\u{1F4F7}"}
      </button>

      <button className="tab-bar-item" type="button" onClick={() => navigate("/benefits")}>
        <TabIcon icon="benefits" active={isBenefits} />
        <span style={{ color: isBenefits ? "var(--color-primary)" : "var(--color-muted)" }}>
          {t(language, "tabBenefits")}
        </span>
      </button>
    </nav>
  );
}
