import { Link } from "react-router-dom";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

export default function Layout({ title, backTo, children, actions }) {
  const { language } = useLanguage();
  return (
    <div className="app-shell">
      <header className="app-header">
        {backTo ? (
          <Link to={backTo} className="back-link no-print">
            &larr; {t(language, "back")}
          </Link>
        ) : (
          <span />
        )}
        {actions}
      </header>
      {title && <h1>{title}</h1>}
      {children}
    </div>
  );
}
