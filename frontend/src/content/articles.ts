/** The guide articles: content/articles/<slug>.json, shared with the backend (which renders their SEO pages). */

export interface ArticleSection {
  heading: string;
  paragraphs?: string[];
  points?: string[];
}

export interface ArticleSource {
  name: string;
  url: string;
}

export interface Article {
  slug: string;
  title: string;
  summary: string;
  published: string;
  sections: ArticleSection[];
  sources: ArticleSource[];
}

type ArticleFile = Omit<Article, "slug">;

const HEBREW_WORDS_PER_MINUTE = 150;

const files = import.meta.glob<ArticleFile>("../../../content/articles/*.json", { eager: true, import: "default" });

function slugFromPath(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1, -".json".length);
}

function newestFirstThenBySlug(a: Article, b: Article): number {
  if (a.published !== b.published) return a.published < b.published ? 1 : -1;
  return a.slug < b.slug ? -1 : 1;
}

export const ARTICLES: Article[] = Object.entries(files)
  .map(([path, file]) => ({ ...file, slug: slugFromPath(path) }))
  .sort(newestFirstThenBySlug);

export function findArticleBySlug(slug: string | undefined): Article | undefined {
  return ARTICLES.find((article) => article.slug === slug);
}

export function estimateReadingMinutes(article: Article): number {
  const text = article.sections.flatMap((s) => [s.heading, ...(s.paragraphs ?? []), ...(s.points ?? [])]).join(" ");
  return Math.max(1, Math.round(text.split(/\s+/).length / HEBREW_WORDS_PER_MINUTE));
}
