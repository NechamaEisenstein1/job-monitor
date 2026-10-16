import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  Avatar, Breadcrumbs, PostBody, RoleBadge, ThreadBadges, forumControl, forumPrimary, forumSecondary,
} from "../../components/forum/ForumUi";
import { Pagination } from "../../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { useApi } from "../../hooks/useApi";
import { useUser } from "../../hooks/useAuth";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import { formatDate, formatDateTime, formatRelative } from "../../services/format";
import type { ForumCategoryCode, ForumPost, ForumThread } from "../../types/api";

const f = he.forum;
const actionBtn = "rounded px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-50";

function quoteOf(post: ForumPost): string {
  const name = post.author?.display_name ?? f.deletedUser;
  // Quotes of quotes are dropped so threads don't nest endlessly.
  const own = post.body.split("\n").filter((l) => !l.startsWith(">")).join("\n").trim();
  return [f.quoteHeader(name), ...own.split("\n")].map((l) => `> ${l}`.trimEnd()).join("\n") + "\n\n";
}

function PostCard({ post, onQuote, onChanged, onThreadDeleted }: {
  post: ForumPost; onQuote: (post: ForumPost) => void; onChanged: () => void; onThreadDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(post.body);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [thanks, setThanks] = useState({ count: post.thanks_count, mine: post.thanked_by_me });
  const author = post.author;
  const me = useUser();

  useEffect(() => setThanks({ count: post.thanks_count, mine: post.thanked_by_me }), [post.thanks_count, post.thanked_by_me]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    try {
      await action();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const save = () => run(async () => {
    await api.forumEditPost(post.id, draft);
    setEditing(false);
    onChanged();
  });
  const remove = () => {
    if (!window.confirm(post.number === 1 ? f.confirmDeleteThread : f.confirmDeletePost)) return;
    run(async () => {
      const result = await api.forumDeletePost(post.id);
      if (result.thread_deleted) onThreadDeleted();
      else onChanged();
    });
  };
  const toggleThanks = () => run(async () => {
    const result = await api.forumThank(post.id, !thanks.mine);
    setThanks({ count: result.thanks_count, mine: !thanks.mine });
  });

  return (
    <article id={`post-${post.id}`} className="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm sm:flex-row">
      <aside className="flex items-center gap-3 border-b border-slate-100 bg-slate-50/70 px-4 py-3 sm:w-44 sm:shrink-0 sm:flex-col sm:items-center sm:border-b-0 sm:border-e sm:py-5 sm:text-center">
        <Avatar name={author?.display_name ?? null} id={author?.id ?? null} size="lg" />
        <div className="min-w-0 space-y-1">
          <div className="truncate font-semibold text-slate-800" dir="auto">{author?.display_name ?? f.deletedUser}</div>
          {author && <RoleBadge role={author.role} />}
          {author && (
            <div className="space-y-0.5 text-[11px] text-slate-500">
              <div>{f.joined(formatDate(author.joined_at))}</div>
              <div>{f.postCount(author.post_count)}</div>
            </div>
          )}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-2 text-xs text-slate-500">
          <span title={formatDateTime(post.created_at)}>
            {formatRelative(post.created_at)}
            {post.edited_at && <span className="text-slate-400"> · {f.edited(formatRelative(post.edited_at))}</span>}
          </span>
          <a href={`#post-${post.id}`} className="ltr font-medium text-slate-400 hover:text-slate-700">{f.postNumber(post.number)}</a>
        </header>
        <div className="flex-1 px-4 py-4">
          {editing ? (
            <div className="space-y-2">
              <textarea className={`${forumControl} min-h-40`} value={draft} maxLength={10000} dir="auto" aria-label={f.body}
                        onChange={(e) => setDraft(e.target.value)} />
              <div className="flex gap-2">
                <button className={forumPrimary} disabled={busy} onClick={save}>{f.save}</button>
                <button className={forumSecondary} onClick={() => { setEditing(false); setDraft(post.body); }}>{f.cancel}</button>
              </div>
            </div>
          ) : (
            <PostBody body={post.body} />
          )}
        </div>
        <footer className="flex flex-wrap items-center gap-1 border-t border-slate-100 px-3 py-1.5">
          {thanks.count > 0 && (
            <span className="me-2 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
              👍 {f.thanksCount(thanks.count)}
            </span>
          )}
          <div className="ms-auto flex flex-wrap items-center gap-1">
            {error && <span role="alert" className="text-xs text-rose-700">{error}</span>}
            {author && author.id !== me.id && (
              <button className={`${actionBtn} ${thanks.mine ? "text-emerald-700" : ""}`} disabled={busy} onClick={toggleThanks}
                      aria-pressed={thanks.mine}>
                👍 {thanks.mine ? f.thanked : f.thanks}
              </button>
            )}
            <button className={actionBtn} onClick={() => onQuote(post)}>❝ {f.quote}</button>
            {post.can_edit && !editing && <button className={actionBtn} onClick={() => setEditing(true)}>{f.edit}</button>}
            {post.can_edit && <button className={`${actionBtn} hover:text-rose-700`} disabled={busy} onClick={remove}>{f.delete}</button>}
          </div>
        </footer>
      </div>
    </article>
  );
}

function ThreadHeader({ data, onChanged }: { data: ForumThread; onChanged: () => void }) {
  const t = data.thread;
  const canEdit = data.posts.some((p) => p.number === 1 && p.can_edit) || data.can_moderate;
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(t.title);
  const [category, setCategory] = useState<ForumCategoryCode>(t.category);
  const [error, setError] = useState<string>();

  async function update(change: Parameters<typeof api.forumUpdateThread>[1]) {
    setError(undefined);
    try {
      await api.forumUpdateThread(t.id, change);
      setEditing(false);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="mb-4 space-y-2">
      {editing ? (
        <form className="flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); update({ title, category }); }}>
          <input className={`${forumControl} sm:max-w-lg`} value={title} maxLength={200} dir="auto" aria-label={f.titleLabel}
                 onChange={(e) => setTitle(e.target.value)} />
          <select className={`${forumControl} w-auto`} value={category} aria-label={f.category}
                  onChange={(e) => setCategory(e.target.value as ForumCategoryCode)}>
            {Object.entries(f.categories).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
          <button className={forumPrimary}>{f.save}</button>
          <button type="button" className={forumSecondary} onClick={() => setEditing(false)}>{f.cancel}</button>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-tight" dir="auto">{t.title}</h1>
          <ThreadBadges thread={t} />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
        <span>{f.by(t.author_name ?? f.deletedUser)} · {formatRelative(t.created_at)}</span>
        <span>{t.reply_count} {f.replies} · {t.view_count} {f.views}</span>
        <div className="ms-auto flex flex-wrap gap-1.5">
          {canEdit && !editing && <button className={forumSecondary} onClick={() => setEditing(true)}>{f.editTitle}</button>}
          {data.can_moderate && (
            <>
              <button className={forumSecondary} onClick={() => update({ is_pinned: !t.is_pinned })}>📌 {t.is_pinned ? f.unpin : f.pin}</button>
              <button className={forumSecondary} onClick={() => update({ is_locked: !t.is_locked })}>🔒 {t.is_locked ? f.unlock : f.lock}</button>
            </>
          )}
        </div>
      </div>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    </div>
  );
}

function ReplyBox({ threadId, text, setText, inputRef, onPosted }: {
  threadId: number; text: string; setText: (t: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>; onPosted: (postId: number, page: number) => void;
}) {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>();

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(undefined);
    try {
      const result = await api.forumReply(threadId, text);
      setText("");
      onPosted(result.id, result.page);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={send} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <label className="flex flex-col gap-1.5 text-sm font-semibold text-slate-800">
        {f.replyTitle}
        <textarea ref={inputRef} className={`${forumControl} min-h-32 font-normal`} value={text} maxLength={10000} required
                  dir="auto" placeholder={f.replyPlaceholder} onChange={(e) => setText(e.target.value)} />
      </label>
      <p className="mt-1 text-xs text-slate-400">{f.bodyHint}</p>
      <div className="mt-3 flex items-center gap-3">
        <button className={forumPrimary} disabled={sending || !text.trim()}>{sending ? f.sending : f.send}</button>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      </div>
    </form>
  );
}

/** One thread: the opening message and its replies, with quoting, thanks, editing and moderation. */
export function ForumThreadPage() {
  const id = Number(useParams().id);
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page")) || 1;
  const navigate = useNavigate();
  const viewed = useRef(new Set<number>()); // a thread's views are counted once per visit, not on every refresh
  const thread = useApi(() => {
    const first = !viewed.current.has(id);
    viewed.current.add(id);
    return api.forumThread(id, page, first);
  }, `${id}|${page}`);
  const [reply, setReply] = useState("");
  const [scrollTo, setScrollTo] = useState<number>();
  const replyRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollTo && thread.data?.posts.some((p) => p.id === scrollTo)) {
      document.getElementById(`post-${scrollTo}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      setScrollTo(undefined);
    }
  }, [scrollTo, thread.data]);

  if (thread.error) return <ErrorState error={thread.error} onRetry={thread.reload} />;
  if (!thread.data) return <LoadingState rows={8} />;
  const data = thread.data;
  const t = data.thread;
  const goToPage = (p: number) => {
    setParams(p > 1 ? { page: String(p) } : {});
    window.scrollTo({ top: 0 });
  };

  function quote(post: ForumPost) {
    setReply(`${reply ? reply.trimEnd() + "\n\n" : ""}${quoteOf(post)}`);
    replyRef.current?.focus();
    replyRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="mx-auto max-w-5xl">
      <Breadcrumbs items={[
        { to: "/forum", label: f.title },
        { to: `/forum/c/${t.category}`, label: f.categories[t.category] },
        { label: t.title },
      ]} />
      <ThreadHeader key={`${t.title}|${t.category}`} data={data} onChanged={thread.reload} />
      <div className={`space-y-3 ${thread.loading ? "opacity-60" : ""}`}>
        {data.posts.length ? data.posts.map((p) => (
          <PostCard key={p.id} post={p} onQuote={quote} onChanged={thread.reload}
                    onThreadDeleted={() => navigate(`/forum/c/${t.category}`, { replace: true })} />
        )) : <EmptyState title={f.noPosts} />}
      </div>
      {data.total_posts > data.page_size && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-white">
          <Pagination page={data.page} pageSize={data.page_size} total={data.total_posts} onPage={goToPage} />
        </div>
      )}
      <div className="mt-5">
        {data.can_reply ? (
          <ReplyBox threadId={t.id} text={reply} setText={setReply} inputRef={replyRef}
                    onPosted={(postId, p) => {
                      setScrollTo(postId);
                      if (p === page) thread.reload(); // compare with the URL's page: the one actually requested
                      else setParams(p > 1 ? { page: String(p) } : {});
                    }} />
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">🔒 {f.lockedNotice}</p>
        )}
      </div>
      <div className="mt-4">
        <Link to={`/forum/c/${t.category}`} className="text-sm text-slate-500 hover:text-slate-800">→ {f.categories[t.category]}</Link>
      </div>
    </div>
  );
}
