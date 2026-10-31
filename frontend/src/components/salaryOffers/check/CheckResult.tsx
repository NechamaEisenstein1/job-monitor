import { useState } from "react";
import { Link } from "react-router-dom";

import { he } from "../../../i18n/he";
import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import type { LevelSummary, ValueRange } from "../../../types/salaryOffers";
import { button } from "../../ui/button";
import { Card } from "../../ui/Card";
import type { OfferFormState } from "../form/offerFormState";
import { formatShare, formatShekelThousands } from "../offerFormat";
import { salaryOfferPaths } from "../salaryOfferPaths";
import type { OfferComparison, OfferPosition } from "./offerComparison";

const t = salaryOfferPages.check;

function PositionBar({ range, total }: { range: ValueRange; total: number }) {
  const low = Math.min(range.low_quartile, total) * 0.9;
  const high = Math.max(range.high_quartile, total) * 1.1;
  const at = (value: number) => `${((value - low) / (high - low)) * 100}%`;
  return (
    <div dir="ltr" className="space-y-2 pt-8">
      <div className="relative h-4 rounded-full bg-slate-100">
        <div className="absolute inset-y-0 rounded-full bg-brand-200"
             style={{ left: at(range.low_quartile), width: `calc(${at(range.high_quartile)} - ${at(range.low_quartile)})` }} />
        <div className="absolute -top-1 h-6 w-[3px] rounded-sm bg-brand-900" style={{ left: at(range.median) }} />
        <div className="absolute -top-8 flex -translate-x-1/2 flex-col items-center" style={{ left: at(total) }}>
          <span className="whitespace-nowrap rounded-md bg-tender-700 px-2 py-0.5 text-xs font-bold text-white">{t.yourOffer}</span>
          <span className="h-7 w-0.5 bg-tender-700" />
        </div>
      </div>
      <div className="flex justify-between text-xs text-slate-600">
        {[range.low_quartile, range.median, range.high_quartile].map((value) => <span key={value}>{formatShekelThousands(value)}</span>)}
      </div>
    </div>
  );
}

function PositionCard({ position, summary, levelLabel }: { position: OfferPosition; summary: LevelSummary; levelLabel: string }) {
  const share = formatShare(position.share);
  return (
    <Card>
      <p className="text-sm text-slate-600">{t.position}</p>
      <h2 className={`mt-1 text-2xl font-extrabold ${position.isBelowMedian ? "text-tender-800" : "text-success-700"}`}>
        {position.isBelowMedian ? t.belowShare(share) : t.aboveShare(share)}
      </h2>
      <p className="mt-1 text-sm text-slate-600">{t.basedOn(summary.offer_count, levelLabel)}</p>
      {summary.total_salary && <PositionBar range={summary.total_salary} total={position.total} />}
    </Card>
  );
}

function TalkingPoints({ points }: { points: string[] }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(points.join("\n"));
    setCopied(true);
  };
  return (
    <section className="rounded-xl border border-brand-200 bg-brand-50 p-5 text-brand-900">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-bold">{t.talkingPoints}</h2>
        {points.length > 0 && <button type="button" onClick={copy} className={button("secondary", "sm")}>{copied ? t.copied : t.copy}</button>}
      </div>
      {points.length
        ? <ul className="mt-3 list-disc space-y-1.5 ps-5">{points.map((point) => <li key={point}>{point}</li>)}</ul>
        : <p className="mt-2 text-sm">{t.noPoints}</p>}
    </section>
  );
}

export function CheckResult({ comparison, summary, form }: { comparison: OfferComparison; summary: LevelSummary; form: OfferFormState }) {
  const levelLabel = he.levelBadge[form.level];
  if (!comparison.position) return <Card><p className="text-sm text-slate-600">{salaryOfferPages.notEnoughOffers}</p></Card>;
  return (
    <div className="space-y-5">
      <PositionCard position={comparison.position} summary={summary} levelLabel={levelLabel} />
      {comparison.terms.length > 0 && (
        <Card title={t.termsTitle} flush>
          <table className="w-full text-sm">
            <thead><tr className="text-start text-xs text-slate-600">
              {[t.term, t.yours, t.typical].map((title) => <th key={title} className="px-4 py-2 text-start font-medium">{title}</th>)}
            </tr></thead>
            <tbody>
              {comparison.terms.map((term) => (
                <tr key={term.label} className="border-t border-slate-100">
                  <td className="px-4 py-2.5">{term.label}</td>
                  <td className={`px-4 py-2.5 font-bold ${term.isWeaker ? "text-tender-800" : ""}`}>{term.yours}</td>
                  <td className="px-4 py-2.5">{term.typical}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <TalkingPoints points={comparison.talkingPoints} />
      <Link to={salaryOfferPaths.share} state={{ offerForm: form }} className={button("primary")}>{t.shareThis}</Link>
    </div>
  );
}
