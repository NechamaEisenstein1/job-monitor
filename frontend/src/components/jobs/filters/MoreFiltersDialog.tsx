import { he } from "../../../i18n/he";
import type { JobFilterValues } from "../../../types/api";
import { button } from "../../ui/button";
import { Dialog } from "../../ui/Dialog";
import { clearedFilters, EXTRA_FILTERS, type FilterContext } from "./filterConfig";
import { FilterField } from "./FilterField";

const f = he.filters;

/** The less-used filters, in a sheet. Changes apply at once; the footer shows the result count. */
export function MoreFiltersDialog({ open, onClose, value, context, total, onChange }: {
  open: boolean;
  onClose: () => void;
  value: JobFilterValues;
  context: FilterContext;
  total: number | undefined;
  onChange: (next: Partial<JobFilterValues>) => void;
}) {
  return (
    <Dialog open={open} onClose={onClose} title={f.more} placement="sheet" footer={
      <div className="flex gap-2.5">
        <button type="button" className={button("secondary", "lg")} onClick={() => onChange(clearedFilters(value))}>
          {f.clearAll}
        </button>
        <button type="button" className={`${button("primary", "lg")} flex-1`} onClick={onClose}>
          {total === undefined ? f.show : f.showCount(total)}
        </button>
      </div>
    }>
      <div className="flex flex-col gap-5 p-4">
        {EXTRA_FILTERS.map((filter) => (
          <FilterField key={filter.key} filter={filter} value={value} context={context} onChange={onChange} />
        ))}
      </div>
    </Dialog>
  );
}
