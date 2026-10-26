import { Link } from "react-router-dom";

import { Reveal, stagger } from "../../components/Motion";
import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { api } from "../../services/api";

const s = he.site;

export function LandingPage() {
  const config = useApi(api.authConfig, "auth-config");

  return (
    <>
      <section className="relative overflow-hidden bg-white">
        {/* Soft color glow behind the hero; decorative only. */}
        <div aria-hidden className="pointer-events-none absolute -top-24 start-1/2 size-[28rem] animate-fade rounded-full bg-emerald-100/60 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-32 -start-16 size-80 animate-fade rounded-full bg-sky-100/60 blur-3xl" />
        <div className="relative mx-auto max-w-5xl px-4 py-16 sm:px-6">
          <p className="animate-enter text-sm font-semibold text-emerald-700">{s.kicker}</p>
          <h1 className="mt-2 max-w-3xl animate-enter text-3xl font-bold leading-tight tracking-tight sm:text-4xl" style={stagger(1, 80)}>{s.headline}</h1>
          <p className="mt-4 max-w-2xl animate-enter text-lg text-slate-600" style={stagger(2, 80)}>{s.lead}</p>
          <div className="mt-8 flex animate-enter flex-wrap gap-3" style={stagger(3, 80)}>
            {config.data?.google_enabled && (
              <a href="/api/auth/google/start"
                 className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:-translate-y-0.5 hover:bg-slate-700 hover:shadow-md">
                {he.auth.google}
              </a>
            )}
            <Link to="/login?mode=register"
                  className={`rounded-md px-5 py-2.5 text-sm font-medium hover:-translate-y-0.5 ${config.data?.google_enabled
                    ? "text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50"
                    : "bg-slate-900 text-white shadow-sm hover:bg-slate-700 hover:shadow-md"}`}>
              {s.ctaRegister}
            </Link>
            <Link to="/login" className="rounded-md px-5 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900">
              {s.ctaLogin}
            </Link>
          </div>
        </div>
      </section>

      <section className="border-t border-amber-200 bg-amber-50">
        <Reveal className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
          <h2 className="text-xl font-semibold text-amber-950">{s.tendersTitle}</h2>
          <p className="mt-2 max-w-3xl leading-7 text-amber-900">{s.tendersBody}</p>
          <Link to="/tenders" className="mt-4 inline-block font-medium text-amber-900 underline underline-offset-4 hover:text-amber-950 hover:underline-offset-8">
            {s.tendersLink}
          </Link>
        </Reveal>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
        <h2 className="text-xl font-semibold">{s.featuresTitle}</h2>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {s.features.map((f, i) => (
            <Reveal as="li" key={f.title} delay={(i % 3) * 90}>
              <div className="h-full rounded-lg border border-slate-200 bg-white p-5 transition-[border-color,box-shadow,translate] duration-200 hover:-translate-y-1 hover:border-emerald-200 hover:shadow-lg">
                <h3 className="font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-1.5 text-sm leading-6 text-slate-600">{f.body}</p>
              </div>
            </Reveal>
          ))}
        </ul>
      </section>

      <section className="border-t border-slate-200 bg-white">
        <Reveal className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
          <h2 className="text-xl font-semibold">{s.sourcesTitle}</h2>
          <p className="mt-2 text-slate-600">{s.sourcesBody}</p>
          <p className="mt-4 flex flex-wrap gap-2 text-sm">
            {s.sources.map((name) => (
              <span key={name} className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 transition-colors hover:bg-emerald-50 hover:text-emerald-800">{name}</span>
            ))}
          </p>
        </Reveal>
      </section>
    </>
  );
}
