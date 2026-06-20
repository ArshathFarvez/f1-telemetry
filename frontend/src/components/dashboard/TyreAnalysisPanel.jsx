import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import PanelCard from "../dashboard/PanelCard";
import EmptyState from "../dashboard/EmptyState";
import { fetchTyres } from "../../services/analyticsApi";
import { useChartTheme } from "../../hooks/useChartTheme";

const COMPOUND_META = {
  HYPERSOFT: { color: "#ff4fd8", abbr: "HS", label: "Hypersoft" },
  ULTRASOFT: { color: "#8b5cf6", abbr: "US", label: "Ultrasoft" },
  SUPERSOFT: { color: "#ff3b30", abbr: "SS", label: "Supersoft" },
  SOFT:   { color: "#e8002d", abbr: "S", label: "Soft" },
  MEDIUM: { color: "#ffd700", abbr: "M", label: "Medium" },
  HARD:   { color: "#e8eaf0", abbr: "H", label: "Hard" },
  SUPERHARD: { color: "#f4f6fb", abbr: "SH", label: "Superhard" },
  C1: { color: "#e8eaf0", abbr: "C1", label: "C1" },
  C2: { color: "#e8eaf0", abbr: "C2", label: "C2" },
  C3: { color: "#ffd700", abbr: "C3", label: "C3" },
  C4: { color: "#e8002d", abbr: "C4", label: "C4" },
  C5: { color: "#e8002d", abbr: "C5", label: "C5" },
  INTER:  { color: "#00c853", abbr: "I", label: "Inter" },
  INTERMEDIATE: { color: "#00c853", abbr: "I", label: "Intermediate" },
  WET:    { color: "#1e90ff", abbr: "W", label: "Wet" },
  FULL_WET: { color: "#1e90ff", abbr: "W", label: "Wet" },
};

const FALLBACK_COMPOUND = { color: "#5a6a80", abbr: "N/A", label: "N/A" };

function normalizeCompound(name) {
  return String(name ?? "").trim().toUpperCase().replace(/\s+/g, "_");
}

