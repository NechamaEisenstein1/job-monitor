// Small building blocks shared by the forum pages.
import { Fragment, useState } from "react";
import { Link } from "react-router-dom";

import { he } from "../../i18n/he";
import { formatRelative } from "../../services/format";
import type { ForumThreadSummary } from "../../types/api";

const f = he.forum;

export const CATEGORY_STYLE: Record<string, { icon: string; tone: string }> = {
  questions: { icon: "❓", tone: "bg-sky-50 ring-sky-200" },
  sharing: { icon: "💡", tone: "bg-amber-50 ring-amber-200" },
  requests: { icon: "🙋", tone: "bg-violet-50 ring-violet-200" },
  offers: { icon: "🤝", tone: "bg-emerald-50 ring-emerald-200" },
  general: { icon: "💬", tone: "bg-slate-50 ring-slate-200" },
};

export const forumControl =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
export const forumPrimary =
  "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
export const forumSecondary =
  "rounded-md px-2.5 py-1 text-sm text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50";

export function CategoryIcon({ code, size = "md" }: { code: string; size?: "sm" | "md" }) {
  const style = CATEGORY_STYLE[code] ?? CATEGORY_STYLE.general;
  const box = size === "sm" ? "h-7 w-7 text-sm" : "h-11 w-11 text-xl";
  return (
    <span aria-hidden className={`inline-flex shrink-0 items-center justify-center rounded-lg ring-1 ${style.tone} ${box}`}>
      {style.icon}
    </span>
  );
}

const AVATAR_TONES = [
  "bg-sky-100 text-sky-800", "bg-emerald-100 text-emerald-800", "bg-amber-100 text-amber-800",
  "bg-violet-100 text-violet-800", "bg-rose-100 text-rose-800", "bg-teal-100 text-teal-800",
];

/** A coloured circle with the first letter of the name; the colour is stable per user. */
export function Avatar({ name, id, size = "md" }: { name: string | null; id: number | null; size?: "sm" | "md" | "lg" }) {
  const tone = id == null ? "bg-slate-100 text-slate-400" : AVATAR_TONES[id % AVATAR_TONES.length];
  const box = { sm: "h-8 w-8 text-sm", md: "h-10 w-10 text-base", lg: "h-14 w-14 text-xl" }[size];
  return (
    <span aria-hidden className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${tone} ${box}`}>
      {(name ?? "?").trim().charAt(0) || "?"}
    </span>
  );
}

export function RoleBadge({ role }: { role: string }) {
  const label = f.roleBadges[role];
  if (!label) return null;
  const tone = role === "admin" ? "bg-rose-50 text-rose-700 ring-rose-200" : "bg-sky-50 text-sky-700 ring-sky-200";
  return <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ring-1 ${tone}`}>{label}</span>;
}

export function ThreadBadges({ thread }: { thread: Pick<ForumThreadSummary, "is_pinned" | "is_locked"> }) {
  return (
    <>
      {thread.is_pinned && (
        <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-800 ring-1 ring-amber-200">📌 {f.pinned}</span>
      )}
      {thread.is_locked && (
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200">🔒 {f.locked}</span>
      )}
    </>
  );
}

export function Breadcrumbs({ items }: { items: { to?: string; label: string }[] }) {
  return (
    <nav aria-label="breadcrumbs" className="mb-3 flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
      {items.map((item, i) => (
        <Fragment key={i}>
          {i > 0 && <span aria-hidden className="text-slate-300">‹</span>}
          {item.to ? <Link to={item.to} className="hover:text-slate-800 hover:underline">{item.label}</Link>
            : <span className="text-slate-700" dir="auto">{item.label}</span>}
        </Fragment>
      ))}
    </nav>
  );
}

