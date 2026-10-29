import { Star } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { pointsGoal } from "../components/celebration/pointsGoal";
import { type PostOutcome, PostCelebration } from "../components/celebration/PostCelebration";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { td, th } from "../components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Badge, Icon } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate } from "../services/format";
import type { JobSubmission, ManualJob, ManualJobInput } from "../types/api";

const r = he.recruiter;
const control =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const EMPTY: ManualJobInput = {
  title: "", description: "", requirements: "", tender_number: "", government_ministry: "", location: "",
  source_recruiter: "", source_published_on: "",
};

/** Today in the user's time zone, as YYYY-MM-DD (the latest allowed tender date). */
function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

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

/** Recruiters publish at once; other users send the posting to the admin for approval
 *  and must say where it came from. */
function PublishForm({ direct, onPublished }: { direct: boolean; onPublished: () => void }) {
  const prices = useApi(api.billingPrices, "billing-prices");
  const subscription = useApi(api.subscription, "subscription");
  const [form, setForm] = useState<ManualJobInput>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [outcome, setOutcome] = useState<PostOutcome>();
  const titleRef = useRef<HTMLInputElement>(null);
  const set = (key: keyof ManualJobInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      if (direct) {
        const result = await api.publishJob(form);
        setOutcome({ kind: "published", points: result.points_awarded, balance: result.balance });
      } else {
        await api.submitJob(form);
        setOutcome({ kind: "pending", points: prices.data?.points_per_manual_job ?? 0 });
      }
      setForm(EMPTY);
      onPublished();
    } catch (err) {
      setError((err as Error).message);
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
            <input ref={titleRef} className={control} required value={form.title} onChange={set("title")} maxLength={500} />
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
        <fieldset className="space-y-2 rounded-md border border-slate-200 p-3">
          <legend className="px-1 text-xs font-semibold text-slate-700">{r.source}</legend>
          {!direct && <p className="text-xs text-slate-500">{r.sourceHint}</p>}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={r.sourceRecruiter} optional={direct}>
              <input className={control} required={!direct} value={form.source_recruiter} onChange={set("source_recruiter")} maxLength={200} />
            </Field>
            <Field label={r.sourcePublishedOn} optional={direct}>
              <input type="date" className={control} required={!direct} max={today()} value={form.source_published_on}
                     onChange={set("source_published_on")} />
            </Field>
          </div>
        </fieldset>
        <div className="flex flex-wrap items-center gap-3">
          <button disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60">
            {direct ? (busy ? r.publishing : r.publish) : (busy ? r.sending : r.sendForApproval)}
          </button>
          {prices.data && (
            <span className="text-xs text-slate-500">
              {direct ? r.earnHint(prices.data.points_per_manual_job, prices.data.max_awarded_posts_per_day)
                : r.approvalHint(prices.data.points_per_manual_job)}
            </span>
          )}
        </div>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      </form>
      <PostCelebration outcome={outcome} goal={pointsGoal(subscription.data, prices.data)}
                       onClose={() => setOutcome(undefined)}
                       onPostAnother={() => {
                         setOutcome(undefined);
                         titleRef.current?.focus();
                       }} />
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
                        <Link to={`/jobs/${job.id}`} target="_blank" rel="noopener" className="font-medium text-slate-900 hover:text-sky-700 hover:underline" dir="auto">{job.title}</Link>
                        {featured && (
                          <div className="mt-1"><Badge tone="violet"><Icon icon={Star} />{r.featuredUntil} {formatDate(job.featured_until)}</Badge></div>
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

const SUBMISSION_TONE = { pending: "amber", approved: "green", rejected: "red" } as const;

function SubmissionsCard() {
  const submissions = useApi(api.mySubmissions, "my-submissions");
  return (
    <Card title={r.mySubmissions} flush>
      {submissions.error ? <div className="p-4"><ErrorState error={submissions.error} onRetry={submissions.reload} /></div>
        : !submissions.data ? <LoadingState />
        : !submissions.data.length ? <EmptyState title={r.noSubmissions} />
        : (
          <ul className="divide-y divide-slate-100">
            {submissions.data.map((s: JobSubmission) => (
              <li key={s.id} className="flex flex-wrap items-start justify-between gap-2 px-4 py-3">
                <div className="min-w-0">
                  <p className="font-medium text-slate-900" dir="auto">{s.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {r.sentOn} {formatDate(s.created_at)}
                    {s.tender_number && <> · {r.tenderNumber}: <span className="ltr">{s.tender_number}</span></>}
                  </p>
                  {s.review_note && <p className="mt-1 text-sm text-slate-700" dir="auto">{r.reviewNote}: {s.review_note}</p>}
                </div>
                <span className="flex items-center gap-2">
                  <Badge tone={SUBMISSION_TONE[s.status]}>{r.submissionStatus[s.status]}</Badge>
                  {s.job_id && (
                    <Link to={`/jobs/${s.job_id}`} className="text-xs font-medium text-sky-700 hover:underline">{r.viewJob}</Link>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
    </Card>
  );
}

export function RecruiterPage() {
  const user = useUser();
  const [version, setVersion] = useState(0);
  const direct = user.role !== "user";
  return (
    <>
      <PageHeader title={r.title} subtitle={direct ? r.subtitle : r.subtitleUser}>
        <Link to="/billing" className="text-sm font-medium text-sky-700 hover:underline">{he.nav.billing} ←</Link>
      </PageHeader>
      <div className="space-y-6">
        <PublishForm direct={direct} onPublished={() => setVersion(version + 1)} />
        {!direct && <SubmissionsCard key={`submissions-${version}`} />}
        <PostingsCard key={`mine-${version}`} all={false} />
        {user.is_admin && <PostingsCard key={`all-${version}`} all />}
      </div>
    </>
  );
}
