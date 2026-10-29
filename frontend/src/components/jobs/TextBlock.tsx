import { he } from "../../i18n/he";

/** Multi-line text from a posting, or a note that the source left it empty. */
export function TextBlock({ text }: { text: string }) {
  return text ? (
    <p className="text-[15px] leading-7 whitespace-pre-line text-slate-700" dir="auto">{text}</p>
  ) : (
    <p className="text-sm text-slate-400">{he.job.notProvided}</p>
  );
}