export function SearchBox({ value, onSearch }: { value: string; onSearch: (q: string) => void }) {
  const [text, setText] = useState(value);
  return (
    <form role="search" className="flex gap-2" onSubmit={(e) => { e.preventDefault(); onSearch(text.trim()); }}>
      <input className={`${forumControl} sm:w-64`} type="search" value={text} placeholder={f.search} maxLength={100}
             aria-label={f.search} dir="auto" onChange={(e) => setText(e.target.value)} />
      <button className={forumSecondary}>{f.searchSubmit}</button>
    </form>
  );
}

/** One row of a thread list: who opened it, counters and the latest reply. */
export function ThreadRow({ thread, showCategory }: { thread: ForumThreadSummary; showCategory?: boolean }) {
  return (
    <li className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 ${thread.is_pinned ? "bg-amber-50/40" : ""}`}>
      <Avatar name={thread.author_name} id={thread.author_id} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <ThreadBadges thread={thread} />
          <Link to={`/forum/t/${thread.id}`} className="truncate font-medium text-slate-900 hover:text-sky-700 hover:underline" dir="auto">
            {thread.title}
          </Link>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
          <span>{thread.author_name ?? f.deletedUser}</span>
          <span aria-hidden>·</span>
          <span>{formatRelative(thread.created_at)}</span>
          {showCategory && (
            <>
              <span aria-hidden>·</span>
              <Link to={`/forum/c/${thread.category}`} className="hover:text-slate-800 hover:underline">
                {f.categories[thread.category]}
              </Link>
            </>
          )}
        </div>
      </div>
      <dl className="hidden w-28 shrink-0 grid-cols-2 gap-x-2 text-center sm:grid">
        <dt className="text-[11px] text-slate-400">{f.replies}</dt>
        <dt className="text-[11px] text-slate-400">{f.views}</dt>
        <dd className="text-sm font-medium tabular-nums text-slate-700">{thread.reply_count}</dd>
        <dd className="text-sm tabular-nums text-slate-500">{thread.view_count}</dd>
      </dl>
      <div className="hidden w-36 shrink-0 text-xs text-slate-500 md:block">
        <div className="truncate text-slate-700">{thread.last_post_user_name ?? f.deletedUser}</div>
        <div>{formatRelative(thread.last_post_at)}</div>
      </div>
    </li>
  );
}

const URL_RE = /(https?:\/\/[^\s<>"']+)/g;

function Linkified({ text }: { text: string }) {
  return (
    <>
      {text.split(URL_RE).map((part, i) =>
        i % 2 === 1 ? (
          <a key={i} href={part} target="_blank" rel="noopener noreferrer nofollow ugc"
             className="ltr break-all text-sky-700 underline hover:text-sky-900">{part}</a>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}

/** Plain text with line breaks; lines starting with ">" are shown as a quote, URLs as links. */
export function PostBody({ body }: { body: string }) {
  const blocks: { quote: boolean; lines: string[] }[] = [];
  for (const line of body.split("\n")) {
    const quote = line.startsWith(">");
    const text = quote ? line.replace(/^>\s?/, "") : line;
    const last = blocks[blocks.length - 1];
    if (last && last.quote === quote) last.lines.push(text);
    else blocks.push({ quote, lines: [text] });
  }
  // Blank lines at the edges of a block become the gap between blocks, not extra empty lines.
  const visible = blocks
    .map((b) => ({ ...b, lines: b.lines.join("\n").replace(/^\s*\n|\n\s*$/g, "").split("\n") }))
    .filter((b) => b.lines.some((l) => l.trim()));
  return (
    <div className="space-y-2 text-[15px] leading-7 text-slate-800">
      {visible.map((b, i) =>
        b.quote ? (
          <blockquote key={i} dir="auto" className="whitespace-pre-wrap rounded-md border-s-4 border-sky-300 bg-sky-50/60 px-3 py-2 text-sm text-slate-600">
            <Linkified text={b.lines.join("\n")} />
          </blockquote>
        ) : (
          <p key={i} dir="auto" className="whitespace-pre-wrap break-words">
            <Linkified text={b.lines.join("\n")} />
          </p>
        ),
      )}
    </div>
  );
}
