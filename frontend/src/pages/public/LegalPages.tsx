import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { api } from "../../services/api";

function Document({ title, updated, sections }: {
  title: string; updated: string; sections: { heading: string; body: string[] }[];
}) {
  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{updated}</p>
      {sections.map((section) => (
        <section key={section.heading} className="mt-8">
          <h2 className="text-lg font-semibold">{section.heading}</h2>
          {section.body.map((paragraph) => (
            <p key={paragraph} className="mt-2 leading-7 text-slate-700">{paragraph}</p>
          ))}
        </section>
      ))}
    </article>
  );
}

export function PrivacyPage() {
  const config = useApi(api.authConfig, "auth-config");
  const contact = config.data?.contact_email;
  const p = he.site.privacyDoc;
  const sections = [...p.sections, {
    heading: p.contactHeading,
    body: [contact ? p.contactWith(contact) : p.contactWithout],
  }];
  return <Document title={p.title} updated={p.updated} sections={sections} />;
}

export function TermsPage() {
  const t = he.site.termsDoc;
  return <Document title={t.title} updated={t.updated} sections={t.sections} />;
}
