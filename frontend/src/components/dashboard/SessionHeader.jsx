import ThemeToggle from "./ThemeToggle";
import { SUPPORTED_SEASONS } from "../../utils/driverMappings";

const SESSIONS = ["FP1", "FP2", "FP3", "SQ", "Sprint", "Q", "Race"];
const DRIVERS  = [{ label: "Max Verstappen", code: "VER" }];

const SELECT_CLS = [
  "rounded-md px-2.5 py-1.5 text-xs font-bold focus:outline-none focus:border-[#e8002d] focus:ring-2 focus:ring-[#e8002d]/20 transition-all duration-200",
  "dark:bg-[#0d1422] dark:border dark:border-[#263147] dark:text-[#e8eaf0] dark:hover:border-[#3a465f]",
  "bg-white border border-slate-200 text-slate-800 hover:border-slate-300 hover:shadow-sm",
].join(" ");

const LABEL_CLS = "text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400";
const DIV_CLS   = "hidden sm:flex flex-col gap-0.5";
const SEP_CLS   = "w-px h-8 dark:bg-[#1c2333] bg-slate-200 hidden sm:block";

function lapLabel(lap) {
  if (!lap) return "";
  if (lap.isFastest) return `Lap ${lap.lapNumber} ${lap.lapTime ?? ""}`.trim();
  return `Lap ${lap.lapNumber}${lap.lapTime ? `  ${lap.lapTime}` : ""}`;
}

export default function SessionHeader({
  year, onYearChange,
  gp, onGpChange, gpList, gpLoading,
  session, onSessionChange,
  driver, onDriverChange,
  lapList, selectedLap, onLapChange, lapLoading,
  onFetch, loading, dataPoints,
}) {
  const hasLaps = Array.isArray(lapList) && lapList.length > 0;

  return (
    <header className="flex flex-wrap items-center gap-3 px-4 sm:px-6 py-3 shrink-0 sticky top-0 z-10 transition-all duration-300 backdrop-blur
      dark:bg-[#070b14]/90 dark:border-b dark:border-[#20283a] dark:shadow-[0_10px_32px_rgba(0,0,0,0.22)]
      bg-white/88 border-b border-slate-200 shadow-[0_8px_24px_rgba(15,23,42,0.06)]">

      {/* Season */}
      <div className={DIV_CLS}>
        <label htmlFor="season-select" className={LABEL_CLS}>Season</label>
        <select id="season-select" value={year} onChange={(e) => onYearChange(e.target.value)} className={SELECT_CLS}>
          {SUPPORTED_SEASONS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className={SEP_CLS} />

      {/* Grand Prix */}
      <div className={DIV_CLS}>
        <label htmlFor="gp-select" className={LABEL_CLS}>Grand Prix</label>
        <select
          id="gp-select" value={gp}
          onChange={(e) => onGpChange(e.target.value)}
          disabled={gpLoading || gpList.length === 0}
          className={`${SELECT_CLS} disabled:opacity-50 disabled:cursor-not-allowed max-w-[160px]`}
        >
          {gpLoading && <option value="">Loading…</option>}
          {gpList.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </div>

      <div className={SEP_CLS} />

      {/* Session */}
      <div className={DIV_CLS}>
        <label htmlFor="session-select" className={LABEL_CLS}>Session</label>
        <select id="session-select" value={session} onChange={(e) => onSessionChange(e.target.value)} className={SELECT_CLS}>
          {SESSIONS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className={SEP_CLS} />

      {/* Driver */}
      <div className={DIV_CLS}>
        <label htmlFor="driver-select" className={LABEL_CLS}>Driver</label>
        <select id="driver-select" value={driver} onChange={(e) => onDriverChange(e.target.value)} className={SELECT_CLS}>
          {DRIVERS.map((d) => <option key={d.code} value={d.code}>{d.label}</option>)}
        </select>
      </div>

      <div className={SEP_CLS} />

      {/* Lap */}
      <div className={DIV_CLS}>
        <label htmlFor="lap-select" className={LABEL_CLS}>Lap</label>
        <select
          id="lap-select"
          value={selectedLap}
          onChange={(e) => onLapChange(e.target.value)}
          disabled={lapLoading || !hasLaps}
          className={`${SELECT_CLS} disabled:opacity-50 disabled:cursor-not-allowed max-w-[180px]`}
        >
          <option value="fastest">Fastest Lap</option>
          <option value="last">Last Lap</option>
          {hasLaps && <option disabled>──────────</option>}
          {lapList.map((lap) => (
            <option key={lap.lapNumber} value={String(lap.lapNumber)}>
              {lapLabel(lap)}
            </option>
          ))}
        </select>
      </div>

      <div className={SEP_CLS} />

      {/* Load */}
      <div className="flex items-end pb-0.5">
        <button
          type="button"
          onClick={onFetch}
          disabled={loading || gpLoading || !gp}
          className="px-4 py-1.5 bg-[#e8002d] hover:bg-[#c0001f] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-black uppercase tracking-wider rounded-md transition-all duration-200 hover:shadow-[0_0_18px_rgba(232,0,45,0.28)] active:scale-[0.98]"
        >
          {loading ? "Loading…" : "Load"}
        </button>
      </div>

      {/* Right: data counter + status + theme toggle */}
      <div className="ml-auto flex items-center gap-3">
        <div className="hidden sm:flex flex-col">
          <span className={LABEL_CLS}>Data Points</span>
          <span className="text-xs font-bold font-mono dark:text-[#e8eaf0] text-slate-800">{dataPoints.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${dataPoints > 0 ? "bg-[#00c853] animate-pulse" : "dark:bg-[#5a6a80] bg-slate-300"}`} />
          <span className="text-[10px] uppercase tracking-widest hidden md:block dark:text-[#5a6a80] text-slate-400">
            {dataPoints > 0 ? "Data Loaded" : "No Data"}
          </span>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
