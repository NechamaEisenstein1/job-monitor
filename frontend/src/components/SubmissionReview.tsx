import { useState } from "react";

import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate, formatDateTime } from "../services/format";
import type { JobSubmission } from "../types/api";
import { Card } from "./ui/Card";
import { EmptyState, ErrorState, LoadingState } from "./States";

const rv = he.review;
const r = he.recruiter;

function Fact({ label, value, ltr }: { label: string; value: string | null; ltr?: boolean }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`mt-0.5 text-sm font-medium text-slate-800 ${ltr ? "ltr text-start" : ""}`} dir={ltr ? undefined : "auto"}>{value}</dd>
    </div>
  );
}

function Submission({ s, onReviewed }: { s: JobSubmission; onReviewed: (text: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function act(run: () => Promise<string>) {
    setBusy(true);
    setError(undefined);
    try {
      onReviewed(await run());
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const approve = () => act(async () => rv.approved((await api.adminApproveSubmission(s.id)).points_awarded));
  const reject = () => {
    const note = window.prompt(rv.rejectPrompt);
    if (note === null) return; // cancelled
    void act(async () => { await api.adminRejectSubmission(s.id, note); return rv.rejected; });
  };

  return (
    <li className="space-y-3 px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-slate-900" dir="auto">{s.title}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {rv.sentBy} <span dir="auto">{s.submitter_name ?? he.common.none}</span>
            {s.submitter_email && <> (<span className="ltr">{s.submitter_email}</span>)</>} · {rv.sentOn} {formatDateTime(s.created_at)}
          </p>
        </div>
        <span className="flex gap-2">
          <button disabled={busy} onClick={approve}
                  className="rounded-md bg-emerald-600 px-3 py-1 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60">
            {rv.approve}
          </button>
          <button disabled={busy} onClick={reject}
                  className="rounded-md px-3 py-1 text-sm font-medium text-rose-700 ring-1 ring-rose-200 hover:bg-rose-50 disabled:opacity-60">
            {rv.reject}
          </button>
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-md bg-amber-50/60 p-3 sm:grid-cols-4">
        <Fact label={r.sourceRecruiter} value={s.source_recruiter} />
        <Fact label={r.sourcePublishedOn} value={formatDate(s.source_published_on)} />
        <Fact label={r.tenderNumber} value={s.tender_number} ltr />
        <Fact label={r.ministry} value={s.government_ministry} />
        <Fact label={r.location} value={s.location} />
      </dl>
      <details className="text-sm">
        <summary className="cursor-pointer text-xs font-medium text-sky-700">{rv.showDetails}</summary>
        <div className="mt-2 space-y-2">
          <p className="text-xs font-medium text-slate-500">{r.description}</p>
          <p className="whitespace-pre-line leading-6 text-slate-700" dir="auto">{s.description}</p>
          {s.requirements && <>
            <p className="text-xs font-medium text-slate-500">{r.requirements}</p>
            <p className="whitespace-pre-line leading-6 text-slate-700" dir="auto">{s.requirements}</p>
          </>}
        </div>
      </details>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    </li>
  );
}

/** Admin: postings sent by users without the recruiter role. Only approved ones reach the board. */
export function SubmissionReviewCard() {
  const queue = useApi(api.adminSubmissions, "admin-submissions");
  const [message, setMessage] = useState<string>();
  const count = queue.data?.length;
  return (
    <Card title={count ? `${rv.title} (${count})` : rv.title} flush>
      <p className="px-4 pt-3 text-xs text-slate-500">{rv.hint}</p>
      {message && <p role="status" className="px-4 pt-2 text-sm text-emerald-700">{message}</p>}
      {queue.error ? <div className="p-4"><ErrorState error={queue.error} onRetry={queue.reload} /></div>
        : !queue.data ? <LoadingState />
        : !queue.data.length ? <EmptyState title={rv.none} />
        : (
          <ul className="divide-y divide-slate-100">
            {queue.data.map((s) => (
              <Submission key={s.id} s={s} onReviewed={(text) => { setMessage(text); queue.reload(); }} />
            ))}
          </ul>
        )}
    </Card>
  );
}
