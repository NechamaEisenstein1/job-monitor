import type { ArticleBlock } from "../../types/articles";

function ArticleBlockView({ block }: { block: ArticleBlock }) {
  switch (block.kind) {
    case "heading":
      return <h2 className="pt-6 text-xl font-semibold text-slate-900">{block.text}</h2>;
    case "paragraph":
      return <p className="leading-8 text-slate-700">{block.text}</p>;
    case "list":
      return (
        <ul className="list-disc space-y-2 ps-5 leading-7 text-slate-700 marker:text-brand-600">
          {block.items.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      );
  }
}

export function ArticleBody({ blocks }: { blocks: ArticleBlock[] }) {
  return (
    <div className="mt-6 space-y-3">
      {blocks.map((block, i) => <ArticleBlockView key={i} block={block} />)}
    </div>
  );
}
