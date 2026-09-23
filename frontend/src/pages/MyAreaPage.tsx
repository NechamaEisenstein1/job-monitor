import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, PageHeader } from "../components/Layout";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { JuniorBadge, RoleBadge, TenderBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { useAuth, useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api, PAGE_SIZE } from "../services/api";
import type { ExperienceLevel, JobListItem, OutreachResult, Recruiter, RecruiterInput } from "../types/api";

const m = he.myArea;
const control =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const primary = "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const secondary = "rounded-md px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
      {label}
      {children}
    </label>
  );
}

function Message({ error, ok }: { error?: string; ok?: string }) {
  if (error) return <p role="alert" className="text-sm text-rose-700">{error}</p>;
  if (ok) return <p role="status" className="text-sm text-emerald-700">{ok}</p>;
  return null;
}

// ------------------------------------------------------------------ profile

function ProfileCard() {
  const user = useUser();
  const { setUser } = useAuth();
  const [name, setName] = useState(user.display_name);
  const [level, setLevel] = useState<ExperienceLevel>(user.experience_level);
  const [alerts, setAlerts] = useState(user.alerts_enabled);
  const [status, setStatus] = useState<{ error?: string; ok?: string }>({});
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [pwStatus, setPwStatus] = useState<{ error?: string; ok?: string }>({});

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      setUser(await api.updateProfile({ display_name: name, experience_level: level, alerts_enabled: alerts }));
      setStatus({ ok: m.saved });
    } catch (err) {
      setStatus({ error: (err as Error).message });
    }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.changePassword(current, next);
      setCurrent("");
      setNext("");
      setPwStatus({ ok: m.passwordChanged });
    } catch (err) {
      setPwStatus({ error: (err as Error).message });
    }
  }

  return (
    <Card title={m.profile}>
      <form onSubmit={save} className="space-y-3">
        <p className="ltr text-start text-sm text-slate-500">{user.email}</p>
        <Field label={m.displayName}>
          <input className={control} value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label={m.level}>
          <select className={control} value={level} onChange={(e) => setLevel(e.target.value as ExperienceLevel)}>
            {Object.entries(m.levels).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" className="size-4" checked={alerts} onChange={(e) => setAlerts(e.target.checked)} />
          {m.alerts}
        </label>
        <div className="flex items-center gap-3">
          <button className={primary}>{m.save}</button>
          <Message {...status} />
        </div>
      </form>
      <details className="mt-4 border-t border-slate-100 pt-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">{m.password}</summary>
        <form onSubmit={changePassword} className="mt-3 space-y-3">
          <Field label={m.currentPassword}>
            <input className={control} type="password" autoComplete="current-password" value={current}
                   onChange={(e) => setCurrent(e.target.value)} required />
          </Field>
          <Field label={m.newPassword}>
            <input className={control} type="password" autoComplete="new-password" minLength={10} value={next}
                   onChange={(e) => setNext(e.target.value)} required />
          </Field>
          <div className="flex items-center gap-3">
            <button className={secondary}>{m.changePassword}</button>
            <Message {...pwStatus} />
          </div>
        </form>
      </details>
    </Card>
  );
}

// ------------------------------------------------------------------ recruiters

const EMPTY: RecruiterInput = { name: "", email: "", company: "" };

