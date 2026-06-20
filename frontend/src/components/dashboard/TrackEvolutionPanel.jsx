import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import PanelCard from "../dashboard/PanelCard";
import EmptyState from "../dashboard/EmptyState";
import { fetchTrackEvolution } from "../../services/analyticsApi";
import { useChartTheme } from "../../hooks/useChartTheme";

const STATIC_GRIP = Array.from({ length: 78 }, (_, i) => ({
  lap:  i + 1,
  grip: Math.min(100, 72 + i * 0.35 + Math.sin(i * 0.4) * 1.2),
  s1:   Math.max(0, 28.4 - i * 0.04 + Math.sin(i * 0.3) * 0.1),
  s2:   Math.max(0, 32.1 - i * 0.03 + Math.sin(i * 0.5) * 0.15),
  s3:   Math.max(0, 14.8 - i * 0.02 + Math.sin(i * 0.2) * 0.08),
}));

function SectorCard({ sector, time, delta, color }) {
  return (
    <div className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-3 text-center"
      style={{ borderTopColor: color, borderTopWidth: 2 }}>
      <p className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-500 mb-1">S{sector}</p>
      <p className="text-lg font-bold font-mono dark:text-[#e8eaf0] text-slate-800">{time}</p>
      <p className="text-[10px] font-mono mt-1" style={{ color }}>{delta}</p>
    </div>
  );
}

function WeatherTile({ label, value }) {
  return (
    <div className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-3 text-center">
      <p className="text-sm font-bold dark:text-[#e8eaf0] text-slate-800">{value}</p>
      <p className="text-[9px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">{label}</p>
    </div>
  );
}

