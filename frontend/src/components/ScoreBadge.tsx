import { he } from "../i18n/he";

/** Shows the backend-computed junior score. `eligible` decides the color; no threshold logic here. */
export function ScoreBadge({ score, eligible }: { score: number | null | undefined; eligible?: boolean | null }) {
  if (score == null) return <span className="text-slate-400">{he.common.none}</span>;
  const tone = eligible ? "bg-emerald-500" : "bg-slate-400";
  return (
    <span className="inline-flex items-center gap-2 tabular-nums" title={`${he.job.score} ${score.toFixed(2)}`}>
      {/* The bar fills from the start (right) edge in RTL. */}
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-200" aria-hidden>
        <span className={`block h-full ${tone}`} style={{ width: `${Math.round(score * 100)}%` }} />
      </span>
      <span className="ltr text-xs font-medium text-slate-700">{score.toFixed(2)}</span>
    </span>
  );
}
