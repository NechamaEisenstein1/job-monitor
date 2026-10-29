import type { ArticleSection } from "../../content/articles";

export function ArticleBody({ sections }: { sections: ArticleSection[] }) {
  return (
    <div className="mt-10 space-y-10">
      {sections.map((section) => (
        <section key={section.heading}>
          <h2 className="text-xl font-semibold text-slate-900">{section.heading}</h2>
          {section.paragraphs?.map((paragraph) => (
            <p key={paragraph} className="mt-3 leading-8 text-slate-700">{paragraph}</p>
          ))}
          {section.points && (
            <ul className="mt-3 list-disc space-y-2 ps-5 leading-7 text-slate-700 marker:text-brand-600">
              {section.points.map((point) => <li key={point}>{point}</li>)}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}
