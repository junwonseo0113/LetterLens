import { formatMoney } from "./format";
import { UI_STRINGS, t } from "./strings";

const MONEY_FIELDS = new Set(["monthly_social_security", "monthly_work_income"]);

// Application document status -> label. "uploaded" is only a photo (photos
// are discarded for privacy, so nobody can check it later); "verified"
// means a caseworker saw the original.
export const DOC_STATUS_KEY = {
  verified: "docVerified",
  signed: "docSigned",
  from_letter: "docFromLetter",
  uploaded: "docPhotographed",
  missing: "docMissing",
};

// Field/document wording lives in strings.js for every language; the
// backend's English/Chinese labels are the fallback for unknown keys.
function lookup(language, key, fallback) {
  return UI_STRINGS.en[key] ? t(language, key) : fallback;
}

export function question(field, language) {
  return lookup(language, `q_${field.key}`, language === "zh" ? field.question_zh : field.question_en);
}

export function label(field, language) {
  return lookup(language, `field_${field.key}`, language === "zh" ? field.label_zh : field.label_en);
}

export function documentLabel(doc, language) {
  return lookup(language, `doc_${doc.key}`, language === "zh" ? doc.label_zh : doc.label_en);
}

export function displayValue(field, language) {
  if (field.value === null) return "—";
  if (field.kind === "yesno") return t(language, field.value === "yes" ? "yes" : "no");
  if (MONEY_FIELDS.has(field.key)) return `$${formatMoney(Number(field.value))}`;
  return field.value;
}
