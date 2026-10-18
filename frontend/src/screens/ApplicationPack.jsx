import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";
import { fetchBenefits, fetchMspChecklist, fetchReminders } from "../api";

const USER_ID = "demo";
const MSP_PROGRAMS = new Set(["QMB", "QI", "MSP"]);

export default function ApplicationPack() {
  const { language } = useLanguage();
  const [reminders, setReminders] = useState([]);
  const [benefits, setBenefits] = useState([]);
  const [mspChecklist, setMspChecklist] = useState(null);

  useEffect(() => {
    fetchReminders(USER_ID).then(setReminders).catch(() => {});
    fetchBenefits(USER_ID, language || "en")
      .then((data) => setBenefits(data.results))
      .catch(() => {});
    fetchMspChecklist(USER_ID).then(setMspChecklist).catch(() => {});
  }, [language]);

  const likelyPrograms = benefits.filter((b) => b.status === "likely" || b.status === "possible");
  const showMspChecklist = benefits.some(
    (b) => MSP_PROGRAMS.has(b.program) && (b.status === "likely" || b.status === "possible"),
  );

  return (
    <Layout title={t(language, "applicationPackTitle")} backTo="/benefits">
      {showMspChecklist && mspChecklist && (
        <section>
          <h3>{t(language, "mspChecklistTitle")}</h3>
          <div className="card">
            <ul style={{ listStyle: "none", paddingLeft: 0, margin: 0 }}>
              {mspChecklist.items.map((item) => (
                <li key={item.key} style={{ padding: "4px 0" }}>
                  {item.status === "already_have" ? "✅" : "⬜"} {item.label_ko}
                </li>
              ))}
            </ul>
            <p style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)", margin: "10px 0 0" }}>
              {t(language, "msp45DayNote")}
            </p>
          </div>
        </section>
      )}

      <section>
        <h3>{t(language, "checklist")}</h3>
        {reminders.length === 0 && <p>&mdash;</p>}
        {reminders.map((r) => (
          <div key={r.id} className="card" style={{ marginBottom: 12 }}>
            <div className="benefit-card-header">
              <strong>{r.program}</strong>
              {r.packet && (
                <span className={`badge ${r.packet.all_satisfied ? "likely" : "possible"}`}>
                  {r.packet.satisfied_count}/{r.packet.total_count} {t(language, "documentsReady")}
                </span>
              )}
            </div>
            <ul style={{ listStyle: "none", paddingLeft: 0 }}>
              {(r.packet?.items ?? r.checklist.map((item) => ({ item, satisfied: false }))).map(
                (packetItem, i) => (
                  <li key={i}>
                    {packetItem.satisfied ? "✅" : "⬜"} {packetItem.item}
                  </li>
                ),
              )}
            </ul>
          </div>
        ))}
      </section>

      <section>
        <h3>
          {t(language, "english")} / {t(language, "translated")}
        </h3>
        {likelyPrograms.length === 0 && <p>&mdash;</p>}
        {likelyPrograms.map((b) => (
          <div key={b.program} className="card" style={{ marginBottom: 12 }}>
            <strong>{b.program}</strong>
            <table className="kv-table">
              <tbody>
                {Object.entries(b.numbers_used).map(([key, value]) => (
                  <tr key={key}>
                    <td>{key}</td>
                    <td>{String(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </section>
    </Layout>
  );
}
