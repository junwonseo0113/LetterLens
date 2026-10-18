import { formatMoney } from "./format";

const MONEY_FIELDS = new Set(["monthly_social_security", "monthly_work_income"]);

export function question(field, language) {
  return language === "zh" ? field.question_zh : field.question_en;
}

export function label(field, language) {
  return language === "zh" ? field.label_zh : field.label_en;
}

export function displayValue(field, language) {
  if (field.value === null) return "—";
  if (field.kind === "yesno") {
    if (language === "zh") return field.value === "yes" ? "是" : "否";
    return field.value === "yes" ? "Yes" : "No";
  }
  if (MONEY_FIELDS.has(field.key)) return `$${formatMoney(Number(field.value))}`;
  return field.value;
}
