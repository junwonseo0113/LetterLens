import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";
import { serverDetail } from "../api";

// A visible error with an optional "Try again" button. `title` is our own
// plain-language message; the server's detail (if any) is shown under it.
export default function ErrorBox({ title, error, onRetry, onDismiss }) {
  const { language } = useLanguage();
  const detail = serverDetail(error, language);
  return (
    <div className="error-box" role="alert">
      <p className="error-box-title">{title}</p>
      {detail && detail !== title && <p className="error-box-detail">{detail}</p>}
      <div className="error-box-actions">
        {onRetry && (
          <button type="button" className="error-box-retry" onClick={onRetry}>
            {t(language, "retry")}
          </button>
        )}
        {onDismiss && (
          <button type="button" className="error-box-dismiss" onClick={onDismiss}>
            {t(language, "dismiss")}
          </button>
        )}
      </div>
    </div>
  );
}
