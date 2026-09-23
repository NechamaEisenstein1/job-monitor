import { useState } from "react";

import { he } from "../i18n/he";
import type { DailyCount, NamedCount } from "../types/api";

// Single-series charts: one hue (no categorical palette needed), text stays in ink colors.
const BAR = "bg-sky-600";

/** Ranked horizontal bars with the value printed next to each - magnitude by category. */
export function BarList({ items, label = (n: string) => n }: { items: NamedCount[]; label?: (name: string) => string }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  if (!items.length) return <p className="text-sm text-slate-400">{he.common.none}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item.name} className="grid grid-cols-[minmax(0,9rem)_1fr_3rem] items-center gap-2 text-sm"
            title={`${label(item.name)}: ${item.count.toLocaleString("he-IL")}`}>
          <span className="truncate text-slate-700" dir="auto">{label(item.name)}</span>
          <span className="h-2.5 overflow-hidden rounded-e-[4px] bg-slate-100" aria-hidden>
            <span className={`block h-full rounded-e-[4px] ${BAR}`} style={{ width: `${(item.count / max) * 100}%` }} />
          </span>
          <span className="text-end tabular-nums text-slate-600">{item.count.toLocaleString("he-IL")}</span>
        </li>
      ))}
    </ul>
  );
}

const shortDay = new Intl.DateTimeFormat("he-IL", { day: "numeric", month: "numeric" });
const longDay = new Intl.DateTimeFormat("he-IL", { weekday: "short", day: "numeric", month: "short" });

/** Page views per day. Time runs left-to-right (axis convention), bars grow from the baseline. */
export function DailyBars({ days }: { days: DailyCount[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...days.map((d) => d.page_views));
  const peak = days.reduce((best, d, i) => (d.page_views > days[best].page_views ? i : best), 0);

  return (
    <figure>
      <div dir="ltr" className="relative flex h-40 items-end gap-[2px] border-b border-slate-200 pt-6"
           onMouseLeave={() => setHover(null)}>
        {days.map((d, i) => {
          const height = d.page_views ? Math.max(3, (d.page_views / max) * 100) : 0;
          return (
            // The hit target is the whole column, wider and taller than the bar itself.
            <div key={d.day} className="relative flex h-full flex-1 items-end justify-center"
                 onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0}
                 aria-label={`${longDay.format(new Date(d.day))}: ${d.page_views}`}>
              <div className={`w-full max-w-7 rounded-t-[4px] ${BAR} ${hover !== null && hover !== i ? "opacity-50" : ""}`}
                   style={{ height: `${height}%` }} />
              {(i === peak && d.page_views > 0) && hover === null && (
                <span className="absolute -top-0 text-xs font-medium tabular-nums text-slate-700">{d.page_views}</span>
              )}
              {hover === i && (
                <div role="tooltip" dir="rtl"
                     className="pointer-events-none absolute -top-2 z-10 -translate-y-full whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow">
                  <div className="font-medium">{longDay.format(new Date(d.day))}</div>
                  <div>{he.admin.views}: {d.page_views} · {he.admin.logins}: {d.logins}
                    {d.failed_logins > 0 && ` · ${he.admin.failed}: ${d.failed_logins}`}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div dir="ltr" className="mt-1 flex gap-[2px] text-[10px] tabular-nums text-slate-400">
        {days.map((d, i) => (
          <span key={d.day} className="flex-1 text-center">{i % 2 === days.length % 2 ? "" : shortDay.format(new Date(d.day))}</span>
        ))}
      </div>
      {/* Table view of the same data for screen readers. */}
      <table className="sr-only">
        <caption>{he.admin.dailyViews}</caption>
        <thead><tr><th>{he.admin.day}</th><th>{he.admin.views}</th><th>{he.admin.logins}</th><th>{he.admin.failed}</th></tr></thead>
        <tbody>
          {days.map((d) => (
            <tr key={d.day}><td>{d.day}</td><td>{d.page_views}</td><td>{d.logins}</td><td>{d.failed_logins}</td></tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
