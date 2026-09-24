import { useParams } from "react-router-dom";

import { ChangeList } from "../components/ChangeList";
import { JobCard } from "../components/JobCard";
import { BackLink, Card, PageHeader } from "../components/Layout";
import { SourceList } from "../components/SourceList";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate, formatDateTime } from "../services/format";
import type { JobDetail } from "../types/api";

function TextBlock({ text }: { text: string }) {
  return text ? (
    <p className="whitespace-pre-line text-sm leading-6 text-slate-700" dir="auto">{text}</p>
  ) : (
    <p className="text-sm text-slate-400">{he.job.notProvided}</p>
  );
}

/** Plain-language version of the listing's honesty labels. */
function TransparencyCard({ job }: { job: JobDetail }) {
  const t = he.signals;
  const sig = job.signals;
  const lines: { tone: string; text: string }[] = [];
  if (job.evaluation?.junior_title_mismatch) lines.push({ tone: "text-rose-700", text: t.fakeJuniorHint });
  if (sig?.is_ghost) lines.push({ tone: "text-amber-800", text: t.ghostHint(sig.days_open, sig.reposts) });
  if (sig && sig.agency_count > 1) lines.push({ tone: "text-sky-800", text: t.agenciesHint(sig.first_agency) });
  if (sig?.is_new) lines.push({ tone: "text-emerald-700", text: t.newHint });
  if (!sig && !lines.length) return null;
  return (
    <Card title={t.title}>
      {sig?.days_open != null && (
        <p className="text-sm font-medium text-slate-800">
          {t.openFor(sig.days_open)} <span className="font-normal text-slate-500">({t.firstSeen}: {formatDate(sig.open_since)})</span>
        </p>
      )}
      <ul className="mt-2 space-y-1.5">
        {lines.map((l) => <li key={l.text} className={`text-sm ${l.tone}`}>{l.text}</li>)}
      </ul>
      <p className="mt-3 text-xs text-slate-400">{t.tracking}</p>
    </Card>
  );
}

export function JobDetailsPage() {
  const id = Number(useParams().id);
  const job = useApi(() => api.job(id), `job-${id}`);
  const sources = useApi(() => api.jobSources(id), `sources-${id}`);
  const history = useApi(() => api.jobHistory(id), `history-${id}`);

  if (job.error) return <ErrorState error={job.error} onRetry={job.reload} />;
  if (!job.data) return <LoadingState rows={10} />;
  const j = job.data;

  return (
    <>
      <BackLink to="/jobs" label={he.job.back} />
      <PageHeader
        title={j.title}
        subtitle={he.job.subtitle(formatDateTime(j.first_seen_at), formatDateTime(j.updated_at), formatDateTime(j.last_seen_at))}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <Card><JobCard job={j} /></Card>
          <Card title={he.job.description}><TextBlock text={j.description} /></Card>
          <Card title={he.job.requirements}><TextBlock text={j.requirements} /></Card>
        </div>
        <div className="min-w-0 space-y-6">
          <TransparencyCard job={j} />
          {!j.is_manual && (
            <Card title={`${he.job.sources}${sources.data ? ` (${sources.data.length})` : ""}`} flush>
              {sources.error ? <div className="p-4"><ErrorState error={sources.error} /></div>
                : sources.data ? <SourceList sources={sources.data} /> : <LoadingState />}
            </Card>
          )}
          <Card title={he.job.history} flush>
            {history.error ? <div className="p-4"><ErrorState error={history.error} /></div>
              : !history.data ? <LoadingState />
              : history.data.length ? <ChangeList changes={history.data} showJob={false} />
              : <EmptyState title={he.job.noHistory} />}
          </Card>
        </div>
      </div>
    </>
  );
}