export default function TrackEvolutionPanel({ data, session }) {
  const ct = useChartTheme();
  const [apiData, setApiData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchTrackEvolution({ year: session?.year, gp: session?.gp, session: session?.session })
      .then((res) => { if (!cancelled) setApiData(res); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [session?.year, session?.gp, session?.session]);

  const hasLiveData = data.length > 0;
  const hasApiData  = apiData != null;

  const ws = apiData?.weatherSummary ?? {};
  const weatherTiles = [
    { label: "Air Temp",   value: ws.airTempMax   != null ? `${ws.airTempMax}°C`      : "24°C" },
    { label: "Track Temp", value: ws.trackTempMax != null ? `${ws.trackTempMax}°C`    : "38°C" },
    { label: "Humidity",   value: ws.humidityMean != null ? `${ws.humidityMean}%`     : "62%" },
    { label: "Wind",       value: ws.windSpeedMean != null ? `${ws.windSpeedMean} m/s` : "12 kph" },
  ];

  const gripChartData = (() => {
    if (hasApiData && Array.isArray(apiData.evolution) && apiData.evolution.length > 0) {
      const times = apiData.evolution.map((e) => e.fastestLapTimeS).filter(Boolean);
      const tMax  = Math.max(...times);
      const tMin  = Math.min(...times);
      const range = tMax - tMin || 1;
      return apiData.evolution.map((e) => ({
        lap:  e.sessionTimeMin,
        grip: tMax === tMin ? 85 : Math.round(70 + ((tMax - e.fastestLapTimeS) / range) * 28),
      }));
    }
    const currentLap = hasLiveData ? Math.min(78, Math.floor(data.length / 50) + 1) : 0;
    return STATIC_GRIP.slice(0, Math.max(currentLap, 1));
  })();

  const currentLap  = hasLiveData ? Math.min(78, Math.floor(data.length / 50) + 1) : 0;
  const sectorData  = STATIC_GRIP.slice(0, Math.max(currentLap, 1));
  const currentGrip = gripChartData.length > 0 ? gripChartData[gripChartData.length - 1]?.grip?.toFixed(1) : null;
  const fastestLap  = apiData?.fastestLap ?? null;

  const sectorTimes = [
    { sector: 1, time: "28.142", delta: "-0.241", color: "#e8002d" },
    { sector: 2, time: "31.876", delta: "-0.183", color: "#ffd700" },
    { sector: 3, time: "14.621", delta: "-0.097", color: "#00c853" },
  ];

  const showGripChart   = hasApiData || hasLiveData;
  const showSectorChart = hasLiveData;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">
          {apiData?.session
            ? `${apiData.session.grandPrix} ${apiData.session.year} · ${apiData.session.type}`
            : "Monaco 2024 · Qualifying"}
          {fastestLap ? ` · Fastest: ${fastestLap.driver} ${fastestLap.lapTimeS?.toFixed(3)}s` : ""}
        </span>
        {loading && <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 animate-pulse">Fetching track data…</span>}
        {error   && <span className="text-[10px] text-[#e8002d]" title={error}>Backend unavailable — showing static data</span>}
      </div>

      <div className="grid grid-cols-4 gap-3">
        {weatherTiles.map((w) => <WeatherTile key={w.label} {...w} />)}
      </div>

      {apiData?.bestGripWindow && (
        <div className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border border-l-2 border-l-[#00c853] rounded-lg px-4 py-2 flex items-center gap-4">
          <span className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest shrink-0">Best Grip Window</span>
          <span className="text-xs font-bold text-[#00c853]">
            {apiData.bestGripWindow.trackTempLow}–{apiData.bestGripWindow.trackTempHigh}°C
          </span>
          <span className="text-[10px] dark:text-[#5a6a80] text-slate-500">
            median {apiData.bestGripWindow.medianLapTimeS?.toFixed(3)}s
          </span>
          {apiData.avgImprovementS != null && (
            <span className="text-[10px] font-mono ml-auto text-[#ffd700]">
              Δ {apiData.avgImprovementS > 0 ? "+" : ""}{apiData.avgImprovementS?.toFixed(3)}s session improvement
            </span>
          )}
        </div>
      )}

      <PanelCard title="Track Grip Evolution" subtitle={hasApiData ? "Lap time improvement over session" : "Rubber laid down over session"} accent>
        {!showGripChart ? (
          <EmptyState message={loading ? "Loading track evolution…" : "Load telemetry to see track evolution"} />
        ) : (
          <div className="p-4 w-full min-w-0" style={{ height: 208, minHeight: 208 }}>
            <div className="flex items-center gap-4 mb-3">
              <div>
                <p className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">Current Grip</p>
                <p className="text-xl font-bold font-mono text-[#00c853]">{currentGrip ?? "—"}%</p>
              </div>
              <div>
                <p className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">
                  {hasApiData ? "Session Time" : "Lap"}
                </p>
                <p className="text-xl font-bold font-mono dark:text-[#e8eaf0] text-slate-800">
                  {hasApiData
                    ? `${gripChartData[gripChartData.length - 1]?.lap?.toFixed(0)} min`
                    : `${currentLap} / 78`}
                </p>
              </div>
              {apiData?.totalValidLaps != null && (
                <div>
                  <p className="text-[10px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest">Valid Laps</p>
                  <p className="text-xl font-bold font-mono dark:text-[#e8eaf0] text-slate-800">{apiData.totalValidLaps}</p>
                </div>
              )}
            </div>
            <div className="h-28 w-full min-w-0" style={{ height: 112, minHeight: 112 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <AreaChart data={gripChartData}>
                  <defs>
                    <linearGradient id="gripGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#00c853" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#00c853" stopOpacity={0}   />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="lap" tick={{ fill: ct.axisText, fontSize: 9 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[65, 100]} tick={{ fill: ct.axisText, fontSize: 9 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, borderRadius: 6, fontSize: 11 }}
                    labelStyle={{ color: ct.axisText }}
                    formatter={(v) => [`${Number(v).toFixed(1)}%`, "Grip"]}
                  />
                  <Area type="monotone" dataKey="grip" stroke="#00c853" strokeWidth={2} fill="url(#gripGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </PanelCard>

      <PanelCard title="Sector Evolution" subtitle="Best sector times this session">
        <div className="p-4">
          <div className="grid grid-cols-3 gap-3 mb-4">
            {sectorTimes.map((s) => <SectorCard key={s.sector} {...s} />)}
          </div>
          {showSectorChart && (
            <div className="h-32 w-full min-w-0" style={{ height: 128, minHeight: 128 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <AreaChart data={sectorData}>
                  <defs>
                    <linearGradient id="s1Grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#e8002d" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#e8002d" stopOpacity={0}   />
                    </linearGradient>
                    <linearGradient id="s2Grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#ffd700" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#ffd700" stopOpacity={0}   />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="lap" hide />
                  <YAxis hide domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, borderRadius: 6, fontSize: 11 }}
                    labelStyle={{ color: ct.axisText }}
                    formatter={(v) => [`${Number(v).toFixed(3)}s`]}
                  />
                  <Area type="monotone" dataKey="s1" stroke="#e8002d" strokeWidth={1.5} fill="url(#s1Grad)" dot={false} name="S1" />
                  <Area type="monotone" dataKey="s2" stroke="#ffd700" strokeWidth={1.5} fill="url(#s2Grad)" dot={false} name="S2" />
                  <Area type="monotone" dataKey="s3" stroke="#00c853" strokeWidth={1.5} fill="none"          dot={false} name="S3" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </PanelCard>
    </div>
  );
}
