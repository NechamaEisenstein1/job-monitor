import { X } from "lucide-react";
import { useEffect, useRef } from "react";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { iconButton } from "./button";

type Placement = "center" | "sheet" | "fullscreen";

const PLACEMENT: Record<Placement, string> = {
  // A card in the middle of the screen.
  center: "m-auto max-h-[92dvh] w-[min(32rem,calc(100%-2rem))] rounded-2xl",
  // Rises from the bottom on phones; slides in from the side on wider screens.
  sheet: "mt-auto mb-0 max-h-[92dvh] w-full max-w-none rounded-t-2xl " +
    "sm:m-0 sm:ms-auto sm:h-full sm:max-h-none sm:w-[26rem] sm:rounded-none",
  // The whole screen (phone detail views).
  fullscreen: "m-0 h-full max-h-none w-full max-w-none",
};

/** Accessible modal on top of the native <dialog>: focus is kept inside, Escape and the
 *  backdrop close it, and the page behind does not scroll. */
export function Dialog({ open, onClose, title, placement = "center", hideHeader, footer, children }: {
  open: boolean;
  onClose: () => void;
  title: string;
  placement?: Placement;
  /** Keep the title for screen readers only (the content shows its own heading). */
  hideHeader?: boolean;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()} // a click on the backdrop
      className={`flex-col overflow-hidden bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-900/50 open:flex ${PLACEMENT[placement]}`}
    >
      {hideHeader ? (
        <button type="button" onClick={onClose} aria-label={he.common.close} className={`${iconButton()} absolute end-2 top-2 z-10`}>
          <Icon icon={X} className="size-5" />
        </button>
      ) : (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-2">
          <h2 className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} aria-label={he.common.close} className={iconButton()}>
            <Icon icon={X} className="size-5" />
          </button>
        </header>
      )}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{children}</div>
      {footer && <footer className="border-t border-slate-100 p-4">{footer}</footer>}
    </dialog>
  );
}
