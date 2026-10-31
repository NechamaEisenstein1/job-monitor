export interface Choice<T extends string> {
  value: T;
  label: string;
}

const PILL_BASE = "min-h-10 rounded-full px-3.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-brand-600";
const PILL_ON = "border-2 border-brand-700 bg-brand-50 font-bold text-brand-700";
const PILL_OFF = "border border-slate-300 bg-white text-slate-700 hover:border-slate-400";

export function Pill({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" aria-pressed={pressed} onClick={onClick} className={`${PILL_BASE} ${pressed ? PILL_ON : PILL_OFF}`}>
      {children}
    </button>
  );
}

/** One choice out of a few, as a row of pills. */
export function ChoiceChips<T extends string>({ label, choices, selected, onSelect }: {
  label: string; choices: Choice<T>[]; selected: T | undefined; onSelect: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-col gap-2">
      <span className="text-sm font-semibold text-slate-800">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {choices.map((choice) => (
          <Pill key={choice.value} pressed={choice.value === selected} onClick={() => onSelect(choice.value)}>
            {choice.label}
          </Pill>
        ))}
      </div>
    </div>
  );
}

/** Two to four mutually exclusive options in one bar (e.g. the experience level). */
export function SegmentedChoice<T extends string>({ label, choices, selected, onSelect, size = "md" }: {
  label: string; choices: Choice<T>[]; selected: T; onSelect: (value: T) => void; size?: "sm" | "md";
}) {
  return (
    <div role="group" aria-label={label} className="flex gap-1 rounded-lg bg-slate-100 p-1">
      {choices.map((choice) => {
        const on = choice.value === selected;
        return (
          <button key={choice.value} type="button" aria-pressed={on} onClick={() => onSelect(choice.value)}
                  className={`${size === "sm" ? "h-8 px-2.5 text-xs" : "h-10 px-4 text-sm"} flex-1 whitespace-nowrap rounded-md ${
                    on ? "bg-white font-bold text-brand-700 shadow-sm" : "text-slate-700 hover:text-slate-900"}`}>
            {choice.label}
          </button>
        );
      })}
    </div>
  );
}

export function choicesFrom<T extends string>(labels: Record<T, string>, values?: T[]): Choice<T>[] {
  return (values ?? (Object.keys(labels) as T[])).map((value) => ({ value, label: labels[value] }));
}
