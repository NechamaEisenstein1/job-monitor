import { Pencil } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { ArticleBody } from "../../components/articles/ArticleBody";
import { ArticleMeta } from "../../components/articles/ArticleMeta";
import { ARTICLES_PATH, articleEditorPath } from "../../components/articles/articlePaths";
import { ArticleSources } from "../../components/articles/ArticleSources";
import { JobBoardCallToAction } from "../../components/articles/JobBoardCallToAction";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { Icon } from "../../components/StatusBadge";
import { button } from "../../components/ui/button";
import { BackLink } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../hooks/useAuth";
import { he } from "../../i18n/he";
import { api, ApiError } from "../../services/api";

const t = he.site.articles;

export function ArticlePage() {
  const slug = useParams().slug ?? "";
  const { user } = useAuth();
  const { data: article, loading, error, reload } = useApi(() => api.article(slug), `article-${slug}`);

  if (error instanceof ApiError && error.status === 404) {
    return <EmptyState title={he.common.pageNotFound} hint={he.site.notFoundHint} />;
  }

  return (
    <article className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
      <div className="flex items-center justify-between gap-4">
        <BackLink to={ARTICLES_PATH} label={t.backToList} />
        {user?.is_admin && article && (
          <Link to={articleEditorPath(article.id)} className={button("secondary", "sm")}>
            <Icon icon={Pencil} className="size-4" />{t.edit}
          </Link>
        )}
      </div>
      {error && <div className="mt-6"><ErrorState error={error} onRetry={reload} /></div>}
      {loading && <LoadingState rows={10} />}
      {article && (
        <>
          <h1 className="mt-4 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{article.title}</h1>
          <div className="mt-4"><ArticleMeta article={article} /></div>
          <p className="mt-6 text-lg leading-8 text-slate-600">{article.summary}</p>
          <ArticleBody blocks={article.blocks} />
          {article.sources.length > 0 && <ArticleSources sources={article.sources} />}
          <JobBoardCallToAction />
        </>
      )}
    </article>
  );
}
