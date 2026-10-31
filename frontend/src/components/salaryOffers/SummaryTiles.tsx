import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import type { LevelSummary } from "../../types/salaryOffers";
import { formatShare, formatShekelThousands, formatShekels } from "./offerFormat";

const t = salaryOfferPages;

function Tile({ label, value, hint, tone = "default" }: {
  label: string; value: string | null; hint: string; tone?: "default" | "positive";
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <span className="text-sm text-slate-600">{label}</span>
      {value === null
        ? <span className="py-1.5 text-sm font-medium text-slate-500">{t.notEnoughOffers}</span>
        : <span className={`ltr text-start text-3xl font-extrabold ${tone === "positive" ? "text-success-700" : ""}`}>{value}</span>}
      <span className="text-xs text-slate-600">{hint}</span>
    </div>
  );
}

export function SummaryTiles({ summary }: { summary: LevelSummary }) {
  const salary = summary.total_salary;
  const gain = summary.average_negotiation_gain;
  return (
    <section aria-label={t.title} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Tile label={t.tiles.median} value={salary && formatShekels(salary.median)} hint={t.tiles.medianHint} />
      <Tile label={t.tiles.range} hint={t.tiles.rangeHint}
            value={salary && `${formatShekelThousands(salary.low_quartile)}–${formatShekelThousands(salary.high_quartile)}`} />
      <Tile label={t.tiles.gain} tone="positive" value={gain === null ? null : `+${formatShare(gain)}`}
            hint={summary.negotiated_share === null ? "" : t.tiles.gainHint(formatShare(summary.negotiated_share))} />
      <Tile label={t.tiles.count} value={String(summary.offer_count)} hint={t.tiles.countHint} />
    </section>
  );
}
