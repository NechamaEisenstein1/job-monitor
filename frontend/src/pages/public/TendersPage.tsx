import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { he } from "../../i18n/he";

const t = he.site.tenders;

/** Public landing page for government software tenders - the page search engines should rank for them. */
export function TendersPage() {
  const { user } = useAuth();

  return (
    <article className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
      <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{t.title}</h1>
      <p className="mt-4 text-lg text-slate-600">{t.lead}</p>

      <section className="mt-10">
        <h2 className="text-xl font-semibold">{t.fieldsTitle}</h2>
        <ul className="mt-4 flex flex-wrap gap-2 text-sm">
          {t.fields.map((f) => (
            <li key={f} className="rounded-full bg-amber-50 px-3 py-1 text-amber-900 ring-1 ring-amber-200">{f}</li>
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-semibold">{t.howTitle}</h2>
        <ol className="mt-4 list-decimal space-y-2 ps-5 text-slate-700">
          {t.how.map((step) => <li key={step}>{step}</li>)}
        </ol>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-semibold">{t.faqTitle}</h2>
        <dl className="mt-4 space-y-5">
          {t.faq.map(({ q, a }) => (
            <div key={q}>
              <dt className="font-semibold text-slate-900">{q}</dt>
              <dd className="mt-1 leading-7 text-slate-600">{a}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="mt-12">
        <Link to={user ? "/jobs" : "/login?mode=register"}
              className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700">
          {user ? t.ctaLoggedIn : t.cta}
        </Link>
      </div>
    </article>
  );
}
