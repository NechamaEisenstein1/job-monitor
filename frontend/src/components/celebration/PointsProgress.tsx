import { useCountUp } from "../../hooks/useCountUp";
import { he } from "../../i18n/he";
import type { PointsGoal } from "./pointsGoal";

const c = he.celebration;

/** The balance counting up to its new value, and how close it now is to the next goal. */
export function PointsProgress({ from, to, goal }: { from: number; to: number; goal: PointsGoal | undefined }) {
  const balance = useCountUp(from, to);
  const left = goal ? Math.max(0, goal.target - balance) : 0;

  return (
    <div className="w-full rounded-xl bg-slate-50 p-4 text-start">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold">{c.balance}</span>
        <span className="text-xl font-extrabold tabular-nums">
          {balance} <span className="text-[13px] font-medium text-slate-600">{c.points}</span>
        </span>
      </div>
      {goal && (
        <>
          <div role="progressbar" aria-label={goal.label} aria-valuemin={0} aria-valuemax={goal.target} aria-valuenow={Math.min(balance, goal.target)}
               className="mt-2.5 h-2.5 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-brand-700" style={{ width: `${Math.min(100, (balance / goal.target) * 100)}%` }} />
          </div>
          <p className="mt-2 text-[13.5px] text-slate-600">{left ? goal.toGo(left) : goal.reached}</p>
        </>
      )}
    </div>
  );
}