function compoundMeta(name) {
  const normalized = normalizeCompound(name);
  if (!normalized) return FALLBACK_COMPOUND;

  return COMPOUND_META[normalized] ?? {
    color: "#5a6a80",
    abbr: normalized.slice(0, 3),
    label: String(name),
  };
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function TyreVisual({ compound, age, maxAge = 30 }) {
  const meta  = compoundMeta(compound);
  const ageValue = numberOrNull(age);
  const hasAge = ageValue != null;
  const wear  = hasAge ? Math.min(100, (ageValue / Math.max(maxAge, 1)) * 100) : 0;
  const r     = 28;
  const circ  = 2 * Math.PI * r;
  const filled = circ * (1 - wear / 100);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 72 72" className="w-full h-full -rotate-90">
          <circle cx="36" cy="36" r={r} fill="none" stroke="#1c2333" strokeWidth="6" />
          <circle cx="36" cy="36" r={r} fill="none"
            stroke={meta.color} strokeWidth="6"
            strokeDasharray={`${filled} ${circ - filled}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-black" style={{ color: meta.color }}>{meta.abbr}</span>
          <span className="text-[9px] dark:text-[#5a6a80] text-slate-500">{hasAge ? `${Math.round(ageValue)}L` : "N/A"}</span>
        </div>
      </div>
      <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-500">{meta.label}</span>
      <span className="text-[10px] dark:text-[#e8eaf0] text-slate-700">{hasAge ? `${Math.round(100 - wear)}% life` : "N/A life"}</span>
    </div>
  );
}

function StintRow({ stint }) {
  const meta = compoundMeta(stint.compound);
  return (
    <div className="flex items-center gap-3 dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg px-3 py-2">
      <div className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-black text-[#0a0e1a]"
        style={{ background: meta.color }}>
        {meta.abbr}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold dark:text-[#e8eaf0] text-slate-800">
          Stint {stint.stint} · {stint.compound ?? "—"}
        </p>
        <p className="text-[10px] dark:text-[#5a6a80] text-slate-500">{stint.laps} laps · avg {stint.avgPaceS?.toFixed(3)}s</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-xs font-mono dark:text-[#e8eaf0] text-slate-800">{stint.fastestLapS?.toFixed(3)}s</p>
        <p className="text-[9px] dark:text-[#5a6a80] text-slate-500">fastest</p>
      </div>
    </div>
  );
}

export default function TyreAnalysisPanel({ data, session }) {
  const ct = useChartTheme();
  const [apiData, setApiData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchTyres({ year: session?.year, gp: session?.gp, session: session?.session, driver: session?.driver ?? "VER" })
      .then((res) => { if (!cancelled) setApiData(res); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [session?.year, session?.gp, session?.session, session?.driver]);

  const stints          = apiData?.stintSummary ?? [];
  const compoundSummary = apiData?.compoundSummary ?? [];
  const laps            = apiData?.laps ?? [];
  const fastestLap      = apiData?.fastestLap ?? {};
  const mostUsed        = apiData?.mostUsedCompound ?? null;

  const currentStint    = stints[stints.length - 1] ?? null;
  const latestTyreLap   = [...laps].reverse().find((lap) => lap.compound || lap.tyreLife != null);
  const currentCompound = latestTyreLap?.compound ?? currentStint?.compound ?? mostUsed ?? null;
  const currentAge      = numberOrNull(latestTyreLap?.tyreLife);
  const stintAges       = stints.map((s) => numberOrNull(s.laps)).filter((age) => age != null);
  const lapAges         = laps.map((lap) => numberOrNull(lap.tyreLife)).filter((age) => age != null);
  const maxAge          = Math.max(...stintAges, ...lapAges, 30);

  const degChartData = laps.length > 0
    ? laps.map((l) => ({ lap: l.lapNumber, lapTimeS: l.lapTimeS, compound: l.compound }))
    : [];

  const hasApiData  = stints.length > 0 || compoundSummary.length > 0 || laps.length > 0;
  const hasLiveData = data.length > 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">
          {apiData?.session ? `${apiData.session.grandPrix} ${apiData.session.year} · ${apiData.session.type}` : "Monaco 2024 · Race"}
          {apiData?.driver ? ` · ${apiData.driver}` : ""}
        </span>
        {loading && <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 animate-pulse">Fetching tyre data…</span>}
        {error   && <span className="text-[10px] text-[#e8002d]" title={error}>Backend unavailable</span>}
      </div>

      <PanelCard title="Current Compounds" subtitle="Tyre age & remaining life">
        {!hasApiData && !hasLiveData ? (
          <EmptyState message={loading ? "Loading tyre data…" : "No tyre data available"} />
        ) : (
          <div className="flex justify-around p-4">
            {["FL", "FR", "RL", "RR"].map((pos) => (
              <div key={pos} className="flex flex-col items-center gap-1">
                <span className="text-[9px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">{pos}</span>
                <TyreVisual compound={currentCompound} age={currentAge} maxAge={maxAge} />
              </div>
            ))}
          </div>
        )}
      </PanelCard>

      {compoundSummary.length > 0 && (
      <div className="flex gap-2">
        {compoundSummary.map((c) => {
          const meta = compoundMeta(c.compound);
          return (
            <div key={c.compound}
              className="flex-1 dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-2 text-center"
              style={{ borderBottomColor: meta.color, borderBottomWidth: 2 }}>
              <span className="text-sm font-black" style={{ color: meta.color }}>{meta.abbr}</span>
              <p className="text-[9px] dark:text-[#5a6a80] text-slate-500 mt-0.5">{c.laps != null ? `${c.laps}L` : meta.label}</p>
              {c.avgPaceS != null && (
                <p className="text-[9px] dark:text-[#e8eaf0] text-slate-700 font-mono">{c.avgPaceS.toFixed(2)}s</p>
              )}
            </div>
          );
        })}
      </div>
      )}

      {stints.length > 0 && (
        <PanelCard title="Stint Breakdown" subtitle={`${stints.length} stints · fastest ${fastestLap.lapTimeS?.toFixed(3) ?? "—"}s`}>
          <div className="flex flex-col gap-2 p-3">
            {stints.map((s) => <StintRow key={`${s.stint}-${s.compound}`} stint={s} />)}
          </div>
        </PanelCard>
      )}

      <PanelCard title="Degradation Model" subtitle="Lap time vs lap number" accent className="flex-1">
        {degChartData.length === 0 ? (
          <EmptyState message={loading ? "Loading…" : "No degradation data"} hint={error ?? undefined} />
        ) : (
          <div className="p-4 w-full min-w-0" style={{ height: 192, minHeight: 192 }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <LineChart data={degChartData}>
                <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" />
                <XAxis dataKey="lap" tick={{ fill: ct.axisText, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: ct.axisText, fontSize: 10 }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, borderRadius: 6, fontSize: 11 }}
                  labelStyle={{ color: ct.axisText }}
                  formatter={(v) => [`${v?.toFixed(3)}s`, "Lap Time"]}
                />
                <Line type="monotone" dataKey="lapTimeS" stroke="#ffd700" strokeWidth={2} dot={false} name="Lap Time" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </PanelCard>
    </div>
  );
}
