import { formatMoney } from "./format";
import { t } from "./strings";

const MONEY_FIELDS = new Set(["gross_monthly_benefit", "part_b_deduction", "net_payment", "ending_balance"]);

// How a fact read from a letter is shown (null = nothing to show).
export function formatField(key, value, language) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "boolean") return t(language, value ? "yes" : "no");
  if (MONEY_FIELDS.has(key) && typeof value === "number") return `$${formatMoney(value)}`;
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return value
      .map((item) =>
        typeof item === "object" ? `${item.description}: $${formatMoney(item.amount)}` : String(item),
      )
      .join("; ");
  }
  return String(value);
}
