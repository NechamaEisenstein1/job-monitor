import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, PageHeader, td, th } from "../components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Badge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate } from "../services/format";
import type { ManualJob, ManualJobInput } from "../types/api";

const r = he.recruiter;
const control =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const EMPTY: ManualJobInput = { title: "", description: "", requirements: "", tender_number: "", government_ministry: "", location: "" };

function Field({ label, optional, children }: { label: string; optional?: boolean; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">
        {label} {optional && <span className="font-normal text-slate-400">{r.optional}</span>}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function PublishForm({ onPublished }: { onPublished: () => void }) {
  const prices = useApi(api.billingPrices, "billing-prices");
  const [form, setForm] = useState<ManualJobInput>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string }>();
  const set = (key: keyof ManualJobInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(undefined);
    try {
      const result = await api.publishJob(form);
      setForm(EMPTY);
      setMessage({ ok: true, text: r.published(result.points_awarded, result.balance) });
      onPublished();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={r.form}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={r.tenderNumber} optional>
            <input className={`${control} ltr text-start`} value={form.tender_number} onChange={set("tender_number")} maxLength={100} />
          </Field>
          <Field label={r.ministry} optional>
            <input className={control} value={form.government_ministry} onChange={set("government_ministry")} maxLength={200} />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={r.jobTitle}>
            <input className={control} required value={form.title} onChange={set("title")} maxLength={500} />
          </Field>
          <Field label={r.location} optional>
            <input className={control} value={form.location} onChange={set("location")} maxLength={200} />
          </Field>
        </div>
        <Field label={r.description}>
          <textarea className={`${control} min-h-28`} required value={form.description} onChange={set("description")} maxLength={20000} />
        </Field>
        <Field label={r.requirements} optional>
          <textarea className={`${control} min-h-20`} value={form.requirements} onChange={set("requirements")} maxLength={20000} />
        </Field>
        <div className="flex flex-wrap items-center gap-3">
          <button disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60">
            {busy ? r.publishing : r.publish}
          </button>
          {prices.data && (
            <span className="text-xs text-slate-500">
              {r.earnHint(prices.data.points_per_manual_job, prices.data.max_awarded_posts_per_day)}
            </span>
          )}
        </div>
        {message && (
          <p role={message.ok ? "status" : "alert"} className={`text-sm ${message.ok ? "text-emerald-700" : "text-rose-700"}`}>
            {message.text}
          </p>
        )}
      </form>
    </Card>
  );
}

function PostingsCard({ all }: { all: boolean }) {
  const postings = useApi(() => api.myPostings(all), `postings-${all}`);
  const prices = useApi(api.billingPrices, "billing-prices");
  const [message, setMessage] = useState<{ ok: boolean; text: string }>();

  async function act(run: () => Promise<string | undefined>) {
    setMessage(undefined);
    try {
      const text = await run();
      if (text) setMessage({ ok: true, text });
      postings.reload();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    }
  }

  const remove = (job: ManualJob) => act(async () => {
    if (!window.confirm(r.confirmRemove)) return undefined;
    return r.removed((await api.removeJob(job.id)).points_reversed);
  });
  const feature = (job: ManualJob) => act(async () => { await api.featureJob(job.id); return undefined; });

  const action = "rounded px-2 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50";
  const now = Date.now();
  return (
    <Card title={all ? r.all : r.mine} flush>
      {postings.error ? <div className="p-4"><ErrorState error={postings.error} onRetry={postings.reload} /></div>
        : !postings.data ? <LoadingState />
        : !postings.data.length ? <EmptyState title={r.none} />
        : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>{[r.jobTitle, r.tenderNumber, r.ministry, he.jobs.columns.updated, ""].map((h, i) => <th key={i} className={th}>{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {postings.data.map((job) => {
                  const featured = job.featured_until && Date.parse(job.featured_until) > now;
                  return (
                    <tr key={job.id}>
                      <td className={td}>
                        <Link to={`/jobs/${job.id}`} className="font-medium text-slate-900 hover:text-sky-700 hover:underline" dir="auto">{job.title}</Link>
                        {featured && (
                          <div className="mt-1"><Badge tone="violet">★ {r.featuredUntil} {formatDate(job.featured_until)}</Badge></div>
                        )}
                      </td>
                      <td className={td}><span className="ltr">{job.tender_number ?? he.common.none}</span></td>
                      <td className={td} dir="auto">{job.government_ministry ?? he.common.none}</td>
                      <td className={`${td} whitespace-nowrap`}>{formatDate(job.created_at)}</td>
                      <td className={`${td} whitespace-nowrap`}>
                        <span className="flex gap-1">
                          {prices.data && (
                            <button className={action} onClick={() => feature(job)}>
                              {r.feature(prices.data.featured_job_points, prices.data.featured_job_days)}
                            </button>
                          )}
                          <button className={`${action} text-rose-700`} onClick={() => remove(job)}>{r.remove}</button>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={`px-4 py-3 text-sm ${message.ok ? "text-emerald-700" : "text-rose-700"}`}>
          {message.text}
        </p>
      )}
    </Card>
  );
}

export function RecruiterPage() {
  const user = useUser();
  const [version, setVersion] = useState(0);
  return (
    <>
      <PageHeader title={r.title} subtitle={r.subtitle}>
        <Link to="/billing" className="text-sm font-medium text-sky-700 hover:underline">{he.nav.billing} ←</Link>
      </PageHeader>
      <div className="space-y-6">
        <PublishForm onPublished={() => setVersion(version + 1)} />
        <PostingsCard key={`mine-${version}`} all={false} />
        {user.is_admin && <PostingsCard key={`all-${version}`} all />}
      </div>
    </>
  );
}
