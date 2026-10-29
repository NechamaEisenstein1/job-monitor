import { Eye, Pencil, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { articleEditorPath, articlePath, newArticlePath } from "../../components/articles/articlePaths";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { Badge, Icon } from "../../components/StatusBadge";
import { button, iconButton } from "../../components/ui/button";
import { Card } from "../../components/ui/Card";
import { PageHeader } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import { formatDate } from "../../services/format";
import type { ArticleSummary } from "../../types/articles";

const a = he.articleAdmin;

function ArticleRow({ article, onDeleted }: { article: ArticleSummary; onDeleted: () => void }) {
  async function remove() {
    if (!window.confirm(a.confirmRemove(article.title))) return;
    try {
      await api.adminDeleteArticle(article.id);
      onDeleted();
    } catch (err) {
      window.alert((err as Error).message);
    }
  }

  return (
    <li className="flex flex-wrap items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <Link to={articleEditorPath(article.id)} className="font-medium text-slate-900 hover:text-brand-700" dir="auto">
          {article.title}
        </Link>
        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <Badge tone={article.is_published ? "green" : "amber"}>{article.is_published ? a.published : a.draft}</Badge>
          {formatDate(article.published_on)}
        </p>
      </div>
      <div className="flex items-center gap-1">
        <Link to={articlePath(article.slug)} className={iconButton("sm")} aria-label={a.view} title={a.view}>
          <Icon icon={Eye} className="size-4" />
        </Link>
        <Link to={articleEditorPath(article.id)} className={iconButton("sm")} aria-label={a.edit} title={a.edit}>
          <Icon icon={Pencil} className="size-4" />
        </Link>
        <button type="button" className={`${iconButton("sm")} hover:text-rose-700`} aria-label={a.remove} title={a.remove}
                onClick={remove}>
          <Icon icon={Trash2} className="size-4" />
        </button>
      </div>
    </li>
  );
}

export function AdminArticlesPage() {
  const articles = useApi(api.adminArticles, "admin-articles");

  return (
    <div className="max-w-4xl">
      <PageHeader title={a.title} subtitle={a.subtitle}>
        <Link to={newArticlePath} className={button("primary", "sm")}><Icon icon={Plus} className="size-4" />{a.newArticle}</Link>
      </PageHeader>
      {articles.error && <ErrorState error={articles.error} onRetry={articles.reload} />}
      <Card flush>
        {articles.loading && !articles.data && <LoadingState rows={6} />}
        {articles.data?.length === 0 && <EmptyState title={a.empty} />}
        <ul className="divide-y divide-slate-100">
          {articles.data?.map((article) => <ArticleRow key={article.id} article={article} onDeleted={articles.reload} />)}
        </ul>
      </Card>
    </div>
  );
}
