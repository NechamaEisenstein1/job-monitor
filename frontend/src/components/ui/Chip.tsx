import { X } from "lucide-react";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";

/** A selected value shown as a pill, with a button that removes it. */
export function RemovableChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex h-9 items-center gap-1 rounded-full bg-brand-50 ps-3 pe-1 text-sm font-medium text-brand-900">
      {label}
      <button type="button" onClick={onRemove} aria-label={he.common.remove(label)}
              className="inline-flex size-7 items-center justify-center rounded-full hover:bg-brand-100">
        <Icon icon={X} className="size-3.5" />
      </button>
    </span>
  );
}
