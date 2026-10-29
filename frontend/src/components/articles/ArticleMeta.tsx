import { CalendarDays, Clock } from "lucide-react";

import { estimateReadingMinutes, type Article } from "../../content/articles";
import { he } from "../../i18n/he";
import { formatDate } from "../../services/format";
import { Icon } from "../StatusBadge";

/** Publication date and reading time, under an article's title. */
export function ArticleMeta({ article }: { article: Article }) {
  return (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
      <span className="inline-flex items-center gap-1.5">
        <Icon icon={CalendarDays} className="size-4" />
        <time dateTime={article.published}>{formatDate(article.published)}</time>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Icon icon={Clock} className="size-4" />
        {he.site.articles.readingTime(estimateReadingMinutes(article))}
      </span>
    </p>
  );
}
