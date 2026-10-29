import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import type { Article } from "../../content/articles";
import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { ArticleMeta } from "./ArticleMeta";

export function ArticleCard({ article }: { article: Article }) {
  return (
    <Link to={`/articles/${article.slug}`}
          className="group flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-200 hover:shadow-md">
      <h2 className="text-lg font-semibold leading-snug text-slate-900 group-hover:text-brand-700">{article.title}</h2>
      <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{article.summary}</p>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <ArticleMeta article={article} />
        <span className="inline-flex items-center gap-1 text-sm font-medium text-brand-700">
          {he.site.articles.readArticle}<Icon icon={ArrowLeft} className="size-4" />
        </span>
      </div>
    </Link>
  );
}
