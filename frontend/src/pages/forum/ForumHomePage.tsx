import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  Breadcrumbs, CategoryIcon, SearchBox, ThreadRow, forumPrimary, forumSecondary,
} from "../../components/forum/ForumUi";
import { Card } from "../../components/ui/Card";
import { PageHeader } from "../../components/ui/PageHeader";
import { Pagination } from "../../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { PAGE_SIZE, api } from "../../services/api";
import { formatRelative } from "../../services/format";
import type { ForumCategory } from "../../types/api";

const f = he.forum;
const LATEST = 10;

function CategoryCard({ category }: { category: ForumCategory }) {
  const last = category.last_post;
  return (
    <li className="flex gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow">
      <CategoryIcon code={category.code} />
      <div className="min-w-0 flex-1">
        <Link to={`/forum/c/${category.code}`} className="font-semibold text-slate-900 hover:text-sky-700 hover:underline">
          {f.categories[category.code]}
        </Link>
        <p className="mt-0.5 text-sm text-slate-500">{f.categoryHints[category.code]}</p>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <span><b className="font-semibold tabular-nums text-slate-700">{category.thread_count}</b> {f.threads}</span>
          <span><b className="font-semibold tabular-nums text-slate-700">{category.post_count}</b> {f.posts}</span>
        </div>
        <div className="mt-2 border-t border-slate-100 pt-2 text-xs text-slate-500">
          {last ? (
            <>
              <span>{f.lastPost}: </span>
              <Link to={`/forum/t/${last.thread_id}`} className="font-medium text-slate-700 hover:underline" dir="auto">
                {last.thread_title}
              </Link>
              <span> · {last.user_name ?? f.deletedUser} · {formatRelative(last.at)}</span>
            </>
          ) : f.noPosts}
        </div>
      </div>
    </li>
  );
}

function ThreadList({ category, q, page, onPage, showCategory, hidePaging }: {
  category?: string; q: string; page: number; onPage: (page: number) => void; showCategory?: boolean; hidePaging?: boolean;
}) {
  const pageSize = hidePaging ? LATEST : PAGE_SIZE;
  const threads = useApi(() => api.forumThreads({ category, q, page, page_size: pageSize }), `${category}|${q}|${page}|${pageSize}`);
  if (threads.error) return <div className="p-4"><ErrorState error={threads.error} onRetry={threads.reload} /></div>;
  if (threads.loading && !threads.data) return <LoadingState rows={6} />;
  if (!threads.data?.items.length) {
    return q ? <EmptyState title={f.noResults} /> : <EmptyState title={f.empty} hint={f.emptyHint} />;
  }
  return (
    <div className={threads.loading ? "opacity-60" : ""}>
      {q && <p className="border-b border-slate-100 px-4 py-2 text-sm text-slate-500">{f.searchResults(q, threads.data.total)}</p>}
      <ul className="divide-y divide-slate-100">
        {threads.data.items.map((t) => <ThreadRow key={t.id} thread={t} showCategory={showCategory} />)}
      </ul>
      {!hidePaging && <Pagination page={page} pageSize={pageSize} total={threads.data.total} onPage={onPage} />}
    </div>
  );
}

function useListParams() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const page = Number(params.get("page")) || 1;
  const set = (next: { q?: string; page?: number }) => {
    const search = new URLSearchParams();
    const merged = { q, ...next, page: next.page ?? 1 };
    if (merged.q) search.set("q", merged.q);
    if (merged.page > 1) search.set("page", String(merged.page));
    setParams(search);
  };
  return { q, page, set };
}

/** Forum home: the categories with their latest activity, then the newest threads everywhere. */
export function ForumHomePage() {
  const { q, page, set } = useListParams();
  const categories = useApi(api.forumCategories, "forum-categories");

  return (
    <>
      <PageHeader title={f.title} subtitle={f.subtitle}>
        <div className="flex flex-wrap gap-2">
          <SearchBox key={q} value={q} onSearch={(text) => set({ q: text })} />
          <Link to="/forum/new" className={forumPrimary}>+ {f.newThread}</Link>
        </div>
      </PageHeader>

      {q ? (
        <Card flush title={f.searchSubmit} actions={<button className={forumSecondary} onClick={() => set({ q: "" })}>{f.clearSearch}</button>}>
          <ThreadList q={q} page={page} onPage={(p) => set({ page: p })} showCategory />
        </Card>
      ) : (
        <div className="space-y-6">
          {categories.error ? <ErrorState error={categories.error} onRetry={categories.reload} />
            : !categories.data ? <LoadingState rows={5} />
            : (
              <ul className="grid gap-3 md:grid-cols-2">
                {categories.data.map((c) => <CategoryCard key={c.code} category={c} />)}
              </ul>
            )}
          <Card flush title={f.latest}>
            <ThreadList q="" page={1} onPage={() => undefined} showCategory hidePaging />
          </Card>
        </div>
      )}
    </>
  );
}

/** The threads of one category: pinned first, then by latest activity. */
export function ForumCategoryPage() {
  const { code = "" } = useParams();
  const { q, page, set } = useListParams();
  const navigate = useNavigate();
  const name = f.categories[code];
  if (!name) return <EmptyState title={he.common.pageNotFound} />;

  return (
    <>
      <Breadcrumbs items={[{ to: "/forum", label: f.title }, { label: name }]} />
      <PageHeader title={name} subtitle={f.categoryHints[code]}>
        <div className="flex flex-wrap gap-2">
          <SearchBox key={q} value={q} onSearch={(text) => set({ q: text })} />
          <button className={forumPrimary} onClick={() => navigate(`/forum/new?category=${code}`)}>+ {f.newThread}</button>
        </div>
      </PageHeader>
      <Card flush>
        <ThreadList category={code} q={q} page={page} onPage={(p) => set({ page: p })} />
      </Card>
    </>
  );
}
