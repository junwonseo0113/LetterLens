const SPEECH_LANG = {
  en: "en-US",
  ko: "ko-KR",
  es: "es-US",
  ru: "ru-RU",
};

// BCP-47 tag for the browser's speech recognizer / synthesizer.
export function speechLang(language, dialect) {
  if (language === "zh") return dialect === "cantonese" ? "zh-HK" : "zh-CN";
  return SPEECH_LANG[language] || "en-US";
}
