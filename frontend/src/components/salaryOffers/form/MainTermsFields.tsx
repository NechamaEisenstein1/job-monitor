import { useState } from "react";

import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import { offerTerms } from "../../../i18n/salaryOffers/terms";
import type { ContributionBase } from "../../../types/salaryOffers";
import { ChoiceChips, choicesFrom } from "../ChoiceChips";
import { SICK_PAY_DETAIL_FIELDS } from "../detailSections";
import { DetailFieldInput } from "./DetailFieldInput";
import { formLabel, formSection, formSectionTitle, tallControl } from "./formStyles";
import { CONTRIBUTION_PRESETS, HOURS_PRESETS, type OfferFormState } from "./offerFormState";
import type { OfferFormControls } from "./useOfferForm";

const t = salaryOfferPages.form;
const CUSTOM = "custom";

const HOURS_CHOICES = [...HOURS_PRESETS.map((hours) => ({ value: hours, label: hours })), { value: CUSTOM, label: t.otherHours }];
const CONTRIBUTION_CHOICES = [
  ...CONTRIBUTION_PRESETS.map((p) => ({ value: p.id, label: `${p.percent}% ${offerTerms.contributionBase[p.base]}` })),
  { value: CUSTOM, label: t.otherContribution },
];

function contributionPresetOf(form: OfferFormState): string | undefined {
  return CONTRIBUTION_PRESETS.find((p) => p.base === form.contribution_base && String(p.percent) === form.contribution_percent)?.id;
}

function HoursChoice({ controls }: { controls: OfferFormControls }) {
  const { form, update } = controls;
  const [custom, setCustom] = useState(() => !HOURS_PRESETS.includes(form.hours_per_day));
  const select = (value: string) => {
    setCustom(value === CUSTOM);
    update({ hours_per_day: value === CUSTOM ? "" : value });
  };
  return (
    <div className="flex flex-col gap-2">
      <ChoiceChips label={t.hoursPerDay} choices={HOURS_CHOICES} selected={custom ? CUSTOM : form.hours_per_day} onSelect={select} />
      {custom && (
        <input required type="number" min={4} max={12} step={0.1} dir="ltr" aria-label={t.hoursPerDay}
               className={`${tallControl} w-32 text-start`} value={form.hours_per_day}
               onChange={(e) => update({ hours_per_day: e.target.value })} />
      )}
    </div>
  );
}

function ContributionChoice({ controls }: { controls: OfferFormControls }) {
  const { form, update } = controls;
  const [custom, setCustom] = useState(() => contributionPresetOf(form) === undefined);
  const select = (value: string) => {
    const preset = CONTRIBUTION_PRESETS.find((p) => p.id === value);
    setCustom(!preset);
    if (preset) update({ contribution_base: preset.base, contribution_percent: String(preset.percent) });
  };
  return (
    <div className="flex flex-col gap-2">
      <ChoiceChips label={t.contributions} choices={CONTRIBUTION_CHOICES} selected={custom ? CUSTOM : contributionPresetOf(form)}
                   onSelect={select} />
      {custom && (
        <div className="flex gap-2">
          <input required type="number" min={1} max={100} dir="ltr" aria-label={t.contributionPercent}
                 className={`${tallControl} w-24 text-start`} value={form.contribution_percent}
                 onChange={(e) => update({ contribution_percent: e.target.value })} />
          <select aria-label={t.contributions} className={`${tallControl} w-36`} value={form.contribution_base}
                  onChange={(e) => update({ contribution_base: e.target.value as ContributionBase })}>
            {Object.entries(offerTerms.contributionBase).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}

export function MainTermsFields({ controls }: { controls: OfferFormControls }) {
  const { form, update } = controls;
  return (
    <fieldset className={formSection}>
      <legend className={`${formSectionTitle} mb-4`}>{t.mainTermsSection}</legend>
      <HoursChoice controls={controls} />
      <ChoiceChips label={t.sickPay} choices={choicesFrom(offerTerms.sickPay)} selected={form.sick_pay}
                   onSelect={(sick_pay) => update({ sick_pay })} />
      {form.sick_pay === "other" && (
        <div className="grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-4">
          {SICK_PAY_DETAIL_FIELDS.map((field) => <DetailFieldInput key={field.key} field={field} controls={controls} />)}
        </div>
      )}
      <ContributionChoice controls={controls} />
      <ChoiceChips label={t.studyFundStart} choices={choicesFrom(offerTerms.studyFundStart)} selected={form.study_fund_start}
                   onSelect={(study_fund_start) => update({ study_fund_start })} />
      <label className={`${formLabel} max-w-48`}>
        {t.vacationDays}
        <input required type="number" min={0} max={40} dir="ltr" className={`${tallControl} text-start`}
               value={form.vacation_days} onChange={(e) => update({ vacation_days: e.target.value })} />
      </label>
    </fieldset>
  );
}
