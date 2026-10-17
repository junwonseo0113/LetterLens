import { useNavigate } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import { LANGUAGES, t } from "../strings";

export default function LanguagePicker() {
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  function choose(code) {
    setLanguage(code);
    navigate("/home");
  }

  return (
    <div className="app-shell">
      <h1>LetterLens</h1>
      <p style={{ fontSize: 22 }}>{t(language || "en", "chooseLanguage")}</p>
      <div className="lang-grid">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            className="big-button secondary"
            onClick={() => choose(l.code)}
          >
            {l.native}
          </button>
        ))}
      </div>
    </div>
  );
}
