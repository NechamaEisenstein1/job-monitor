export interface ToggleOption {
  value: string;
  label: string;
}

/** A row of on/off buttons where any number can be on (e.g. experience levels). */
export function ToggleGroup({ label, options, selected, onToggle, className = "" }: {
  label: string;
  options: ToggleOption[];
  selected: string[];
  onToggle: (value: string, on: boolean) => void;
  className?: string;
}) {
  return (
    <div role="group" aria-label={label} className={`flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1 ${className}`}>
      {options.map((o) => {
        const on = selected.includes(o.value);
        return (
          <button key={o.value} type="button" aria-pressed={on} onClick={() => onToggle(o.value, !on)}
                  className={`h-9 flex-1 whitespace-nowrap rounded-md px-3 text-sm font-semibold transition-colors ${
                    on ? "bg-brand-700 text-white" : "text-slate-600 hover:bg-white hover:text-slate-900"}`}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
