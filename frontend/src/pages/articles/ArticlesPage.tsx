import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { ArticleCard } from "../../components/articles/ArticleCard";
import { newArticlePath } from "../../components/articles/articlePaths";
import { ErrorState, LoadingState } from "../../components/States";
import { Icon } from "../../components/StatusBadge";
import { button } from "../../components/ui/button";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../hooks/useAuth";
import { he } from "../../i18n/he";
import { api } from "../../services/api";

const t = he.site.articles;

export function ArticlesPage() {
  const { user } = useAuth();
  const articles = useApi(api.articles, "articles");

  return (
    <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{t.title}</h1>
        {user?.is_admin && (
          <Link to={newArticlePath} className={button("primary", "sm")}><Icon icon={Plus} className="size-4" />{t.newArticle}</Link>
        )}
      </div>
      <p className="mt-4 max-w-2xl text-lg text-slate-600">{t.lead}</p>
      <div className="mt-10">
        {articles.error && <ErrorState error={articles.error} onRetry={articles.reload} />}
        {articles.loading && <LoadingState rows={6} />}
        <ul className="grid gap-4 sm:grid-cols-2">
          {articles.data?.map((article) => <li key={article.id}><ArticleCard article={article} /></li>)}
        </ul>
      </div>
    </div>
  );
}
