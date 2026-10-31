import { useState } from "react";

import type { ExtraKind } from "../../../types/salaryOffers";
import type { ExtraDraft, OfferFormState } from "./offerFormState";

export interface OfferFormControls {
  form: OfferFormState;
  update: (change: Partial<OfferFormState>) => void;
  updateDetail: (key: string, value: string | boolean) => void;
  addExtra: (kind: ExtraKind) => void;
  updateExtra: (index: number, change: Partial<ExtraDraft>) => void;
  removeExtra: (index: number) => void;
}

export function useOfferForm(initial: () => OfferFormState): OfferFormControls {
  const [form, setForm] = useState(initial);
  const update = (change: Partial<OfferFormState>) => setForm((current) => ({ ...current, ...change }));
  const replaceExtras = (edit: (extras: ExtraDraft[]) => ExtraDraft[]) =>
    setForm((current) => ({ ...current, extras: edit(current.extras) }));

  return {
    form,
    update,
    updateDetail: (key, value) => setForm((current) => ({ ...current, details: { ...current.details, [key]: value } })),
    addExtra: (kind) => replaceExtras((extras) => [...extras, { kind, amount: "", included_in_total: true }]),
    updateExtra: (index, change) =>
      replaceExtras((extras) => extras.map((extra, i) => (i === index ? { ...extra, ...change } : extra))),
    removeExtra: (index) => replaceExtras((extras) => extras.filter((_, i) => i !== index)),
  };
}
