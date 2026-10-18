import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import BigButton from "../components/BigButton";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { errorText, requestCode, verifyCode } from "../api";

export default function SignIn() {
  const { language } = useLanguage();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [demoCode, setDemoCode] = useState(null);
  const [codeSent, setCodeSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSend(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await requestCode(phone);
      setDemoCode(result.demo_code);
      setCodeSent(true);
    } catch (err) {
      setError(errorText(err, language));
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      signIn(await verifyCode(phone, code));
      navigate(location.state?.from || "/home", { replace: true });
    } catch (err) {
      setError(errorText(err, language));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <h1>{t(language, "signInTitle")}</h1>
      <p>{"\u{1F512}"} {t(language, "signInWhy")}</p>

      {!codeSent ? (
        <form className="section" onSubmit={handleSend}>
          <label htmlFor="phone">
            <h3>{t(language, "phoneLabel")}</h3>
          </label>
          <input
            id="phone"
            className="text-input"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="(718) 555-0142"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <BigButton type="submit" disabled={busy || !phone.trim()} style={{ marginTop: 12 }}>
            {t(language, "sendCode")}
          </BigButton>
        </form>
      ) : (
        <form className="section" onSubmit={handleVerify}>
          {demoCode && (
            <div className="card notice" role="status">
              {t(language, "demoCodeNotice")} <strong style={{ letterSpacing: "0.15em" }}>{demoCode}</strong>
            </div>
          )}
          <label htmlFor="code">
            <h3>{t(language, "codeLabel")}</h3>
          </label>
          <input
            id="code"
            className="text-input"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <BigButton type="submit" disabled={busy || code.trim().length !== 6} style={{ marginTop: 12 }}>
            {t(language, "verify")}
          </BigButton>
          <button type="button" className="link-button" onClick={() => setCodeSent(false)}>
            {t(language, "changeNumber")}
          </button>
        </form>
      )}

      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
    </div>
  );
}
