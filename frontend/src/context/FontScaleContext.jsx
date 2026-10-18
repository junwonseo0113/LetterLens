import { useEffect, useState } from "react";
import { FontScaleContext } from "./contexts";

const STORAGE_KEY = "letterlens_font_scale";
const STEPS = [1, 1.15, 1.3];

function load() {
  const saved = Number(localStorage.getItem(STORAGE_KEY));
  return STEPS.includes(saved) ? saved : STEPS[0];
}

export function FontScaleProvider({ children }) {
  const [scale, setScale] = useState(load);

  useEffect(() => {
    document.documentElement.style.setProperty("--font-scale", String(scale));
    localStorage.setItem(STORAGE_KEY, String(scale));
  }, [scale]);

  function cycleScale() {
    const i = STEPS.indexOf(scale);
    setScale(STEPS[(i + 1) % STEPS.length]);
  }

  return (
    <FontScaleContext.Provider value={{ scale, cycleScale }}>{children}</FontScaleContext.Provider>
  );
}
