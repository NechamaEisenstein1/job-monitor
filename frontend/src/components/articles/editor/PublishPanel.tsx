import { CheckCircle2, Eye } from "lucide-react";
import { Link } from "react-router-dom";

import { he } from "../../../i18n/he";
import { Icon } from "../../StatusBadge";
import { button } from "../../ui/button";
import { Card } from "../../ui/Card";
import { control, fieldHint, fieldLabel } from "../../ui/form";

const a = he.articleAdmin;

export type SaveStatus = "editing" | "saving" | "saved";

/** Side panel of the editor: publication settings, the save button and its outcome. */
export function PublishPanel({ isPublished, publishedOn, onChange, status, error, previewTo }: {
  isPublished: boolean;
  publishedOn: string;
  onChange: (changes: { is_published?: boolean; published_on?: string }) => void;
  status: SaveStatus;
  error?: string;
  previewTo?: string;
}) {
  return (
    <Card>
      <div className="space-y-4">
        <label className="flex items-start gap-2 text-sm text-slate-800">
          <input type="checkbox" className="mt-1" checked={isPublished} onChange={(e) => onChange({ is_published: e.target.checked })} />
          <span>{a.fields.isPublished}<span className={`block ${fieldHint}`}>{a.fields.isPublishedHint}</span></span>
        </label>
        <label className={fieldLabel}>
          {a.fields.publishedOn}
          <input type="date" className={control} value={publishedOn} required onChange={(e) => onChange({ published_on: e.target.value })} />
        </label>
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        {status === "saved" && (
          <p role="status" className="flex items-center gap-1.5 text-sm text-success-700">
            <Icon icon={CheckCircle2} className="size-4" />{a.saved}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <button className={button("primary", "sm")} disabled={status === "saving"}>
            {status === "saving" ? a.saving : a.save}
          </button>
          {previewTo && (
            <Link to={previewTo} className={button("secondary", "sm")}><Icon icon={Eye} className="size-4" />{a.preview}</Link>
          )}
        </div>
      </div>
    </Card>
  );
}
