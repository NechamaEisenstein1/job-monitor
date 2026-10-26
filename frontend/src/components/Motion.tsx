import { useEffect, useRef, useState } from "react";

const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** Staggered entrance delay for the i-th item of a list, capped so long lists don't drag. */
export function stagger(i: number, step = 40, max = 400): React.CSSProperties {
  return { animationDelay: `${Math.min(i * step, max)}ms` };
}

/** Fades its children in the first time they scroll into view. */
export function Reveal({ children, className = "", delay = 0, as: Tag = "div" }: {
  children: React.ReactNode; className?: string; delay?: number; as?: "div" | "section" | "li";
}) {
  const ref = useRef<HTMLElement>(null);
  // Starts visible; only hidden once we know an observer will show it again.
  const [state, setState] = useState<"idle" | "pending" | "shown">("idle");

  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window) || reducedMotion()) return;
    if (el.getBoundingClientRect().top < window.innerHeight) return; // already on screen: no flash
    setState("pending");
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setState("shown");
        observer.disconnect();
      }
    }, { rootMargin: "0px 0px -10% 0px" });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const cls = state === "pending" ? "reveal-pending" : state === "shown" ? "reveal-shown" : "";
  return (
    <Tag ref={ref as React.Ref<never>} className={`${className} ${cls}`}
         style={state === "shown" && delay ? { transitionDelay: `${delay}ms` } : undefined}>
      {children}
    </Tag>
  );
}

/** Counts up from 0 to `target` once it is known. */
export function useCountUp(target: number | undefined, duration = 700): number | undefined {
  const [value, setValue] = useState<number | undefined>(undefined);
  useEffect(() => {
    if (target == null) return;
    if (reducedMotion() || target === 0) {
      setValue(target);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setValue(Math.round(target * (1 - (1 - t) ** 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}
