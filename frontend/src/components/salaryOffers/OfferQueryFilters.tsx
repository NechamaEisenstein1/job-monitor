import { he } from "../../i18n/he";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { offerTerms } from "../../i18n/salaryOffers/terms";
import type { ExperienceLevel } from "../../types/api";
import type { ClientType, SalaryOfferQuery } from "../../types/salaryOffers";
import { control, fieldLabel } from "../ui/form";
import { type Choice, SegmentedChoice } from "./ChoiceChips";

const t = salaryOfferPages.filters;
const PERIODS = [6, 12, 24, 60];

export const LEVEL_CHOICES: Choice<ExperienceLevel>[] = [
  { value: "a", label: he.filters.levelShortA },
  { value: "b", label: he.filters.levelShortB },
  { value: "c", label: he.filters.levelShortC },
];

export function OfferQueryFilters({ query, roleTypes, onChange }: {
  query: SalaryOfferQuery; roleTypes: string[]; onChange: (query: SalaryOfferQuery) => void;
}) {
  const update = (change: Partial<SalaryOfferQuery>) => onChange({ ...query, ...change });
  return (
    <section aria-label={t.level} className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`${fieldLabel} min-w-[18rem]`}>
        {t.level}
        <SegmentedChoice label={t.level} choices={LEVEL_CHOICES} selected={query.level} onSelect={(level) => update({ level })} />
      </div>
      <label className={fieldLabel}>
        {t.role}
        <select className={`${control} h-10 min-w-44`} value={query.role_type ?? ""}
                onChange={(e) => update({ role_type: e.target.value || undefined })}>
          <option value="">{t.allRoles}</option>
          {roleTypes.map((role) => <option key={role} value={role}>{he.roles[role] ?? role}</option>)}
        </select>
      </label>
      <label className={fieldLabel}>
        {t.client}
        <select className={`${control} h-10 min-w-40`} value={query.client_type ?? ""}
                onChange={(e) => update({ client_type: (e.target.value || undefined) as ClientType | undefined })}>
          <option value="">{t.allClients}</option>
          {Object.entries(offerTerms.clientType).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className={fieldLabel}>
        {t.period}
        <select className={`${control} h-10 min-w-44`} value={query.months_back}
                onChange={(e) => update({ months_back: Number(e.target.value) })}>
          {PERIODS.map((months) => <option key={months} value={months}>{t.months[months]}</option>)}
        </select>
      </label>
    </section>
  );
}
