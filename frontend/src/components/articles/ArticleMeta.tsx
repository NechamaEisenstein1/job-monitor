import { CalendarDays, Clock } from "lucide-react";

import { he } from "../../i18n/he";
import { formatDate } from "../../services/format";
import type { ArticleSummary } from "../../types/articles";
import { Badge, Icon } from "../StatusBadge";

/** Publication date and reading time, under an article's title. Drafts (visible to the admin only) say so. */
export function ArticleMeta({ article }: { article: ArticleSummary }) {
  return (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
      {!article.is_published && <Badge tone="amber">{he.site.articles.draft}</Badge>}
      <span className="inline-flex items-center gap-1.5">
        <Icon icon={CalendarDays} className="size-4" />
        <time dateTime={article.published_on}>{formatDate(article.published_on)}</time>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Icon icon={Clock} className="size-4" />
        {he.site.articles.readingTime(article.reading_minutes)}
      </span>
    </p>
  );
}
