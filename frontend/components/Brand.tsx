import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      role="img"
      aria-label="Lynsea logo"
    >
      {/* Two diverging paths from one origin — the parallel-futures motif */}
      <circle cx="6" cy="16" r="3" fill="#3b6ef5" />
      <path
        d="M8.5 15 C 16 11, 20 9, 27 7"
        stroke="#0d9488"
        strokeWidth="2.4"
        fill="none"
        strokeLinecap="round"
      />
      <path
        d="M8.5 17 C 16 21, 20 23, 27 25"
        stroke="#d97706"
        strokeWidth="2.4"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="28" cy="6.6" r="2" fill="#0d9488" />
      <circle cx="28" cy="25.4" r="2" fill="#d97706" />
    </svg>
  );
}

export function Header({ subtitle }: { subtitle?: string }) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]/70 backdrop-blur sticky top-0 z-30">
      <div className="mx-auto max-w-[1180px] px-5 py-3 flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5 focus-ring rounded-lg">
          <Logo className="w-7 h-7" />
          <div className="leading-tight">
            <div className="font-semibold tracking-tight text-[var(--ink)]">
              Lynsea
            </div>
            <div className="text-[11px] text-[var(--muted)] -mt-0.5">
              {subtitle ?? "Decision-outcome simulator"}
            </div>
          </div>
        </Link>
        <div className="ml-auto chip text-[var(--muted)]">
          Probabilities, not prophecy
        </div>
      </div>
    </header>
  );
}
