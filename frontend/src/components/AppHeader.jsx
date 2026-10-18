import { Link } from "react-router-dom";
import { useFontScale } from "../context/useFontScale";
import { LANGUAGES } from "../strings";
import { useLanguage } from "../context/useLanguage";

function BrandMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="2" y="5" width="16" height="12" rx="2" stroke="#fff" strokeWidth="1.8" />
      <path d="M2 7l8 5 8-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="18.5" cy="17.5" r="4" fill="var(--color-primary)" stroke="#fff" strokeWidth="1.6" />
      <path d="M21.2 20.2l2.3 2.3" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default function AppHeader() {
  const { scale, cycleScale } = useFontScale();
  const { language } = useLanguage();
  const native = LANGUAGES.find((l) => l.code === language)?.native || "English";

  return (
    <header className="app-header-v2 no-print">
      <div className="brand">
        <div className="brand-mark">
          <BrandMark />
        </div>
        <span className="brand-name">LetterLens</span>
      </div>
      <div className="header-utils">
        <button
          type="button"
          className="util-pill"
          onClick={cycleScale}
          aria-label="Text size"
          title="Text size"
        >
          <span style={{ fontSize: scale > 1 ? "13px" : "11px", fontWeight: 800 }}>가가</span>
        </button>
        <Link to="/" className="util-pill" aria-label="Language">
          {"\u{1F310}"} {native}
        </Link>
      </div>
    </header>
  );
}
