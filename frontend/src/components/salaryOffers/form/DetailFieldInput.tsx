import { offerTerms } from "../../../i18n/salaryOffers/terms";
import type { DetailField } from "../detailSections";
import { formLabel, tallControl } from "./formStyles";
import type { OfferFormControls } from "./useOfferForm";

/** One optional detail, drawn by its kind: a number box, a checkbox or a short list. */
export function DetailFieldInput({ field, controls }: { field: DetailField; controls: OfferFormControls }) {
  const label = offerTerms.details[field.key];
  const value = controls.form.details[field.key];
  const set = (next: string | boolean) => controls.updateDetail(field.key, next);

  if (field.input === "flag") {
    return (
      <label className="flex min-h-11 items-center gap-2 text-sm text-slate-800">
        <input type="checkbox" className="size-4" checked={value === true} onChange={(e) => set(e.target.checked)} />
        {label}
      </label>
    );
  }
  return (
    <label className={`${formLabel} font-medium`}>
      {label}
      {field.input === "number" ? (
        <input type="number" min={0} step={field.step} inputMode="decimal" dir="ltr" placeholder={offerTerms.notStated}
               className={`${tallControl} text-start`} value={typeof value === "string" ? value : ""}
               onChange={(e) => set(e.target.value)} />
      ) : (
        <select className={tallControl} value={typeof value === "string" ? value : ""} onChange={(e) => set(e.target.value)}>
          <option value="">{offerTerms.notStated}</option>
          {field.choices.map((choice) => <option key={choice} value={choice}>{offerTerms.detailChoices[choice]}</option>)}
        </select>
      )}
    </label>
  );
}
