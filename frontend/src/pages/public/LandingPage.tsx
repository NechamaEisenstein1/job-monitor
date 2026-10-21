import { Link } from "react-router-dom";

import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import { isEmbeddedBrowser } from "../../services/browser";

const s = he.site;

export function LandingPage() {
  const config = useApi(api.authConfig, "auth-config");
  // Shown unless the server says Google sign-in is off, so a slow or failed config request doesn't hide it.
  const googleEnabled = config.data?.google_enabled ?? true;

  return (
    <>
      <section className="bg-white">
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
          <p className="text-sm font-semibold text-emerald-700">{s.kicker}</p>
          <h1 className="mt-2 max-w-3xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{s.headline}</h1>
          <p className="mt-4 max-w-2xl text-lg text-slate-600">{s.lead}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {googleEnabled && (
              <a href="/api/auth/google/start"
                 className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700">
                {he.auth.google}
              </a>
            )}
            <Link to="/login?mode=register"
                  className={`rounded-md px-5 py-2.5 text-sm font-medium ${googleEnabled
                    ? "text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50"
                    : "bg-slate-900 text-white hover:bg-slate-700"}`}>
              {s.ctaRegister}
            </Link>
            <Link to="/login" className="rounded-md px-5 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900">
              {s.ctaLogin}
            </Link>
          </div>
          {googleEnabled && isEmbeddedBrowser() && (
            <p className="mt-4 max-w-2xl rounded-md bg-amber-50 p-3 text-sm text-amber-900">{he.auth.embeddedBrowser}</p>
          )}
        </div>
      </section>

      <section className="border-t border-amber-200 bg-amber-50">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
          <h2 className="text-xl font-semibold text-amber-950">{s.tendersTitle}</h2>
          <p className="mt-2 max-w-3xl leading-7 text-amber-900">{s.tendersBody}</p>
          <Link to="/tenders" className="mt-4 inline-block font-medium text-amber-900 underline underline-offset-4 hover:text-amber-950">
            {s.tendersLink}
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
        <h2 className="text-xl font-semibold">{s.featuresTitle}</h2>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {s.features.map((f) => (
            <li key={f.title} className="rounded-lg border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">{f.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
          <h2 className="text-xl font-semibold">{s.sourcesTitle}</h2>
          <p className="mt-2 text-slate-600">{s.sourcesBody}</p>
          <p className="mt-4 flex flex-wrap gap-2 text-sm">
            {s.sources.map((name) => (
              <span key={name} className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">{name}</span>
            ))}
          </p>
        </div>
      </section>
    </>
  );
}
