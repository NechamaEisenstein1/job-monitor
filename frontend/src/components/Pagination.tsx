import { ChevronLeft, ChevronRight } from "lucide-react";

import { he } from "../i18n/he";
import { Icon } from "./StatusBadge";

export function Pagination({ page, pageSize, total, onPage }: {
  page: number; pageSize: number; total: number; onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(total, page * pageSize);
  const btn = "inline-flex items-center gap-1 rounded-md px-3 py-1 text-sm font-medium ring-1 ring-slate-300 enabled:hover:bg-slate-50 disabled:opacity-40";
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
      <span className="tabular-nums">{he.pagination.range(from, to, total)}</span>
      <div className="flex gap-2">
        <button className={btn} disabled={page <= 1} onClick={() => onPage(page - 1)}><Icon icon={ChevronRight} className="size-4" />{he.pagination.previous}</button>
        <button className={btn} disabled={page >= pages} onClick={() => onPage(page + 1)}>{he.pagination.next}<Icon icon={ChevronLeft} className="size-4" /></button>
      </div>
    </div>
  );
}
