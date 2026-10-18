import { useEffect, useState } from "react";
import { LanguageContext } from "./contexts";

const STORAGE_KEY = "letterlens_language";

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem(STORAGE_KEY) || "");

  useEffect(() => {
    if (language) localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}
