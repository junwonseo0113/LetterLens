// Line-art camera glyph -- replaces the 📷 emoji (renders inconsistently
// across platforms/fonts) everywhere the app means "take or scan a photo".
export default function CameraIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path
        d="M4 8.5h3.2l1.4-2h6.8l1.4 2H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5a1 1 0 0 1 1-1z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="13" r="3.4" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="17.3" cy="10.8" r="0.9" fill="currentColor" />
    </svg>
  );
}
