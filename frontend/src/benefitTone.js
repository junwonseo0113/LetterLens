const TONE = { QMB: "pink", MSP: "pink", QI: "pink", "Extra Help": "yellow", SNAP: "green" };

export function benefitTone(program) {
  return TONE[program] || "blue";
}
