import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Breadcrumbs, CategoryIcon, forumControl, forumPrimary, forumSecondary } from "../../components/forum/ForumUi";
import { Card, PageHeader } from "../../components/Layout";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import type { ForumCategoryCode } from "../../types/api";

const f = he.forum;
const field = "flex flex-col gap-1 text-xs font-medium text-slate-500";

/** Opening a thread: pick a category, a title and the first message. */
export function ForumNewThreadPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const initial = params.get("category");
  const [category, setCategory] = useState<ForumCategoryCode>(
    (initial && initial in f.categories ? initial : "questions") as ForumCategoryCode);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>();

  async function publish(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(undefined);
    try {
      const { id } = await api.forumCreateThread({ category, title, body });
      navigate(`/forum/t/${id}`, { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setSending(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <Breadcrumbs items={[{ to: "/forum", label: f.title }, { label: f.newThread }]} />
      <PageHeader title={f.newThread} />
      <Card>
        <form onSubmit={publish} className="space-y-4">
          <fieldset>
            <legend className="mb-2 text-xs font-medium text-slate-500">{f.category}</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {Object.entries(f.categories).map(([code, label]) => (
                <label key={code} className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm ring-1 transition ${
                  category === code ? "bg-slate-900 text-white ring-slate-900" : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50"}`}>
                  <input type="radio" name="category" value={code} className="sr-only" checked={category === code}
                         onChange={() => setCategory(code as ForumCategoryCode)} />
                  <CategoryIcon code={code} size="sm" />
                  {label}
                </label>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-slate-400">{f.categoryHints[category]}</p>
          </fieldset>
          <label className={field}>
            {f.titleLabel}
            <input className={forumControl} value={title} minLength={3} maxLength={200} required dir="auto"
                   placeholder={f.titleHint} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className={field}>
            {f.body}
            <textarea className={`${forumControl} min-h-56`} value={body} maxLength={10000} required dir="auto"
                      onChange={(e) => setBody(e.target.value)} />
            <span className="font-normal text-slate-400">{f.bodyHint}</span>
          </label>
          <div className="flex items-center gap-3">
            <button className={forumPrimary} disabled={sending}>{sending ? f.publishing : f.publish}</button>
            <button type="button" className={forumSecondary} onClick={() => navigate(-1)}>{f.cancel}</button>
            {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
          </div>
        </form>
      </Card>
    </div>
  );
}
