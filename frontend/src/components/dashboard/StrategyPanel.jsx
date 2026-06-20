import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Cell } from "recharts";
import PanelCard from "../dashboard/PanelCard";
import EmptyState from "../dashboard/EmptyState";
import { fetchStrategy } from "../../services/analyticsApi";
import { useChartTheme } from "../../hooks/useChartTheme";

const COMPOUND_COLORS = {
  SOFT:   "#e8002d",
  MEDIUM: "#ffd700",
  HARD:   "#e8eaf0",
  INTER:  "#00c853",
  WET:    "#1e90ff",
};

const STRATEGY_PALETTE = ["#ffd700", "#00c853", "#e8002d", "#1e90ff"];

function compoundColor(name) {
  return COMPOUND_COLORS[(name ?? "").toUpperCase()] ?? "#5a6a80";
}

function StintBar({ compounds, pitLaps, raceLaps }) {
  if (!compounds?.length || !raceLaps) return null;
  const boundaries = [0, ...(pitLaps ?? []), raceLaps];
  const segments = compounds.map((compound, i) => ({
    compound,
    laps: boundaries[i + 1] - boundaries[i],
  })).filter((s) => s.laps > 0);
  const total = segments.reduce((s, x) => s + x.laps, 0) || 1;
  return (
    <div className="flex h-5 rounded overflow-hidden gap-px">
      {segments.map((s, i) => (
        <div
          key={i}
          className="flex items-center justify-center text-[9px] font-bold text-[#0a0e1a]"
          style={{ width: `${(s.laps / total) * 100}%`, background: compoundColor(s.compound) }}
          title={`${s.compound} · ${s.laps}L`}
        >
          {s.laps > 8 ? s.compound?.[0] ?? "" : ""}
        </div>
      ))}
    </div>
  );
}

