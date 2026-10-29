/** Guide articles, as backend/application/article_dto.py serves them. */

export interface ArticleSource {
  name: string;
  url: string;
}

export type ArticleBlock =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

export interface ArticleSummary {
  id: number;
  slug: string;
  title: string;
  summary: string;
  published_on: string;
  is_published: boolean;
  reading_minutes: number;
  updated_at: string;
}

export interface Article extends ArticleSummary {
  blocks: ArticleBlock[];
  sources: ArticleSource[];
}

/** What the admin edits; `body` is in the text format of backend/domain/services/articles.py. */
export interface ArticleInput {
  slug: string;
  title: string;
  summary: string;
  body: string;
  sources: ArticleSource[];
  is_published: boolean;
  published_on: string;
}

export type EditableArticle = ArticleSummary & Pick<ArticleInput, "body" | "sources">;
