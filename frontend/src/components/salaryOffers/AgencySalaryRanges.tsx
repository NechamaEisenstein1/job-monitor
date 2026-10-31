import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import type { AgencySalaryRange, ValueRange } from "../../types/salaryOffers";
import { Card } from "../ui/Card";
import { formatShekelThousands, formatShekels } from "./offerFormat";

const t = salaryOfferPages.agencies;
const AXIS_STEPS = 4;

interface Scale {
  low: number;
  high: number;
}

function scaleAround(ranges: ValueRange[]): Scale {
  const low = Math.min(...ranges.map((r) => r.low_quartile));
  const high = Math.max(...ranges.map((r) => r.high_quartile));
  const padding = Math.max((high - low) * 0.15, 1000);
  return { low: low - padding, high: high + padding };
}

function positionOnScale(value: number, scale: Scale): string {
  return `${((value - scale.low) / (scale.high - scale.low)) * 100}%`;
}

function RangeBar({ range, scale }: { range: ValueRange; scale: Scale }) {
  const width = ((range.high_quartile - range.low_quartile) / (scale.high - scale.low)) * 100;
  return (
    <div dir="ltr" className="relative h-3.5 rounded-full bg-slate-100">
      <div className="absolute inset-y-0 rounded-full bg-brand-200"
           style={{ left: positionOnScale(range.low_quartile, scale), width: `${width}%` }} />
      <div className="absolute -top-1 h-5.5 w-[3px] rounded-sm bg-brand-900" style={{ left: positionOnScale(range.median, scale) }} />
    </div>
  );
}

function ScaleAxis({ scale }: { scale: Scale }) {
  const ticks = Array.from({ length: AXIS_STEPS + 1 }, (_, i) => scale.low + ((scale.high - scale.low) * i) / AXIS_STEPS);
  return (
    <div dir="ltr" className="flex justify-between text-xs text-slate-600">
      {ticks.map((tick) => <span key={tick}>{formatShekelThousands(Math.round(tick / 100) * 100)}</span>)}
    </div>
  );
}

const ROW = "grid grid-cols-[8.5rem_minmax(0,1fr)_5.5rem] items-center gap-3";

export function AgencySalaryRanges({ agencies }: { agencies: AgencySalaryRange[] }) {
  if (!agencies.length) return null;
  const shownRanges = agencies.flatMap((a) => (a.total_salary ? [a.total_salary] : []));
  const scale = shownRanges.length ? scaleAround(shownRanges) : null;
  return (
    <Card title={t.title}>
      <p className="mb-4 text-sm text-slate-600">{t.hint}</p>
      <ul className="space-y-4">
        {agencies.map((agency) => (
          <li key={agency.agency} className={ROW}>
            <span className="flex min-w-0 flex-col">
              <span className="truncate font-semibold" dir="auto">{agency.agency}</span>
              <span className="text-xs text-slate-600">{t.offers(agency.offer_count)}</span>
            </span>
            {agency.total_salary && scale ? (
              <>
                <RangeBar range={agency.total_salary} scale={scale} />
                <span className="ltr text-end font-bold">{formatShekels(agency.total_salary.median)}</span>
              </>
            ) : (
              <span className="col-span-2 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-xs text-slate-600">
                {t.hidden}
              </span>
            )}
          </li>
        ))}
      </ul>
      {scale && <div className={`${ROW} mt-3`}><span /><ScaleAxis scale={scale} /><span /></div>}
    </Card>
  );
}