function PitWindowRow({ window: w, index, recommended }) {
  const color = index === 0 ? "#00c853" : index === 1 ? "#ffd700" : "#ff6d00";
  const isRec = recommended != null && recommended >= w.start && recommended <= w.end;
  return (
    <div className="flex items-center gap-3 dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg px-3 py-2">
      <div className="w-8 h-8 rounded flex items-center justify-center text-xs font-black text-[#0a0e1a] shrink-0"
        style={{ background: color }}>
        {w.start}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold dark:text-[#e8eaf0] text-slate-800">
          Stop {index + 1} Window{isRec ? " (Recommended)" : ""}
        </p>
        <p className="text-[10px] dark:text-[#5a6a80] text-slate-500">Laps {w.start}–{w.end}</p>
      </div>
      <span className="text-[10px] uppercase tracking-widest shrink-0" style={{ color }}>
        {isRec ? `Rec. L${recommended}` : `L${w.start}–${w.end}`}
      </span>
    </div>
  );
}

export default function StrategyPanel({ data, session }) {
  const ct = useChartTheme();
  const [apiData, setApiData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchStrategy({ year: session?.year, gp: session?.gp, session: session?.session, driver: session?.driver ?? "VER" })
      .then((res) => { if (!cancelled) setApiData(res); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [session?.year, session?.gp, session?.session, session?.driver]);

  const strategies     = Array.isArray(apiData?.strategies) ? apiData.strategies : [];
  const recommendation = apiData?.recommendation ?? null;
  const raceLaps       = apiData?.raceLaps ?? 78;

  const chartData = (() => {
    const sample = strategies[0]?.lapTableSample;
    if (Array.isArray(sample) && sample.length > 0) {
      return sample.map((row) => ({
        lap:  row.LapNumber ?? row.lapNumber,
        time: row.PredLapTimeSeconds ?? row.predLapTimeSeconds,
      })).filter((r) => r.lap != null && r.time != null);
    }
    return [
      { lap: 1, time: 75.2 }, { lap: 5, time: 74.8 }, { lap: 10, time: 74.5 },
      { lap: 15, time: 74.9 }, { lap: 20, time: 75.6 }, { lap: 25, time: 74.2 },
      { lap: 30, time: 74.0 }, { lap: 35, time: 74.4 }, { lap: 40, time: 75.1 },
      { lap: 45, time: 75.8 }, { lap: 50, time: 74.6 }, { lap: 55, time: 74.3 },
      { lap: 60, time: 74.1 }, { lap: 65, time: 74.8 }, { lap: 70, time: 75.2 },
      { lap: 75, time: 74.9 }, { lap: 78, time: 74.5 },
    ];
  })();

  const timeMin = Math.min(...chartData.map((d) => d.time ?? Infinity)) - 0.5;
  const timeMax = Math.max(...chartData.map((d) => d.time ?? -Infinity)) + 0.5;
  const yDomain = Number.isFinite(timeMin) ? [Math.floor(timeMin), Math.ceil(timeMax)] : [73, 77];

  const hasApiData  = strategies.length > 0;
  const hasLiveData = data.length > 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">
          {apiData?.session ? `${apiData.session.grandPrix} ${apiData.session.year} · ${apiData.session.type}` : "Monaco 2024 · Race"}
          {apiData?.driver ? ` · ${apiData.driver}` : ""}
          {raceLaps ? ` · ${raceLaps} laps` : ""}
        </span>
        {loading && <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 animate-pulse">Running simulation…</span>}
        {error   && <span className="text-[10px] text-[#e8002d]" title={error}>Backend unavailable — showing static model</span>}
      </div>

      {recommendation && (
        <div className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border border-l-2 border-l-[#00c853] rounded-lg px-4 py-2 flex items-center gap-4">
          <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest shrink-0">Recommendation</span>
          <span className="text-xs font-bold text-[#00c853]">{recommendation.fastestStrategy}</span>
          <span className="text-[10px] dark:text-[#5a6a80] text-slate-500">{recommendation.projectedFinishTimeMin} min projected</span>
          {recommendation.bestCompound && (
            <span className="text-[10px] font-mono ml-auto" style={{ color: compoundColor(recommendation.bestCompound) }}>
              Best: {recommendation.bestCompound}
            </span>
          )}
        </div>
      )}

      <PanelCard title="Strategy Simulation" subtitle="Optimal pit stop scenarios">
        <div className="flex flex-col gap-3 p-4">
          {(hasApiData ? strategies : [
            { name: "One-stop", compounds: ["MEDIUM", "HARD"],         pitLaps: [51], totalTimeMin: null, avgStintPaceS: null },
            { name: "Two-stop", compounds: ["MEDIUM", "HARD", "HARD"], pitLaps: [31, 56], totalTimeMin: null, avgStintPaceS: null },
          ]).map((s, i) => {
            const color = STRATEGY_PALETTE[i % STRATEGY_PALETTE.length];
            const isRec = recommendation?.fastestStrategy === s.name;
            const delta = strategies.length >= 2
              ? ((s.totalTimeS ?? 0) - (strategies[0]?.totalTimeS ?? 0))
              : null;
            return (
              <div key={s.name}
                className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-3"
                style={isRec ? { borderColor: "#00c853" } : {}}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold dark:text-[#e8eaf0] text-slate-800">
                    {s.name}{isRec ? " (Recommended)" : ""}
                  </span>
                  <span className="text-xs font-mono font-bold" style={{ color }}>
                    {delta != null ? (delta === 0 ? "+0.0s" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}s`) : "—"}
                  </span>
                </div>
                <p className="text-[10px] dark:text-[#5a6a80] text-slate-500 mb-2">
                  {(s.compounds ?? []).join(" → ")}
                  {s.avgStintPaceS != null ? ` · avg ${s.avgStintPaceS.toFixed(3)}s` : ""}
                </p>
                <StintBar compounds={s.compounds} pitLaps={s.pitLaps} raceLaps={raceLaps} />
              </div>
            );
          })}
        </div>
      </PanelCard>

      <PanelCard title="Pit Windows" subtitle="Optimal stop windows from simulation">
        <div className="flex flex-col gap-2 p-4">
          {hasApiData ? (
            strategies.flatMap((s, si) =>
              (s.pitWindows ?? []).map((w, wi) => (
                <PitWindowRow key={`${si}-${wi}`} window={w} index={wi} recommended={s.pitLaps?.[wi]} />
              ))
            ).slice(0, 6)
          ) : (
            [{ start: 18, end: 24 }, { start: 24, end: 31 }, { start: 31, end: 38 }].map((w, i) => (
              <PitWindowRow key={i} window={w} index={i} recommended={null} />
            ))
          )}
        </div>
      </PanelCard>

      <PanelCard title="Lap Time Projection" subtitle="Predicted pace per lap" accent className="flex-1">
        {!hasLiveData && !hasApiData ? (
          <EmptyState message={loading ? "Running strategy simulation…" : "Load telemetry for strategy analysis"} />
        ) : (
          <div className="p-4 w-full min-w-0" style={{ height: 192, minHeight: 192 }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart data={chartData} barSize={6}>
                <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="lap" tick={{ fill: ct.axisText, fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis domain={yDomain} tick={{ fill: ct.axisText, fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, borderRadius: 6, fontSize: 11 }}
                  labelStyle={{ color: ct.axisText }}
                  formatter={(v) => [`${v?.toFixed(3)}s`, "Lap Time"]}
                />
                <Bar dataKey="time" radius={[2, 2, 0, 0]}>
                  {chartData.map((entry, i) => {
                    const mid = (yDomain[0] + yDomain[1]) / 2;
                    const fill = (entry.time ?? mid) < mid - 0.3
                      ? "#00c853"
                      : (entry.time ?? mid) > mid + 0.3
                        ? "#e8002d"
                        : "#ffd700";
                    return <Cell key={i} fill={fill} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </PanelCard>
    </div>
  );
}
