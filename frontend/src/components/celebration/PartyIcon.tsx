/** Party popper, drawn inline so it can wiggle (no image request, no emoji). */
export function PartyIcon({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 48 48" fill="none" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M8 42l8-24 14 14z" fill="#f59e0b" stroke="#b45309" strokeWidth="2" />
      <path d="M13 27l8 8M11 33l4 4" stroke="#b45309" strokeWidth="2" />
      <path d="M26 14c2-4 6-5 8-3" stroke="#1d4ed8" strokeWidth="2.5" />
      <path d="M33 22c4-1 7 1 7 4" stroke="#db2777" strokeWidth="2.5" />
      <circle cx="38" cy="10" r="2.2" fill="#10b981" />
      <circle cx="22" cy="8" r="1.8" fill="#f59e0b" />
      <circle cx="42" cy="18" r="1.8" fill="#1d4ed8" />
      <path d="M30 6l1 3M36 30l3 1" stroke="#10b981" strokeWidth="2.5" />
    </svg>
  );
}
