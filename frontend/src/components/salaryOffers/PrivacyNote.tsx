import { salaryOfferPages } from "../../i18n/salaryOffers/pages";

const t = salaryOfferPages.privacy;

export function PrivacyNote() {
  return (
    <section className="rounded-xl border border-brand-200 bg-brand-50 p-4 text-brand-900">
      <h2 className="font-bold">{t.title}</h2>
      <ul className="mt-2 list-disc space-y-1 ps-5 text-sm">
        {t.items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}
