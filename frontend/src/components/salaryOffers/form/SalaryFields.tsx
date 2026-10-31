import { X } from "lucide-react";

import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import { offerTerms } from "../../../i18n/salaryOffers/terms";
import type { ExtraKind } from "../../../types/salaryOffers";
import { Icon } from "../../StatusBadge";
import { iconButton } from "../../ui/button";
import { SegmentedChoice } from "../ChoiceChips";
import { formatShekels } from "../offerFormat";
import { formLabel, formSection, formSectionTitle, tallControl } from "./formStyles";
import { computedTotalOf } from "./offerFormState";
import type { OfferFormControls } from "./useOfferForm";

const t = salaryOfferPages.form;
const EXTRA_KINDS = Object.keys(offerTerms.extraKind) as ExtraKind[];
const ADD_EXTRA_BUTTON = "min-h-9 rounded-full border border-dashed border-slate-400 bg-white px-3 text-sm text-slate-700 "
  + "hover:border-brand-600 hover:text-brand-700";
const INCLUSION_CHOICES = [{ value: "included", label: t.includedInTotal }, { value: "on_top", label: t.onTop }];

function ExtrasEditor({ controls }: { controls: OfferFormControls }) {
  const { form, addExtra, updateExtra, removeExtra } = controls;
  const unusedKinds = EXTRA_KINDS.filter((kind) => kind === "other" || !form.extras.some((extra) => extra.kind === kind));
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold text-slate-800">{t.extras}</span>
      {form.extras.map((extra, index) => {
        const label = offerTerms.extraKind[extra.kind];
        return (
          <div key={index} className="grid grid-cols-[minmax(0,1fr)_7rem_11rem_2.75rem] items-center gap-2">
            <span>{label}</span>
            <input type="number" min={1} inputMode="numeric" dir="ltr" aria-label={t.extraAmount(label)}
                   className={`${tallControl} text-start`} value={extra.amount}
                   onChange={(e) => updateExtra(index, { amount: e.target.value })} />
            <SegmentedChoice size="sm" label={label} choices={INCLUSION_CHOICES}
                             selected={extra.included_in_total ? "included" : "on_top"}
                             onSelect={(value) => updateExtra(index, { included_in_total: value === "included" })} />
            <button type="button" onClick={() => removeExtra(index)} aria-label={t.removeExtra(label)} className={iconButton("sm")}>
              <Icon icon={X} className="size-4" />
            </button>
          </div>
        );
      })}
      <div className="flex flex-wrap gap-1.5">
        {unusedKinds.map((kind) => (
          <button key={kind} type="button" onClick={() => addExtra(kind)} className={ADD_EXTRA_BUTTON}>
            {t.addExtra(offerTerms.extraKind[kind])}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SalaryFields({ controls }: { controls: OfferFormControls }) {
  const { form, update } = controls;
  return (
    <fieldset className={formSection}>
      <legend className={`${formSectionTitle} mb-4`}>{t.salarySection}</legend>
      <label className={formLabel}>
        {t.baseSalary}
        <input required type="number" min={1} inputMode="numeric" dir="ltr" className={`${tallControl} text-start font-bold`}
               value={form.base_salary} onChange={(e) => update({ base_salary: e.target.value })} />
      </label>
      <ExtrasEditor controls={controls} />
      <div className="flex items-center justify-between rounded-lg bg-brand-50 px-4 py-3 text-brand-900">
        <span className="text-sm">{t.computedTotal}</span>
        <span className="ltr text-xl font-extrabold">{formatShekels(computedTotalOf(form))}</span>
      </div>
    </fieldset>
  );
}
