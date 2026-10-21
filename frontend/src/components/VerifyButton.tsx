import { ShieldCheck } from "lucide-react";

import { useUser } from "../hooks/useAuth";
import type { Verifications } from "../hooks/useVerifications";
import { he } from "../i18n/he";
import type { Reliability } from "../types/api";
import { Badge, Icon } from "./StatusBadge";

const v = he.verify;

/** How reliable a listing is, from users' votes. Nothing for an unconfirmed one. */
export function ReliabilityBadge({ reliability }: { reliability: Reliability }) {
  if (reliability === "none") return null;
  return (
    <Badge tone={reliability === "high" ? "green" : "blue"}>
      <Icon icon={ShieldCheck} />{v.levels[reliability]}
    </Badge>
  );
}

/** "The details are correct" toggle for one job (like a "like"), with the vote count. */
export function VerifyButton({ job, verifications }: {
  job: { id: number; verification_count: number; reliability: Reliability; posted_by: number | null; is_manual: boolean };
  verifications: Verifications;
}) {
  const user = useUser();
  if (!job.is_manual) return null; // only postings uploaded on the site can be verified
  const checked = verifications.verifiedIds.has(job.id);
  const count = verifications.latest[job.id]?.verification_count ?? job.verification_count;
  // Vouching for your own posting proves nothing (the server refuses it too): show the count only.
  if (job.posted_by === user.id) return <span className="whitespace-nowrap text-xs text-slate-500">{v.count(count)}</span>;
  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <button type="button" title={v.hint} aria-pressed={checked}
              onClick={() => verifications.toggle(job.id, !checked)}
              className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                checked ? "bg-emerald-50 text-emerald-700 ring-emerald-600/30" : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50"}`}>
        <Icon icon={ShieldCheck} />{checked ? v.done : v.button}
      </button>
      <span className="whitespace-nowrap text-xs text-slate-500">{v.count(count)}</span>
    </span>
  );
}
