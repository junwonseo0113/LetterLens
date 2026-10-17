// Colored category icon badges -- letter types and benefit programs each
// get a distinct color + glyph so lists are scannable at a glance, not
// just a wall of text. Plain SVG primitives, no illustration library.

const STYLES = {
  ssa_benefit_letter: { bg: "#34C759", icon: "benefit" },
  bank_statement: { bg: "#007AFF", icon: "bank" },
  hra_renewal_notice: { bg: "#FF9500", icon: "renewal" },
  medical_bill: { bg: "#FF3B30", icon: "bill" },
  medicare_notice: { bg: "#AF52DE", icon: "doc" },
  other: { bg: "#8E8E93", icon: "doc" },
  QMB: { bg: "#007AFF", icon: "plus" },
  MSP: { bg: "#007AFF", icon: "plus" },
  "Extra Help": { bg: "#AF52DE", icon: "pill" },
  SNAP: { bg: "#FF9500", icon: "bag" },
};

function Glyph({ icon }) {
  const s = "#fff";
  const w = 2;
  switch (icon) {
    case "plus":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke={s} strokeWidth={w} />
          <path d="M12 8v8M8 12h8" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
    case "pill":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect
            x="4"
            y="10"
            width="16"
            height="7"
            rx="3.5"
            transform="rotate(-30 12 13.5)"
            stroke={s}
            strokeWidth={w}
          />
          <path d="M10.3 9.3l3.4 5.9" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
    case "bag":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M6 9h12l-1 11H7L6 9z" stroke={s} strokeWidth={w} strokeLinejoin="round" />
          <path d="M9 9V7a3 3 0 0 1 6 0v2" stroke={s} strokeWidth={w} />
        </svg>
      );
    case "bank":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M4 10l8-5 8 5" stroke={s} strokeWidth={w} strokeLinejoin="round" />
          <path d="M5 10h14v8H5z" stroke={s} strokeWidth={w} strokeLinejoin="round" />
          <path d="M3 20h18" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
    case "renewal":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="4" y="5" width="16" height="15" rx="2" stroke={s} strokeWidth={w} />
          <path d="M4 9h16M8 3v4M16 3v4" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
    case "bill":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="5" y="3" width="14" height="18" rx="2" stroke={s} strokeWidth={w} />
          <path d="M9 8h6M9 12h6M9 16h3" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
    case "benefit":
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke={s} strokeWidth={w} />
          <path d="M9 12.5l2 2 4-4.5" stroke={s} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    default:
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <rect x="5" y="3" width="14" height="18" rx="2" stroke={s} strokeWidth={w} />
          <path d="M9 8h6M9 12h6M9 16h4" stroke={s} strokeWidth={w} strokeLinecap="round" />
        </svg>
      );
  }
}

export default function IconBadge({ kind, size = 40 }) {
  const style = STYLES[kind] || STYLES.other;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.28,
        background: style.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
      aria-hidden="true"
    >
      <Glyph icon={style.icon} />
    </div>
  );
}
