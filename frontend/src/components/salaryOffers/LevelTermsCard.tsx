import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import type { LevelSummary, ValueRange } from "../../types/salaryOffers";
import { Card } from "../ui/Card";
import { formatDays, formatShare } from "./offerFormat";

const t = salaryOfferPages.levelTerms;

interface TermFigure {
  label: string;
  value: string;
  detail: string;
}

function rangeFigure(label: string, range: ValueRange | null, format: (value: number) => string): TermFigure | null {
  return range && {
    label,
    value: t.median(format(range.median)),
    detail: t.range(format(range.low_quartile), format(range.high_quartile)),
  };
}

function shareFigure(label: string, share: number | null): TermFigure | null {
  return share === null ? null : { label, value: formatShare(share), detail: t.ofOffers };
}

function levelTermFigures(summary: LevelSummary): TermFigure[] {
  return [
    rangeFigure(t.vacationDays, summary.vacation_days, formatDays),
    rangeFigure(t.baseShare, summary.base_share, formatShare),
    shareFigure(t.studyFundFirstDay, summary.study_fund_from_first_day_share),
    shareFigure(t.sickAboveLaw, summary.sick_pay_above_law_share),
    rangeFigure(t.negativeVacation, summary.negative_vacation_days, formatDays),
    shareFigure(t.healthInsurance, summary.health_insurance_share),
  ].filter((figure): figure is TermFigure => figure !== null);
}

export function LevelTermsCard({ summary }: { summary: LevelSummary }) {
  const figures = levelTermFigures(summary);
  return (
    <Card title={t.title}>
      {figures.length ? (
        <dl className="divide-y divide-slate-100">
          {figures.map((figure) => (
            <div key={figure.label} className="flex items-baseline justify-between gap-3 py-2.5">
              <dt className="text-sm text-slate-700">{figure.label}</dt>
              <dd className="flex flex-col items-end">
                <span className="font-extrabold text-brand-900">{figure.value}</span>
                <span className="text-xs text-slate-600">{figure.detail}</span>
              </dd>
            </div>
          ))}
        </dl>
      ) : <p className="text-sm text-slate-600">{salaryOfferPages.notEnoughOffers}</p>}
      <p className="mt-3 text-xs text-slate-600">{t.hint}</p>
    </Card>
  );
}
