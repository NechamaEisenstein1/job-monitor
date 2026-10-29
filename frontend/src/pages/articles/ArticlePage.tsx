import { useParams } from "react-router-dom";

import { ArticleBody } from "../../components/articles/ArticleBody";
import { ArticleMeta } from "../../components/articles/ArticleMeta";
import { ArticleSources } from "../../components/articles/ArticleSources";
import { JobBoardCallToAction } from "../../components/articles/JobBoardCallToAction";
import { EmptyState } from "../../components/States";
import { BackLink } from "../../components/ui/PageHeader";
import { findArticleBySlug } from "../../content/articles";
import { he } from "../../i18n/he";

export function ArticlePage() {
  const article = findArticleBySlug(useParams().slug);
  if (!article) return <EmptyState title={he.common.pageNotFound} hint={he.site.notFoundHint} />;

  return (
    <article className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
      <BackLink to="/articles" label={he.site.articles.backToList} />
      <h1 className="mt-4 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{article.title}</h1>
      <div className="mt-4"><ArticleMeta article={article} /></div>
      <p className="mt-6 text-lg leading-8 text-slate-600">{article.summary}</p>
      <ArticleBody sections={article.sections} />
      <ArticleSources sources={article.sources} />
      <JobBoardCallToAction />
    </article>
  );
}
