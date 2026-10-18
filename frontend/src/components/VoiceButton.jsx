import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

// Browser speech recognition (Chrome, Edge, iOS Safari 14.5+). No audio
// leaves the device through our backend -- only the recognized text does.
const SpeechRecognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

// SpeechRecognition error codes -> what to tell the user. Typing is always
// available below the button, so every message points there.
const ERROR_KEYS = {
  "not-allowed": "voiceErrPermission",
  "service-not-allowed": "voiceErrPermission",
  "audio-capture": "voiceErrNoMic",
  "no-speech": "voiceErrNoSpeech",
  network: "voiceErrNetwork",
};

function errorKeyFor(code) {
  // Browsers block the microphone on plain-http addresses (a phone opening
  // http://<laptop-ip>:5173); localhost is the only exception.
  if (typeof window !== "undefined" && !window.isSecureContext) return "voiceErrInsecure";
  return ERROR_KEYS[code] || "voiceErrGeneric";
}

export default function VoiceButton({ lang, onResult }) {
  const { language } = useLanguage();
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [errorKey, setErrorKey] = useState(null);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  if (!SpeechRecognition) {
    return <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)" }}>{t(language, "voiceUnsupported")}</p>;
  }

  function toggle() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    setErrorKey(null);
    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript;
      if (text) onResult(text);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = (event) => {
      setListening(false);
      // "aborted" is us stopping it (e.g. leaving the page), not a failure.
      if (event.error !== "aborted") setErrorKey(errorKeyFor(event.error));
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      setErrorKey(errorKeyFor());
    }
  }

  return (
    <>
      <button type="button" className={`voice-button ${listening ? "listening" : ""}`} onClick={toggle}>
        <span aria-hidden="true">{"\u{1F3A4}"}</span> {t(language, listening ? "listening" : "speak")}
      </button>
      {errorKey && (
        <p className="form-error" role="alert">
          {t(language, errorKey)}
        </p>
      )}
    </>
  );
}