function RecruiterForm({ initial, submitLabel, onSubmit, onCancel }: {
  initial: RecruiterInput; submitLabel: string;
  onSubmit: (r: RecruiterInput) => Promise<void>; onCancel?: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState<string>();
  const set = (k: keyof RecruiterInput) => (e: React.ChangeEvent<HTMLInputElement>) => setValue({ ...value, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(undefined);
    try {
      await onSubmit(value);
      if (!onCancel) setValue(EMPTY);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
      <Field label={m.recruiterName}><input className={control} value={value.name} onChange={set("name")} required /></Field>
      <Field label={m.recruiterEmail}>
        <input className={`${control} ltr text-start`} type="email" value={value.email} onChange={set("email")} required />
      </Field>
      <Field label={m.recruiterCompany}><input className={control} value={value.company} onChange={set("company")} required /></Field>
      <div className="flex gap-2">
        <button className={primary}>{submitLabel}</button>
        {onCancel && <button type="button" className={secondary} onClick={onCancel}>{m.cancel}</button>}
      </div>
      {error && <p role="alert" className="text-sm text-rose-700 sm:col-span-4">{error}</p>}
    </form>
  );
}

function RecruitersCard({ recruiters, reload }: { recruiters: Recruiter[]; reload: () => void }) {
  const [editing, setEditing] = useState<number | null>(null);

  async function remove(r: Recruiter) {
    if (!window.confirm(m.confirmRemove(r.name))) return;
    await api.deleteRecruiter(r.id);
    reload();
  }

  return (
    <Card title={`${m.recruiters} (${recruiters.length})`}>
      <p className="mb-3 text-xs text-slate-500">{m.recruitersHint}</p>
      {recruiters.length === 0 ? (
        <p className="mb-4 text-sm text-slate-500">{m.noRecruiters}</p>
      ) : (
        <ul className="mb-4 divide-y divide-slate-100">
          {recruiters.map((r) => (
            <li key={r.id} className="py-2">
              {editing === r.id ? (
                <RecruiterForm initial={r} submitLabel={m.save} onCancel={() => setEditing(null)}
                               onSubmit={async (v) => { await api.updateRecruiter(r.id, v); setEditing(null); reload(); }} />
              ) : (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  <span className="font-medium text-slate-900">{r.name}</span>
                  <span className="text-slate-500">{r.company}</span>
                  <span className="ltr text-xs text-slate-400">{r.email}</span>
                  <span className="ms-auto flex gap-1">
                    <button className="rounded px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100" onClick={() => setEditing(r.id)}>{m.edit}</button>
                    <button className="rounded px-2 py-0.5 text-xs text-rose-700 hover:bg-rose-50" onClick={() => remove(r)}>{m.remove}</button>
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <RecruiterForm initial={EMPTY} submitLabel={m.add} onSubmit={async (v) => { await api.addRecruiter(v); reload(); }} />
    </Card>
  );
}

// ------------------------------------------------------------------ matches + outreach

function OutreachButton({ job, recruiterCount }: { job: JobListItem; recruiterCount: number }) {
  const [stage, setStage] = useState<"idle" | "confirm" | "sending" | "done">("idle");
  const [results, setResults] = useState<OutreachResult[]>([]);
  const [error, setError] = useState<string>();

  async function send() {
    setStage("sending");
    setError(undefined);
    try {
      setResults(await api.sendOutreach(job.id));
      setStage("done");
    } catch (err) {
      setError((err as Error).message);
      setStage("idle");
    }
  }

  if (stage === "done") {
    return (
      <ul className="flex flex-wrap gap-1.5 text-xs">
        {results.map((r) => (
          <li key={r.recruiter_id}
              className={`rounded px-1.5 py-0.5 ${r.status === "sent" ? "bg-emerald-50 text-emerald-800" : r.status === "failed" ? "bg-rose-50 text-rose-800" : "bg-slate-100 text-slate-600"}`}>
            {r.recruiter_name}: {m.outreachStatus[r.status]}{r.detail && m.outreachDetail[r.detail] ? ` (${m.outreachDetail[r.detail]})` : ""}
          </li>
        ))}
      </ul>
    );
  }
  if (stage === "confirm" || stage === "sending") {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
        <span>{m.confirmAsk(recruiterCount)}</span>
        <button className={primary} onClick={send} disabled={stage === "sending"}>{stage === "sending" ? m.sending : m.send}</button>
        <button className={secondary} onClick={() => setStage("idle")} disabled={stage === "sending"}>{m.cancel}</button>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button className={secondary} disabled={recruiterCount === 0} onClick={() => setStage("confirm")}
              title={recruiterCount === 0 ? he.errors.no_recruiters : undefined}>
        ✉ {m.askRecruiters}
      </button>
      {error && <span role="alert" className="text-sm text-rose-700">{error}</span>}
    </div>
  );
}

function MatchesCard({ recruiterCount }: { recruiterCount: number }) {
  const [page, setPage] = useState(1);
  const [tendersOnly, setTendersOnly] = useState(false);
  const matches = useApi(() => api.matches(page, tendersOnly || undefined), `matches-${page}-${tendersOnly}`);

  return (
    <Card title={m.matches} flush actions={
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" className="size-4 accent-amber-500" checked={tendersOnly}
               onChange={(e) => { setTendersOnly(e.target.checked); setPage(1); }} />
        {m.tendersOnly}
      </label>
    }>
      <p className="px-4 pt-3 text-xs text-slate-500">{m.matchesHint}</p>
      {matches.error ? <div className="p-4"><ErrorState error={matches.error} onRetry={matches.reload} /></div>
        : !matches.data ? <LoadingState rows={5} />
        : !matches.data.items.length ? <EmptyState title={m.noMatches} />
        : (
          <>
            <ul className="divide-y divide-slate-100">
              {matches.data.items.map((job) => (
                <li key={job.id} className={`space-y-2 px-4 py-3 ${job.is_government_tender ? "border-s-4 border-amber-400 bg-amber-50/40" : ""}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/jobs/${job.id}`} className="font-medium text-slate-900 hover:underline" dir="auto">{job.title}</Link>
                    {job.is_government_tender && <TenderBadge />}
                    {job.is_junior && <JuniorBadge />}
                    <RoleBadge role={job.role_type} />
                  </div>
                  <div className="flex flex-wrap gap-x-3 text-xs text-slate-500">
                    <span dir="auto">{job.location ?? he.common.none}</span>
                    <span>{job.recruitment_companies.join(", ")}</span>
                    {job.known_recruiters.length > 0 && (
                      <span className="font-medium text-emerald-700">{m.knownRecruiters(job.known_recruiters.join(", "))}</span>
                    )}
                  </div>
                  <OutreachButton job={job} recruiterCount={recruiterCount} />
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={PAGE_SIZE} total={matches.data.total} onPage={setPage} />
          </>
        )}
    </Card>
  );
}

export function MyAreaPage() {
  const recruiters = useApi(api.recruiters, "recruiters");
  return (
    <>
      <PageHeader title={m.title} subtitle={m.subtitle} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <MatchesCard recruiterCount={recruiters.data?.length ?? 0} />
        </div>
        <div className="min-w-0 space-y-6">
          <ProfileCard />
          {recruiters.error ? <ErrorState error={recruiters.error} onRetry={recruiters.reload} />
            : recruiters.data ? <RecruitersCard recruiters={recruiters.data} reload={recruiters.reload} />
            : <LoadingState />}
        </div>
      </div>
    </>
  );
}
