import { useState, useEffect, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import PanelCard from "../dashboard/PanelCard";
import EmptyState from "../dashboard/EmptyState";
import { fetchComparison, fetchLapTelemetry } from "../../services/analyticsApi";
import { useChartTheme } from "../../hooks/useChartTheme";
import { telemetryDriverId, verstappenTeammate } from "../../utils/driverMappings";

const DRIVER_COLORS = {
  VER: "#e8002d",
  RIC: "#1e90ff",
  GAS: "#1e90ff",
  ALB: "#1e90ff",
  TSU: "#1e90ff",
  HAD: "#1e90ff",
  NOR: "#ff8700",
  PIA: "#ff8700",
  SAI: "#e8002d",
  HAM: "#00d2be",
  RUS: "#00d2be",
};

const FALLBACK_COLOR = "#5a6a80";

function driverColor(code, index) {
  return DRIVER_COLORS[code] ?? (index === 0 ? "#e8002d" : "#1e90ff");
}

function telemetryRows(result) {
  if (Array.isArray(result)) return result;
  if (Array.isArray(result?.data)) return result.data;
  if (Array.isArray(result?.telemetry)) return result.telemetry;
  return [];
}

function numericValue(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function sampleAt(rows, index, targetLength) {
  if (!rows.length) return null;
  if (targetLength <= 1) return rows[0];
  const sourceIndex = Math.round((index * (rows.length - 1)) / (targetLength - 1));
  return rows[Math.min(sourceIndex, rows.length - 1)] ?? null;
}

function buildOverlayData(primaryRows, secondaryRows) {
  const targetLength = Math.max(primaryRows.length, secondaryRows.length);
  if (targetLength === 0) return [];

  return Array.from({ length: targetLength }, (_, i) => {
    const p0 = sampleAt(primaryRows, i, targetLength);
    const p1 = sampleAt(secondaryRows, i, targetLength);
    return {
      index: i,
      distance: numericValue(p0?.distance ?? p1?.distance) ?? i,
      speed: numericValue(p0?.speed),
      speed2: numericValue(p1?.speed),
    };
  }).filter((pt) => pt.speed != null || pt.speed2 != null);
}

// ── Sub-components ──────────────────────────────────────────────────────────

function DriverBadge({ driver, index }) {
  const color = driverColor(driver.driver, index);
  return (
    <div
      className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-3 flex items-center gap-3"
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-black text-white shrink-0"
        style={{ background: color }}
      >
        {driver.driver?.slice(0, 2)}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-bold dark:text-[#e8eaf0] text-slate-800 truncate">{driver.driver}</p>
        <p className="text-[10px] dark:text-[#5a6a80] text-slate-500 truncate">{driver.team ?? "—"}</p>
      </div>
      <div className="ml-auto text-right shrink-0">
        <p className="text-xs font-mono font-bold dark:text-[#e8eaf0] text-slate-800">{driver.lapTime ?? "—"}</p>
        {driver.topSpeed != null && (
          <p className="text-[10px] dark:text-[#5a6a80] text-slate-500">{driver.topSpeed} km/h</p>
        )}
      </div>
    </div>
  );
}

function CompareRow({ label, drivers, field, unit, fmt }) {
  const values = drivers.map((d) => d[field] ?? 0);
  const max = Math.max(...values, 0.001);
  return (
    <div className="grid grid-cols-[1fr_72px_1fr] items-center gap-2 py-2 border-b dark:border-[#1c2333] border-slate-100 last:border-0">
      <div className="flex items-center gap-2 justify-end">
        <span className="text-xs font-mono tabular-nums dark:text-[#e8eaf0] text-slate-800">
          {fmt ? fmt(values[0]) : values[0]}{unit}
        </span>
        <div className="w-20 dark:bg-[#1c2333] bg-slate-200 rounded-full h-1.5 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${(values[0] / max) * 100}%`, background: driverColor(drivers[0]?.driver, 0) }} />
        </div>
      </div>
      <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-500 text-center">{label}</span>
      <div className="flex items-center gap-2">
        <div className="w-20 dark:bg-[#1c2333] bg-slate-200 rounded-full h-1.5 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${(values[1] / max) * 100}%`, background: driverColor(drivers[1]?.driver, 1) }} />
        </div>
        <span className="text-xs font-mono tabular-nums dark:text-[#e8eaf0] text-slate-800">
          {fmt ? fmt(values[1]) : values[1]}{unit}
        </span>
      </div>
    </div>
  );
}

function StatusBadge({ loading, error }) {
  if (loading) return (
    <span className="text-[10px] text-[#5a6a80] animate-pulse">Fetching comparison data…</span>
  );
  if (error) return (
    <span className="text-[10px] text-[#e8002d]" title={error}>Backend unavailable — showing live telemetry overlay</span>
  );
  return null;
}

// ── Main component ──────────────────────────────────────────────────────────

export default function DriverComparisonPanel({ data, session }) {
  const ct = useChartTheme();
  const teammate = verstappenTeammate(session?.year);
  const comparisonDrivers = useMemo(() => ["VER", teammate], [teammate]);
  const [apiData, setApiData]   = useState(null);
  const [telemetryByDriver, setTelemetryByDriver] = useState({});
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      fetchComparison({ year: session?.year, gp: session?.gp, session: session?.session, drivers: comparisonDrivers }),
      ...comparisonDrivers.map((driver) =>
        fetchLapTelemetry({
          driver: telemetryDriverId(driver, session?.year),
          year: session?.year,
          gp: session?.gp,
          session: session?.session,
          lap: "fastest",
        })
      ),
    ])
      .then(([comparisonResult, ...telemetryResults]) => {
        if (cancelled) return;

        if (comparisonResult.status === "fulfilled") {
          setApiData(comparisonResult.value);
        } else {
          setError(comparisonResult.reason?.message ?? "Comparison data unavailable");
        }

        const nextTelemetry = {};
        telemetryResults.forEach((result, index) => {
          if (result.status === "fulfilled") {
            const rows = telemetryRows(result.value);
            if (rows.length > 0) nextTelemetry[comparisonDrivers[index]] = rows;
          }
        });
        setTelemetryByDriver(nextTelemetry);
      })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [session?.year, session?.gp, session?.session, comparisonDrivers]);

  // Use real API drivers when available, fall back to telemetry-derived display
  const drivers = apiData?.drivers ?? [];
  const d0 = drivers[0];
  const d1 = drivers[1];

  const primaryTelemetry = telemetryByDriver[comparisonDrivers[0]] ?? data;
  const secondaryTelemetry = telemetryByDriver[comparisonDrivers[1]] ?? [];
  const overlayData = buildOverlayData(primaryTelemetry, secondaryTelemetry);

  const hasOverlayData = overlayData.length > 0;
  const hasApiData   = drivers.length >= 2;

  return (
    <div className="flex flex-col gap-4">
      {/* Status */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-[#5a6a80] uppercase tracking-widest">
          {apiData?.session ? `${apiData.session.grandPrix} ${apiData.session.year} · ${apiData.session.type}` : "Monaco 2024 · Qualifying"}
        </span>
        <StatusBadge loading={loading} error={error} />
      </div>

      {/* Driver badges */}
      {hasApiData ? (
        <div className="grid grid-cols-2 gap-3">
          {drivers.slice(0, 2).map((d, i) => <DriverBadge key={d.driver} driver={d} index={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {comparisonDrivers.map((driver) => ({ driver, team: "Red Bull Racing" })).map((d, i) => (
            <div key={d.driver} className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-3 flex items-center gap-3 opacity-40"
              style={{ borderLeftColor: driverColor(d.driver, i), borderLeftWidth: 3 }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-black text-white"
                style={{ background: driverColor(d.driver, i) }}>{d.driver.slice(0, 2)}</div>
              <div><p className="text-xs font-bold dark:text-[#e8eaf0] text-slate-800">{d.driver}</p><p className="text-[10px] dark:text-[#5a6a80] text-slate-500">{d.team}</p></div>
            </div>
          ))}
        </div>
      )}

      {/* Head-to-head sector comparison */}
      <PanelCard title="Head-to-Head" subtitle={hasApiData ? "Fastest qualifying lap sectors" : "Load data to compare"}>
        {!hasApiData ? (
          <EmptyState message={loading ? "Fetching comparison…" : "Comparison data unavailable"} hint={error ?? undefined} />
        ) : (
          <div className="px-4 py-2">
            <CompareRow label="Lap"  drivers={[d0, d1]} field="lapTimeS"  unit="s" fmt={(v) => v?.toFixed(3)} />
            <CompareRow label="S1"   drivers={[d0, d1]} field="sector1S"  unit="s" fmt={(v) => v?.toFixed(3)} />
            <CompareRow label="S2"   drivers={[d0, d1]} field="sector2S"  unit="s" fmt={(v) => v?.toFixed(3)} />
            <CompareRow label="S3"   drivers={[d0, d1]} field="sector3S"  unit="s" fmt={(v) => v?.toFixed(3)} />
            <CompareRow label="V-Max" drivers={[d0, d1]} field="topSpeed" unit=" km/h" />
          </div>
        )}
      </PanelCard>

      {/* Sector winners */}
      {hasApiData && apiData?.sectorWinners && (
        <div className="grid grid-cols-3 gap-2">
          {["sector1", "sector2", "sector3"].map((s, i) => {
            const winner = apiData.sectorWinners[s];
            const color  = winner ? driverColor(winner, drivers.findIndex((d) => d.driver === winner)) : FALLBACK_COLOR;
            return (
              <div key={s} className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-2 text-center"
                style={{ borderTopColor: color, borderTopWidth: 2 }}>
                <p className="text-[9px] dark:text-[#5a6a80] text-slate-500 uppercase tracking-widest mb-1">S{i + 1} Winner</p>
                <p className="text-sm font-black" style={{ color }}>{winner ?? "—"}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Speed overlay chart */}
      <PanelCard title="Speed Overlay" subtitle="Live telemetry trace" accent className="flex-1">
        {!hasOverlayData ? (
          <EmptyState message="Load telemetry to see speed overlay" hint="Enter a driver number and click Load" />
        ) : (
          <div className="p-4 w-full min-w-0" style={{ height: 224, minHeight: 224 }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <LineChart data={overlayData}>
                <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" />
                <XAxis dataKey="distance" hide />
                <YAxis tick={{ fill: ct.axisText, fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, borderRadius: 6, fontSize: 11 }}
                  labelStyle={{ color: ct.axisText }}
                />
                <Line type="monotone" dataKey="speed"  stroke="#e8002d" strokeWidth={1.5} dot={false} name={d0?.driver ?? "VER"} connectNulls isAnimationActive={false} />
                <Line type="monotone" dataKey="speed2" stroke="#1e90ff" strokeWidth={1.5} dot={false} name={d1?.driver ?? teammate} strokeDasharray="4 2" connectNulls isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </PanelCard>
    </div>
  );
}
