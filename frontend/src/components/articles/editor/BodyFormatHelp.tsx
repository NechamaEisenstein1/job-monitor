import { he } from "../../../i18n/he";

const a = he.articleAdmin;

/** The three rules of the body text format, next to the text box. */
export function BodyFormatHelp() {
  return (
    <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 ring-1 ring-slate-200">
      <p className="font-semibold text-slate-700">{a.bodyHelpTitle}</p>
      <ul className="mt-2 space-y-1.5">
        {a.bodyHelp.map(({ prefix, meaning }) => (
          <li key={meaning} className="flex items-center gap-2">
            {prefix && <code className="ltr rounded bg-white px-1.5 py-0.5 font-mono text-slate-900 ring-1 ring-slate-200">{prefix.trim()}</code>}
            {meaning}
          </li>
        ))}
      </ul>
    </div>
  );
}
