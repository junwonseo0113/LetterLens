import { useNavigate } from "react-router-dom";
import { useLanguage } from "../context/useLanguage";
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
      <div className="section">
        <h3>{t(language || "en", "chooseLanguage")}</h3>
        <div className="lang-grid">
          {LANGUAGES.map((l) => (
            <button key={l.code} type="button" onClick={() => choose(l.code)}>
              {l.native}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
