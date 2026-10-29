import { Check, Send, Sparkle } from "lucide-react";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { button } from "../ui/button";
import { Dialog } from "../ui/Dialog";
import { Confetti } from "./Confetti";
import { PartyIcon } from "./PartyIcon";
import type { PointsGoal } from "./pointsGoal";
import { PointsProgress } from "./PointsProgress";

const c = he.celebration;

/** What happened to the posting: on the board now (points paid), or waiting for the admin. */
export type PostOutcome =
  | { kind: "published"; points: number; balance: number }
  | { kind: "pending"; points: number };

/** Thank-you screen after posting a job, to make posting the next one feel worth it. */
export function PostCelebration({ outcome, goal, onPostAnother, onClose }: {
  outcome: PostOutcome | undefined;
  /** What the points are collected toward. */
  goal: PointsGoal | undefined;
  onPostAnother: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog open={!!outcome} onClose={onClose} title={outcome?.kind === "pending" ? c.pendingTitle : c.publishedTitle} hideHeader
            footer={
              <div className="flex flex-col gap-2.5 sm:flex-row">
                <button type="button" onClick={onPostAnother} className={`${button("primary", "lg")} flex-1`}>{c.postAnother}</button>
                <button type="button" onClick={onClose} className={button("secondary", "lg")}>{c.close}</button>
              </div>
            }>
      {outcome?.kind === "published" && <Published outcome={outcome} goal={goal} />}
      {outcome?.kind === "pending" && <Pending points={outcome.points} />}
    </Dialog>
  );
}

function Published({ outcome, goal }: { outcome: Extract<PostOutcome, { kind: "published" }>; goal: PointsGoal | undefined }) {
  return (
    <div className="relative flex flex-col items-center px-8 pt-10 pb-6 text-center">
      <Confetti />
      <div className="animate-pop flex size-22 items-center justify-center rounded-full bg-tender-100">
        <PartyIcon className="animate-wiggle size-12" />
      </div>
      <h2 className="animate-rise mt-4 text-3xl font-extrabold tracking-tight [animation-delay:.15s]">{c.publishedTitle}</h2>
      <p className="animate-rise mt-1 text-base text-slate-600 [animation-delay:.25s]">{c.thanks}</p>
      {outcome.points > 0 ? (
        <div className="animate-pop mt-5 inline-flex items-baseline gap-2 rounded-full bg-success-50 px-6 py-2.5 text-success-700 [animation-delay:.45s]">
          <span className="text-4xl font-extrabold tracking-tight">+{outcome.points}</span>
          <span className="text-lg font-bold">{c.points}</span>
        </div>
      ) : (
        <p className="mt-5 rounded-xl bg-slate-50 px-4 py-2.5 text-sm text-slate-600">{c.dailyCapReached}</p>
      )}
      <div className="mt-5 w-full">
        <PointsProgress from={outcome.balance - outcome.points} to={outcome.balance} goal={goal} />
      </div>
    </div>
  );
}

function Pending({ points }: { points: number }) {
  const steps = [c.stepSent, c.stepReview, c.stepLive(points)];
  return (
    <div className="flex flex-col items-center px-8 pt-10 pb-6 text-center">
      <div className="animate-pop relative flex size-22 items-center justify-center rounded-full bg-brand-50 text-brand-700">
        <Icon icon={Send} className="size-11" />
        <Icon icon={Sparkle} className="animate-twinkle absolute -top-1 start-1 size-5 text-tender-700" />
        <Icon icon={Sparkle} className="animate-twinkle absolute -end-1 bottom-2 size-3.5 text-success-700 [animation-delay:.5s]" />
      </div>
      <h2 className="mt-4 text-[26px] font-extrabold tracking-tight">{c.pendingTitle}</h2>
      <p className="mt-1 text-base text-slate-600">{c.pendingBody}</p>
      {points > 0 && (
        <div className="mt-5 flex w-full items-center gap-3.5 rounded-xl border-2 border-dashed border-success-100 bg-success-50 p-4 text-start">
          <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-white text-xl font-extrabold text-success-700">+{points}</span>
          <span>
            <span className="block font-bold text-success-800">{c.pendingPoints}</span>
            <span className="block text-sm text-success-800">{c.pendingPointsHint}</span>
          </span>
        </div>
      )}
      <ol className="mt-5 w-full space-y-3 text-start">
        {steps.map((step, i) => (
          <li key={step} className="flex items-center gap-3">
            <span className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${
              i === 0 ? "bg-success-700 text-white" : i === 1 ? "border-2 border-brand-600 text-brand-700" : "border-2 border-slate-300 text-slate-500"}`}>
              {i === 0 ? <Icon icon={Check} className="size-3.5" /> : i + 1}
            </span>
            <span className={i === 1 ? "font-semibold" : i === 2 ? "text-slate-600" : ""}>{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
