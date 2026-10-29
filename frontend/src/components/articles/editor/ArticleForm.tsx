import { useState } from "react";

import { he } from "../../../i18n/he";
import type { ArticleInput } from "../../../types/articles";
import { Card } from "../../ui/Card";
import { control, fieldHint, fieldLabel } from "../../ui/form";
import { BodyFormatHelp } from "./BodyFormatHelp";
import { PublishPanel, type SaveStatus } from "./PublishPanel";
import { slugFromTitle } from "./slugFromTitle";
import { SourcesField } from "./SourcesField";

const a = he.articleAdmin;

/** The article editor. A new article's address follows its title until the admin edits the address. */
export function ArticleForm({ initial, onSubmit, previewTo, justCreated = false }: {
  initial: ArticleInput;
  onSubmit: (article: ArticleInput) => Promise<void>;
  previewTo?: string;
  justCreated?: boolean;
}) {
  const [article, setArticle] = useState(initial);
  const [slugFollowsTitle, setSlugFollowsTitle] = useState(!initial.slug);
  const [status, setStatus] = useState<SaveStatus>(justCreated ? "saved" : "editing");
  const [error, setError] = useState<string>();

  function change(changes: Partial<ArticleInput>) {
    setArticle((current) => ({ ...current, ...changes }));
    setStatus("editing");
  }

  function changeTitle(title: string) {
    change(slugFollowsTitle ? { title, slug: slugFromTitle(title) } : { title });
  }

  function changeSlug(slug: string) {
    setSlugFollowsTitle(false);
    change({ slug });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setStatus("saving");
    setError(undefined);
    try {
      await onSubmit(article);
      setStatus("saved");
    } catch (err) {
      setError((err as Error).message);
      setStatus("editing");
    }
  }

  return (
    <form onSubmit={save} className="grid gap-6 lg:grid-cols-3">
      <div className="min-w-0 lg:col-span-2">
        <Card>
          <div className="space-y-4">
            <label className={fieldLabel}>
              {a.fields.title}
              <input className={`${control} text-base`} value={article.title} required maxLength={200} dir="auto"
                     onChange={(e) => changeTitle(e.target.value)} />
            </label>
            <label className={fieldLabel}>
              {a.fields.slug}
              <input className={`${control} ltr`} value={article.slug} required maxLength={120}
                     onChange={(e) => changeSlug(e.target.value)} />
              <span className={fieldHint}>{a.fields.slugHint}</span>
            </label>
            <label className={fieldLabel}>
              {a.fields.summary}
              <textarea className={control} rows={3} value={article.summary} required maxLength={400} dir="auto"
                        onChange={(e) => change({ summary: e.target.value })} />
              <span className={fieldHint}>{a.fields.summaryHint}</span>
            </label>
            <label className={fieldLabel}>
              {a.fields.body}
              <textarea className={`${control} leading-7`} rows={18} value={article.body} required dir="auto"
                        onChange={(e) => change({ body: e.target.value })} />
            </label>
            <SourcesField sources={article.sources} onChange={(sources) => change({ sources })} />
          </div>
        </Card>
      </div>
      <div className="space-y-4">
        <PublishPanel isPublished={article.is_published} publishedOn={article.published_on} onChange={change}
                      status={status} error={error} previewTo={previewTo} />
        <BodyFormatHelp />
      </div>
    </form>
  );
}
