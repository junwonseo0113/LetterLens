import { useEffect, useRef } from "react";
import { useLanguage } from "../context/LanguageContext";
import { t } from "../strings";

// Finger/mouse signature on a canvas. Calls onChange with a PNG data URL
// after each stroke, or null when cleared.
export default function SignaturePad({ onChange }) {
  const { language } = useLanguage();
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);
  const hasInkRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * ratio;
    canvas.height = canvas.offsetHeight * ratio;
    const ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#000";
  }, []);

  function point(event) {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function start(event) {
    event.preventDefault();
    canvasRef.current.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    const ctx = canvasRef.current.getContext("2d");
    const { x, y } = point(event);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function move(event) {
    if (!drawingRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    const { x, y } = point(event);
    ctx.lineTo(x, y);
    ctx.stroke();
    hasInkRef.current = true;
  }

  function end() {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (hasInkRef.current) onChange(canvasRef.current.toDataURL("image/png"));
  }

  function clear() {
    const canvas = canvasRef.current;
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    hasInkRef.current = false;
    onChange(null);
  }

  return (
    <div>
      <canvas
        ref={canvasRef}
        className="signature-pad"
        aria-label={t(language, "signHere")}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
        <span style={{ color: "var(--color-muted)", fontSize: "var(--font-size-xs)" }}>{t(language, "signHere")}</span>
        <button type="button" className="link-button" onClick={clear}>
          {t(language, "clearSignature")}
        </button>
      </div>
    </div>
  );
}
