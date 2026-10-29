import { ExternalLink } from "lucide-react";

import type { ArticleSource } from "../../types/articles";
import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";

export function ArticleSources({ sources }: { sources: ArticleSource[] }) {
  return (
    <section className="mt-12 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-slate-800">{he.site.articles.sourcesTitle}</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {sources.map((source) => (
          <li key={source.url}>
            <a href={source.url} target="_blank" rel="noopener noreferrer nofollow" dir="auto"
               className="inline-flex items-center gap-1.5 text-brand-700 hover:underline">
              {source.name}<Icon icon={ExternalLink} className="size-3.5" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
