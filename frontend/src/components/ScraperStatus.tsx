import type { ScraperRun } from "../types/api";
import { he } from "../i18n/he";
import { formatDuration } from "../services/format";
import { StatusBadge } from "./StatusBadge";
import { td, th } from "./Layout";

const s = he.scrapers;

export function ScraperStatus({ scrapers }: { scrapers: ScraperRun[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-100">
        <thead className="bg-slate-50">
          <tr>
            {[s.site, s.status, s.fetched, s.parsed, s.invalid, s.duration, s.notes].map((h) => (
              <th key={h} className={th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {scrapers.map((r) => (
            <tr key={r.id}>
              <td className={`${td} font-medium`}>{r.site}</td>
              <td className={td}><StatusBadge status={r.status} /></td>
              <td className={`${td} tabular-nums`}>{r.jobs_fetched}</td>
              <td className={`${td} tabular-nums`}>{r.jobs_parsed}</td>
              <td className={`${td} tabular-nums ${r.jobs_invalid ? "font-medium text-amber-700" : ""}`}>{r.jobs_invalid}</td>
              <td className={`${td} whitespace-nowrap`}>{formatDuration(r.duration_seconds)}</td>
              <td className={`${td} max-w-md text-xs`}>
                {/* Technical messages come from the backend in English. */}
                {r.error && <p className="ltr text-start text-rose-700">{r.error}</p>}
                {r.warning && <p className="ltr text-start text-amber-700">{r.warning}</p>}
                {!r.error && !r.warning && <span className="text-slate-400">{he.common.none}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
