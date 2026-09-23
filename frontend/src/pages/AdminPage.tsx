import { useState } from "react";

import { BarList, DailyBars } from "../components/Charts";
import { Card, PageHeader, td, th } from "../components/Layout";
import { ErrorState, LoadingState } from "../components/States";
import { Badge, StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate, formatDateTime } from "../services/format";
import type { ExperienceLevel, User } from "../types/api";

const a = he.admin;
const control =
  "rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";

function Tile({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${warn && value > 0 ? "text-rose-700" : "text-slate-900"}`}>
        {value.toLocaleString("he-IL")}
      </p>
    </div>
  );
}

function NewUserForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({ email: "", display_name: "", password: "", is_admin: false,
    experience_level: "junior" as ExperienceLevel });
  const [error, setError] = useState<string>();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(undefined);
    try {
      await api.adminCreateUser(form);
      setForm({ ...form, email: "", display_name: "", password: "" });
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-2 border-t border-slate-100 p-4">
      <input className={`${control} ltr text-start`} type="email" placeholder={he.auth.email} required value={form.email}
             onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <input className={control} placeholder={he.myArea.displayName} required value={form.display_name}
             onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
      <input className={`${control} ltr text-start`} type="password" placeholder={he.myArea.newPassword} minLength={10} required
             value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" />
      <select className={control} value={form.experience_level}
              onChange={(e) => setForm({ ...form, experience_level: e.target.value as ExperienceLevel })}>
        {Object.entries(he.myArea.levels).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
      </select>
      <label className="flex items-center gap-1.5 text-sm text-slate-700">
        <input type="checkbox" checked={form.is_admin} onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} />
        {a.isAdmin}
      </label>
      <button className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700">{a.create}</button>
      {error && <p role="alert" className="w-full text-sm text-rose-700">{error}</p>}
    </form>
  );
}

function UsersCard() {
  const me = useUser();
  const users = useApi(api.adminUsers, "admin-users");
  const [error, setError] = useState<string>();

  async function update(u: User, change: { is_active?: boolean; new_password?: string }) {
    setError(undefined);
    try {
      await api.adminUpdateUser(u.id, change);
      users.reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function resetPassword(u: User) {
    const password = window.prompt(a.newPasswordPrompt);
    if (password) update(u, { new_password: password });
  }

  const action = "rounded px-2 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50";
  return (
    <Card title={`${a.users}${users.data ? ` (${users.data.length})` : ""}`} flush>
      {users.error ? <div className="p-4"><ErrorState error={users.error} onRetry={users.reload} /></div>
        : !users.data ? <LoadingState />
        : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  {[he.myArea.displayName, he.auth.email, he.myArea.level, a.lastLogin, ""].map((h, i) => <th key={i} className={th}>{h}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.data.map((u) => (
                  <tr key={u.id} className={u.is_active ? "" : "text-slate-400"}>
                    <td className={td}>
                      <span className="font-medium">{u.display_name}</span>
                      <span className="ms-2 inline-flex gap-1">
                        {u.is_admin && <Badge tone="violet">{a.isAdmin}</Badge>}
                        {!u.is_active && <Badge tone="slate">{he.sources.disabled}</Badge>}
                      </span>
                    </td>
                    <td className={td}><span className="ltr">{u.email}</span></td>
                    <td className={td}>{he.myArea.levels[u.experience_level]}</td>
                    <td className={`${td} whitespace-nowrap`}>{formatDateTime(u.last_login_at)}</td>
                    <td className={`${td} whitespace-nowrap`}>
                      {u.id !== me.id && (
                        <span className="flex gap-1">
                          <button className={action} onClick={() => update(u, { is_active: !u.is_active })}>
                            {u.is_active ? a.deactivate : a.activate}
                          </button>
                          <button className={action} onClick={() => resetPassword(u)}>{a.resetPassword}</button>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      {error && <p role="alert" className="px-4 pt-3 text-sm text-rose-700">{error}</p>}
      <NewUserForm onCreated={users.reload} />
    </Card>
  );
}

export function AdminPage() {
  const stats = useApi(api.adminStats, "admin-stats");
  const s = stats.data;

  return (
    <>
      <PageHeader title={a.title} subtitle={a.subtitle} />
      {stats.error && <ErrorState error={stats.error} onRetry={stats.reload} />}
      {!s ? (!stats.error && <LoadingState rows={8} />) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Tile label={a.cards.users} value={s.users_total} />
            <Tile label={a.cards.active7d} value={s.users_active_7d} />
            <Tile label={a.cards.logins7d} value={s.logins_7d} />
            <Tile label={a.cards.failed7d} value={s.failed_logins_7d} warn />
            <Tile label={a.cards.views7d} value={s.page_views_7d} />
            <Tile label={a.cards.alerts7d} value={s.alerts_sent_7d} />
            <Tile label={a.cards.outreach7d} value={s.outreach_sent_7d} />
            <Tile label={a.cards.tenders} value={s.government_tenders_active} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="min-w-0 lg:col-span-2">
              <Card title={a.dailyViews}><DailyBars days={s.daily} /></Card>
            </div>
            <Card title={a.topPages}><BarList items={s.top_pages} /></Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title={a.bySource}><BarList items={s.jobs_by_source} /></Card>
            <Card title={a.byRole}><BarList items={s.jobs_by_role} label={(r) => he.roles[r] ?? r} /></Card>
          </div>

          <Card title={he.runs.title} flush>
            <ul className="divide-y divide-slate-100">
              {s.recent_runs.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-3 px-4 py-2 text-sm">
                  <StatusBadge status={r.status} />
                  <span>{formatDate(r.scheduled_date)}</span>
                  <span className="ltr tabular-nums text-slate-500">{r.sites_succeeded}/{r.sites_total}</span>
                  <span className="text-slate-500">{r.raw_jobs_found.toLocaleString("he-IL")} · {r.eligible_jobs}</span>
                </li>
              ))}
            </ul>
          </Card>

          <UsersCard />
        </div>
      )}
    </>
  );
}
