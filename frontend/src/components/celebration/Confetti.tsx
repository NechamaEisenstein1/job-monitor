import type { CSSProperties } from "react";

/** Brand, tender and success colors plus two accents, so the burst feels like the site. */
const COLORS = ["#1d4ed8", "#f59e0b", "#10b981", "#db2777", "#60a5fa", "#fbbf24"];

/** Positions are derived from the index, not random, so every burst looks the same. */
function piece(i: number): CSSProperties {
  const width = 6 + (i % 4) * 2;
  return {
    left: `${(i * 37) % 100}%`,
    width,
    height: i % 3 === 0 ? width : width * 1.8,
    background: COLORS[i % COLORS.length],
    borderRadius: i % 4 === 0 ? "50%" : 2,
    "--drift": `${((i % 7) - 3) * 30}px`,
    "--spin": `${360 + (i % 6) * 120}deg`,
    "--delay": `${(i % 9) * 0.07}s`,
    "--duration": `${1.8 + (i % 5) * 0.3}s`,
  } as CSSProperties;
}

/** A one-off burst of falling confetti over its positioned parent (motion: styles/celebration.css). */
export function Confetti({ pieces = 46 }: { pieces?: number }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: pieces }, (_, i) => <span key={i} className="confetti-piece" style={piece(i)} />)}
    </div>
  );
}
