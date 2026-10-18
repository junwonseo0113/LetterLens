import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

function ResourceCard({ name, desc, phone }) {
  return (
    <a className="card" href={`tel:${phone.replace(/[^0-9+]/g, "")}`} style={{ display: "block", textDecoration: "none", color: "inherit" }}>
      <h2 style={{ margin: "0 0 4px" }}>{name}</h2>
      <p style={{ margin: "0 0 10px" }}>{desc}</p>
      <strong style={{ color: "var(--color-primary)", fontSize: "var(--font-size-lg)" }}>{phone}</strong>
    </a>
  );
}

export default function Help() {
  const { language } = useLanguage();
  return (
    <div className="app-shell">
      <AppHeader />
      <h1>{t(language, "helpTitle")}</h1>
      <p>{t(language, "helpIntro")}</p>

      <div className="section">
        <ResourceCard name={t(language, "helpNycAging")} desc={t(language, "helpNycAgingDesc")} phone="311" />
        <ResourceCard
          name={t(language, "helpMedicare")}
          desc={t(language, "helpMedicareDesc")}
          phone="1-800-633-4227"
        />
      </div>

      <Link to="/privacy" className="privacy-link">
        {t(language, "privacyLink")}
      </Link>

      <p className="disclaimer">{t(language, "disclaimer")}</p>
    </div>
  );
}
