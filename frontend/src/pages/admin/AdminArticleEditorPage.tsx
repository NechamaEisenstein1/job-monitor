import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { ADMIN_ARTICLES_PATH, articleEditorPath, articlePath } from "../../components/articles/articlePaths";
import { ArticleForm } from "../../components/articles/editor/ArticleForm";
import { ErrorState, LoadingState } from "../../components/States";
import { BackLink, PageHeader } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { api } from "../../services/api";
import type { ArticleInput, EditableArticle } from "../../types/articles";

const a = he.articleAdmin;

/** Shown once on the editor page a new article lands on after its first save. */
interface CreatedState {
  created: true;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function emptyArticle(): ArticleInput {
  return { slug: "", title: "", summary: "", body: "", sources: [{ name: "", url: "" }], is_published: false,
    published_on: todayIso() };
}

function toInput(article: EditableArticle): ArticleInput {
  const { slug, title, summary, body, sources, is_published, published_on } = article;
  return { slug, title, summary, body, sources, is_published, published_on };
}

function EditorFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <BackLink to={ADMIN_ARTICLES_PATH} label={a.backToList} />
      <div className="mt-3"><PageHeader title={title} /></div>
      {children}
    </>
  );
}

export function NewArticlePage() {
  const navigate = useNavigate();

  async function create(article: ArticleInput) {
    const { id } = await api.adminCreateArticle(article);
    navigate(articleEditorPath(id), { replace: true, state: { created: true } satisfies CreatedState });
  }

  return <EditorFrame title={a.newArticle}><ArticleForm initial={emptyArticle()} onSubmit={create} /></EditorFrame>;
}

export function EditArticlePage() {
  const id = Number(useParams().id);
  const justCreated = (useLocation().state as CreatedState | null)?.created === true;
  const { data, error, reload } = useApi(() => api.adminArticle(id), `admin-article-${id}`);
  const [savedSlug, setSavedSlug] = useState<string>();

  async function update(article: ArticleInput) {
    await api.adminUpdateArticle(id, article);
    setSavedSlug(article.slug);
  }

  return (
    <EditorFrame title={a.editTitle}>
      {error && <ErrorState error={error} onRetry={reload} />}
      {!data ? !error && <LoadingState rows={10} /> : (
        <ArticleForm key={data.id} initial={toInput(data)} onSubmit={update} justCreated={justCreated}
                     previewTo={articlePath(savedSlug ?? data.slug)} />
      )}
    </EditorFrame>
  );
}
