import { useState } from "react";

import { useAuth } from "../hooks/useAuth";
import { he } from "../i18n/he";

const control =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-sm font-semibold text-slate-500">{he.appName}</p>
          <h1 className="mt-1 text-xl font-semibold">{he.auth.title}</h1>
          <p className="mt-1 text-sm text-slate-500">{he.auth.subtitle}</p>
        </div>
        <label className="block space-y-1 text-sm font-medium text-slate-700">
          <span>{he.auth.email}</span>
          <input className={`${control} ltr text-start`} type="email" autoComplete="username" required
                 value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block space-y-1 text-sm font-medium text-slate-700">
          <span>{he.auth.password}</span>
          <input className={`${control} ltr text-start`} type="password" autoComplete="current-password" required
                 value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
        <button type="submit" disabled={busy}
                className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60">
          {busy ? he.auth.submitting : he.auth.submit}
        </button>
        <p className="text-center text-xs text-slate-500">{he.auth.noSignup}</p>
      </form>
    </div>
  );
}
