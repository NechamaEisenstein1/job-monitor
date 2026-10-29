import { ArticleCard } from "../../components/articles/ArticleCard";
import { ARTICLES } from "../../content/articles";
import { he } from "../../i18n/he";

const t = he.site.articles;

export function ArticlesPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
      <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{t.title}</h1>
      <p className="mt-4 max-w-2xl text-lg text-slate-600">{t.lead}</p>
      <ul className="mt-10 grid gap-4 sm:grid-cols-2">
        {ARTICLES.map((article) => <li key={article.slug}><ArticleCard article={article} /></li>)}
      </ul>
    </div>
  );
}
