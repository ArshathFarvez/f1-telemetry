function TelemetryIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d="M4 16h3l2-8 4 12 2-7h5" />
    </svg>
  );
}

function ComparisonIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d="M7 5v14" />
      <path d="M17 5v14" />
      <path d="M4 9h6" />
      <path d="M14 15h6" />
      <path d="M10 9l4 6" />
    </svg>
  );
}

function TyresIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <circle cx="12" cy="12" r="7" />
      <circle cx="12" cy="12" r="3" />
      <path d="M12 5v3" />
      <path d="M12 16v3" />
      <path d="M5 12h3" />
      <path d="M16 12h3" />
    </svg>
  );
}

function StrategyIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d="M5 18V6" />
      <path d="M19 18V6" />
      <path d="M5 8h14" />
      <path d="M7 18c0-4 10-4 10-8" />
      <path d="M15 8l4 2-4 2" />
    </svg>
  );
}

function EvolutionIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d="M4 18h16" />
      <path d="M6 15l4-5 3 3 5-7" />
      <path d="M15 6h3v3" />
    </svg>
  );
}

const NAV_ITEMS = [
  { id: "telemetry",  Icon: TelemetryIcon,  label: "Telemetry" },
  { id: "comparison", Icon: ComparisonIcon, label: "Comparison" },
  { id: "tyres",      Icon: TyresIcon,      label: "Tyres" },
  { id: "strategy",   Icon: StrategyIcon,   label: "Strategy" },
  { id: "evolution",  Icon: EvolutionIcon,  label: "Track Evolution" },
];

export default function Sidebar({ active, onSelect }) {
  return (
    <aside className="sticky top-0 flex h-screen max-h-screen min-h-0 w-16 shrink-0 flex-col overflow-hidden transition-colors duration-300 lg:w-60
      dark:bg-[#070b14] dark:border-r dark:border-[#20283a]
      bg-white border-r border-slate-200 shadow-[6px_0_24px_rgba(15,23,42,0.06)] dark:shadow-[10px_0_40px_rgba(232,0,45,0.05)]">
      <div className="flex shrink-0 items-center justify-center gap-3 px-3 py-5 lg:justify-start lg:px-4 dark:border-b dark:border-[#20283a] border-b border-slate-200">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#e8002d] shadow-[0_0_22px_rgba(232,0,45,0.35)]">
          <span className="text-xs font-black text-white">VP</span>
        </div>
        <div className="hidden min-w-0 lg:block">
          <span className="block truncate text-sm font-black uppercase dark:text-[#e8eaf0] text-slate-900">
            Verstappen
          </span>
          <span className="block truncate text-[10px] font-bold uppercase tracking-widest text-[#e8002d]">
            Pitwall
          </span>
        </div>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto p-2">
        {NAV_ITEMS.map(({ id, Icon, label }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onSelect(id)}
              aria-current={isActive ? "page" : undefined}
              className={[
                "group relative flex w-full items-center justify-center gap-0 overflow-hidden rounded-md border px-2 py-2.5 text-left transition-all duration-200 lg:justify-start lg:gap-3 lg:px-3 lg:pr-7",
                isActive
                  ? "bg-[#e8002d]/15 border-[#e8002d]/40 dark:text-[#e8eaf0] text-slate-900 shadow-[0_0_22px_rgba(232,0,45,0.12)]"
                  : "border-transparent dark:text-[#6d7890] dark:hover:bg-[#101827] dark:hover:text-[#e8eaf0] text-slate-500 hover:bg-slate-100 hover:text-slate-900",
              ].join(" ")}
            >
              <span className={[
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition-all duration-200 group-hover:scale-105",
                isActive
                  ? "border-[#e8002d]/50 bg-[#e8002d]/18 text-[#e8002d]"
                  : "dark:border-[#263147] dark:bg-[#0b1220] border-slate-200 bg-white text-[#e8002d]",
              ].join(" ")}>
                <Icon className="h-4 w-4" />
              </span>
              <span className="hidden min-w-0 truncate text-xs font-semibold uppercase tracking-wide lg:block">{label}</span>
              {isActive && <span className="absolute right-2 top-1/2 hidden h-6 w-0.5 -translate-y-1/2 rounded-full bg-[#e8002d] lg:block" />}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto shrink-0 px-2 py-4 text-center lg:px-4 lg:text-left dark:border-t dark:border-[#20283a] border-t border-slate-200">
        <p className="truncate text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">
          <span className="lg:hidden">ORBR</span>
          <span className="hidden lg:inline">Oracle Red Bull Racing</span>
        </p>
      </div>
    </aside>
  );
}
