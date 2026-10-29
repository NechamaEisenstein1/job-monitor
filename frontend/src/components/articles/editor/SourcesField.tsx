import { Plus, X } from "lucide-react";

import { he } from "../../../i18n/he";
import type { ArticleSource } from "../../../types/articles";
import { Icon } from "../../StatusBadge";
import { button, iconButton } from "../../ui/button";
import { control } from "../../ui/form";

const a = he.articleAdmin;
const EMPTY_SOURCE: ArticleSource = { name: "", url: "" };

/** One row per source: a name and a link. Rows left empty are ignored by the server. */
export function SourcesField({ sources, onChange }: { sources: ArticleSource[]; onChange: (sources: ArticleSource[]) => void }) {
  const replaceAt = (index: number, source: ArticleSource) => onChange(sources.map((s, i) => (i === index ? source : s)));
  const removeAt = (index: number) => onChange(sources.filter((_, i) => i !== index));

  return (
    <fieldset>
      <legend className="text-xs font-medium text-slate-500">{a.sources}</legend>
      <ul className="mt-2 space-y-2">
        {sources.map((source, i) => (
          <li key={i} className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
            <input className={`${control} sm:w-2/5`} value={source.name} placeholder={a.sourceName} aria-label={a.sourceName}
                   dir="auto" onChange={(e) => replaceAt(i, { ...source, name: e.target.value })} />
            <input className={`${control} ltr min-w-0 flex-1`} type="url" value={source.url} placeholder={a.sourceUrl}
                   aria-label={a.sourceUrl} onChange={(e) => replaceAt(i, { ...source, url: e.target.value })} />
            <button type="button" className={iconButton("sm")} aria-label={a.removeSource} onClick={() => removeAt(i)}>
              <Icon icon={X} className="size-4" />
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className={`${button("ghost", "sm")} mt-2`} onClick={() => onChange([...sources, EMPTY_SOURCE])}>
        <Icon icon={Plus} className="size-4" />{a.addSource}
      </button>
    </fieldset>
  );
}
