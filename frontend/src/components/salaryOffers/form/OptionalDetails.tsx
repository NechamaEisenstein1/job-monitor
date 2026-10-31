import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import { offerTerms } from "../../../i18n/salaryOffers/terms";
import { Icon } from "../../StatusBadge";
import { DETAIL_SECTIONS, type DetailSection } from "../detailSections";
import { DetailFieldInput } from "./DetailFieldInput";
import { formSectionTitle } from "./formStyles";
import { countFilledDetails } from "./offerFormState";
import type { OfferFormControls } from "./useOfferForm";

const t = salaryOfferPages.form;
const FOLDED_SECTIONS = DETAIL_SECTIONS.filter((section) => section.id !== "sick");

function FoldedSection({ section, open, onToggle, controls }: {
  section: DetailSection; open: boolean; onToggle: () => void; controls: OfferFormControls;
}) {
  const { title, hint } = offerTerms.detailSections[section.id];
  const filled = countFilledDetails(controls.form, section.fields);
  return (
    <div className="rounded-xl border border-slate-200">
      <button type="button" onClick={onToggle} aria-expanded={open}
              className="flex min-h-14 w-full items-center justify-between gap-3 px-4 text-start">
        <span className="flex flex-col">
          <span className="font-bold text-slate-900">{title}</span>
          <span className="text-xs text-slate-600">{hint}</span>
        </span>
        <span className="flex items-center gap-2">
          {filled > 0 && (
            <span className="rounded-full bg-success-100 px-2 py-0.5 text-xs font-bold text-success-800">{t.filledCount(filled)}</span>
          )}
          <Icon icon={ChevronDown} className={`size-5 text-slate-600 transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
      </button>
      {open && (
        <div className="grid gap-3 px-4 pb-4 sm:grid-cols-2">
          {section.fields.map((field) => <DetailFieldInput key={field.key} field={field} controls={controls} />)}
        </div>
      )}
    </div>
  );
}

export function OptionalDetails({ controls }: { controls: OfferFormControls }) {
  const [openSectionId, setOpenSectionId] = useState<string>();
  return (
    <section className="flex flex-col gap-2">
      <h2 className={`${formSectionTitle} mb-2`}>
        {t.moreSection} <span className="text-sm font-medium text-slate-600">· {t.optional}</span>
      </h2>
      {FOLDED_SECTIONS.map((section) => (
        <FoldedSection key={section.id} section={section} controls={controls} open={openSectionId === section.id}
                       onToggle={() => setOpenSectionId(openSectionId === section.id ? undefined : section.id)} />
      ))}
    </section>
  );
}
