import { he } from "../../../i18n/he";
import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import { offerTerms } from "../../../i18n/salaryOffers/terms";
import type { SalaryOfferOptions } from "../../../types/salaryOffers";
import { SegmentedChoice } from "../ChoiceChips";
import { LEVEL_CHOICES } from "../OfferQueryFilters";
import { formLabel, formSection, formSectionTitle, tallControl } from "./formStyles";
import type { OfferFormControls } from "./useOfferForm";

const t = salaryOfferPages.form;
const AGENCY_SUGGESTIONS_ID = "salary-offer-agencies";

export function OfferBasicsFields({ controls, options }: { controls: OfferFormControls; options: SalaryOfferOptions }) {
  const { form, update } = controls;
  return (
    <fieldset className={formSection}>
      <legend className={`${formSectionTitle} mb-4`}>{t.offerSection}</legend>
      <SegmentedChoice label={t.level} choices={LEVEL_CHOICES} selected={form.level} onSelect={(level) => update({ level })} />
      <div className="grid gap-3 sm:grid-cols-3">
        <label className={formLabel}>
          {t.role}
          <select required className={tallControl} value={form.role_type} onChange={(e) => update({ role_type: e.target.value })}>
            <option value="" disabled>{t.chooseRole}</option>
            {options.role_types.map((role) => <option key={role} value={role}>{he.roles[role] ?? role}</option>)}
          </select>
        </label>
        <label className={formLabel}>
          {t.agency}
          <input required className={tallControl} list={AGENCY_SUGGESTIONS_ID} maxLength={80} dir="auto"
                 value={form.agency} onChange={(e) => update({ agency: e.target.value })} />
          <datalist id={AGENCY_SUGGESTIONS_ID}>
            {options.agencies.map((agency) => <option key={agency} value={agency} />)}
          </datalist>
        </label>
        <label className={formLabel}>
          {t.client}
          <select className={tallControl} value={form.client_type}
                  onChange={(e) => update({ client_type: e.target.value as typeof form.client_type })}>
            {Object.entries(offerTerms.clientType).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={formLabel}>
          {t.month}
          <input required type="month" className={tallControl} value={form.offered_month}
                 onChange={(e) => update({ offered_month: e.target.value })} />
        </label>
        <label className={formLabel}>
          {t.outcome}
          <select className={tallControl} value={form.outcome}
                  onChange={(e) => update({ outcome: e.target.value as typeof form.outcome })}>
            {Object.entries(offerTerms.outcome).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>
    </fieldset>
  );
}
