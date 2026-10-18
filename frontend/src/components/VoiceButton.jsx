import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

// Browser speech recognition (Chrome, Edge, iOS Safari 14.5+). No audio
// leaves the device through our backend -- only the recognized text does.
const SpeechRecognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function VoiceButton({ lang, onResult }) {
  const { language } = useLanguage();
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  if (!SpeechRecognition) {
    return <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)" }}>{t(language, "voiceUnsupported")}</p>;
  }

  function toggle() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript;
      if (text) onResult(text);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }

  return (
    <button type="button" className={`voice-button ${listening ? "listening" : ""}`} onClick={toggle}>
      <span aria-hidden="true">{"\u{1F3A4}"}</span> {t(language, listening ? "listening" : "speak")}
    </button>
  );
}
