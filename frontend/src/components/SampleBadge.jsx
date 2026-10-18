import { useLanguage } from "../context/useLanguage";
import { t } from "../strings";

// Marks MOCK_MODE sample data so it's never mistaken for the user's own.
export function SampleBadge() {
  const { language } = useLanguage();
  return <span className="sample-badge">{t(language, "sampleBadge")}</span>;
}

export function SampleNote({ textKey }) {
  const { language } = useLanguage();
  return (
    <p className="sample-note" role="note">
      <SampleBadge /> {t(language, textKey)}
    </p>
  );
}
