import { useState } from "react";

import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { errorLabel, he } from "../i18n/he";
import { api } from "../services/api";
import type { ExperienceLevel } from "../types/api";

const control =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const a = he.auth;

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1 text-sm font-medium text-slate-700">
      <span>{label}</span>
      {children}
      {hint && <span className="block text-xs font-normal text-slate-400">{hint}</span>}
    </label>
  );
}

function GoogleButton() {
  // A plain link: the server runs the OAuth redirect dance and sets the session cookie.
  return (
    <a href="/api/auth/google/start"
       className="flex w-full items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50">
      <svg aria-hidden viewBox="0 0 48 48" className="size-4">
        <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
        <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
        <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
        <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
      </svg>
      {a.google}
    </a>
  );
}

export function LoginPage() {
  const { login, register } = useAuth();
  const config = useApi(api.authConfig, "auth-config");
  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [level, setLevel] = useState<ExperienceLevel>("junior");
  const urlError = new URLSearchParams(window.location.search).get("auth_error");
  const [error, setError] = useState<string | undefined>(urlError ? errorLabel(urlError) : undefined);
  const [busy, setBusy] = useState(false);

  const signupEnabled = config.data?.signup_enabled ?? false;
  const registering = tab === "register" && signupEnabled;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      if (registering) await register({ email, password, display_name: name, experience_level: level });
      else await login(email, password);
      window.history.replaceState(null, "", window.location.pathname); // drop ?auth_error
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const tabClass = (active: boolean) =>
    `flex-1 rounded-md px-3 py-1.5 text-sm font-medium ${active ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800"}`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-8">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-sm font-semibold text-slate-500">{he.appName}</p>
          <h1 className="mt-1 text-xl font-semibold">{registering ? a.registerTitle : a.title}</h1>
          <p className="mt-1 text-sm text-slate-500">{registering ? a.registerSubtitle : a.subtitle}</p>
        </div>

        {signupEnabled && (
          <div className="flex gap-1 rounded-lg bg-slate-100 p-1" role="tablist">
            <button type="button" role="tab" aria-selected={!registering} className={tabClass(!registering)}
                    onClick={() => setTab("login")}>{a.loginTab}</button>
            <button type="button" role="tab" aria-selected={registering} className={tabClass(registering)}
                    onClick={() => setTab("register")}>{a.registerTab}</button>
          </div>
        )}

        {config.data?.google_enabled && (
          <>
            <GoogleButton />
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="h-px flex-1 bg-slate-200" />{a.or}<span className="h-px flex-1 bg-slate-200" />
            </div>
          </>
        )}

        {registering && (
          <Field label={a.displayName}>
            <input className={control} required autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
        )}
        <Field label={a.email}>
          <input className={`${control} ltr text-start`} type="email" autoComplete="username" required
                 value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={a.password} hint={registering ? a.passwordHint : undefined}>
          <input className={`${control} ltr text-start`} type="password" required minLength={registering ? 10 : undefined}
                 autoComplete={registering ? "new-password" : "current-password"}
                 value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {registering && (
          <Field label={a.level}>
            <select className={control} value={level} onChange={(e) => setLevel(e.target.value as ExperienceLevel)}>
              {Object.entries(he.myArea.levels).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </Field>
        )}

        {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
        <button type="submit" disabled={busy}
                className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60">
          {registering ? (busy ? a.registering : a.registerSubmit) : (busy ? a.submitting : a.submit)}
        </button>
        {config.data && !signupEnabled && <p className="text-center text-xs text-slate-500">{a.noSignup}</p>}
      </form>
    </div>
  );
}
