import type { ChangeType, JobStatus, RunStatus, ScrapeStatus } from "../types/api";
import { he } from "../i18n/he";

type Tone = "green" | "amber" | "red" | "slate" | "blue" | "violet";

const TONES: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/20",
  red: "bg-rose-50 text-rose-700 ring-rose-600/20",
  slate: "bg-slate-100 text-slate-600 ring-slate-500/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  violet: "bg-violet-50 text-violet-700 ring-violet-600/20",
};

// Maps backend status values to a color. Display only.
const STATUS_TONE: Record<JobStatus | RunStatus | ScrapeStatus | ChangeType, Tone> = {
  active: "green",
  not_seen_recently: "amber",
  archived: "slate",
  success: "green",
  partial: "amber",
  failed: "red",
  timeout: "red",
  network_error: "red",
  parse_error: "red",
  config_error: "red",
  zero_results: "amber",
  new: "blue",
  content_updated: "violet",
  new_source: "green",
  source_url_updated: "slate",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: keyof typeof STATUS_TONE | null | undefined }) {
  if (!status) return <Badge tone="slate">{he.sources.neverRun}</Badge>;
  return <Badge tone={STATUS_TONE[status] ?? "slate"}>{he.status[status] ?? status}</Badge>;
}

export function EligibilityBadge({ eligible }: { eligible: boolean | null | undefined }) {
  if (eligible == null) return <Badge tone="slate">{he.eligibility.notEvaluated}</Badge>;
  return eligible
    ? <Badge tone="green">{he.eligibility.eligible}</Badge>
    : <Badge tone="slate">{he.eligibility.notEligible}</Badge>;
}

/** Government tender: the one badge meant to catch the eye (filled, with an icon). */
export function TenderBadge() {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-md bg-amber-400 px-2 py-0.5 text-xs font-semibold text-amber-950">
      <span aria-hidden>🏛</span>{he.tender}
    </span>
  );
}

export function RoleBadge({ role }: { role: string | null | undefined }) {
  if (!role) return null;
  return <Badge tone={role === "software" ? "blue" : "slate"}>{he.roles[role] ?? role}</Badge>;
}

export function JuniorBadge() {
  return <Badge tone="green">{he.junior}</Badge>;
}
