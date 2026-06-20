import { useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from "recharts";
import PanelCard from "../dashboard/PanelCard";
import EmptyState from "../dashboard/EmptyState";
import { useChartTheme } from "../../hooks/useChartTheme";

// ── Shared sub-components ────────────────────────────────────────────────────

function StatCard({ label, value, unit, color }) {
  return (
    <div className="dark:bg-[#0a0e1a] bg-slate-50 dark:border-[#1c2333] border-slate-200 border rounded-lg p-4 flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-widest dark:text-[#5a6a80] text-slate-500">{label}</span>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold font-mono tabular-nums" style={{ color }}>
          {value ?? "—"}
        </span>
        {unit && <span className="text-xs dark:text-[#5a6a80] text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}

function SummaryItem({ label, value, color }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">{label}</span>
      <span className="text-sm font-bold font-mono tabular-nums dark:text-[#e8eaf0] text-slate-700" style={color ? { color } : {}}>
        {value ?? "—"}
      </span>
    </div>
  );
}

function Bar({ value, max = 100, color }) {
  const pct = Math.min(100, ((value ?? 0) / max) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 dark:bg-[#1c2333] bg-slate-200 rounded-full h-2 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-200" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono tabular-nums dark:text-[#e8eaf0] text-slate-700 w-8 text-right">{value ?? 0}</span>
    </div>
  );
}

function TraceTooltip({ active, payload, ct, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: ct.tooltipBg, border: `1px solid ${ct.tooltipBorder}`, color: ct.tooltipText }}
      className="rounded px-3 py-2 text-xs font-mono">
      {payload[0].value}{unit}
    </div>
  );
}

function TraceChart({ data, dataKey, stroke, unit, domain, ct, height = "h-32", heightPx = 128 }) {
  return (
    <div className={`${height} w-full min-w-0`} style={{ height: heightPx, minHeight: heightPx }}>
      <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
        <LineChart data={data}>
          <CartesianGrid stroke={ct.grid} strokeDasharray="3 3" />
          <XAxis dataKey="distance" hide />
          <YAxis tick={{ fill: ct.axisText, fontSize: 9 }} axisLine={false} tickLine={false} domain={domain ?? ["auto", "auto"]} width={28} />
          <Tooltip content={<TraceTooltip ct={ct} unit={unit} />} />
          <Line type="monotone" dataKey={dataKey} stroke={stroke} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function TelemetryPanel({ data, session, lapSummary }) {
  const ct = useChartTheme();

  useEffect(() => {
    if (data.length > 0) {
      console.log(`[TelemetryPanel] ${data.length} rows. First:`, data[0]);
    }
  }, [data]);

  const latest = (() => {
    for (let i = data.length - 1; i >= 0; i--) {
      if ((data[i].speed ?? 0) > 0) return data[i];
    }
    return data[data.length - 1] ?? {};
  })();

  const brakeDisplay = latest.brake === true ? 100 : (typeof latest.brake === "number" ? latest.brake : 0);

  const chartData = data.map((row) => ({
    ...row,
    brakeNum: row.brake === true ? 100 : (typeof row.brake === "number" ? row.brake : 0),
  }));

  const sessionLabel = `${session?.gp ?? ""} ${session?.year ?? ""} · ${session?.session ?? "Q"}`;

  const fmt = (s) => s != null ? `${s}s` : "—";
  const fmtKmh = (v) => v != null ? `${v} km/h` : "—";

  return (
    <div className="flex flex-col gap-4">

      {/* ── Session summary card ─────────────────────────────────────────── */}
      {lapSummary && (
        <PanelCard title="Lap Summary" subtitle={sessionLabel} accent>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-x-6 gap-y-3 p-4">
            <SummaryItem label="Lap"       value={lapSummary.lapNumber} />
            <SummaryItem label="Lap Time"  value={lapSummary.lapTime}   color="#e8002d" />
            <SummaryItem label="Top Speed" value={fmtKmh(lapSummary.topSpeed)} color="#ffd700" />
            <SummaryItem label="Avg Speed" value={fmtKmh(lapSummary.avgSpeed)} />
            <SummaryItem label="Sector 1"  value={fmt(lapSummary.sector1S)} color="#e8002d" />
            <SummaryItem label="Sector 2"  value={fmt(lapSummary.sector2S)} color="#ffd700" />
            <SummaryItem label="Sector 3"  value={fmt(lapSummary.sector3S)} color="#00c853" />
          </div>
        </PanelCard>
      )}

      {/* ── Live stat cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Speed"    value={latest.speed}    unit="km/h" color="#e8002d" />
        <StatCard label="Gear"     value={latest.gear}     color="#ffd700" />
        <StatCard label="Throttle" value={latest.throttle} unit="%" color="#00c853" />
        <StatCard label="Brake"    value={brakeDisplay}    unit="%" color="#ff6d00" />
      </div>

      {/* ── Driver inputs bars ───────────────────────────────────────────── */}
      <PanelCard title="Driver Inputs" subtitle="Throttle · Brake">
        <div className="flex flex-col gap-4 p-4">
          <div>
            <div className="flex justify-between text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-500 mb-2">
              <span>Throttle</span><span>{latest.throttle ?? 0}%</span>
            </div>
            <Bar value={latest.throttle} color="#00c853" />
          </div>
          <div>
            <div className="flex justify-between text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-500 mb-2">
              <span>Brake</span><span>{brakeDisplay}%</span>
            </div>
            <Bar value={brakeDisplay} color="#ff6d00" />
          </div>
        </div>
      </PanelCard>

      {/* ── Four traces ─────────────────────────────────────────────────── */}
      {data.length === 0 ? (
        <PanelCard title="Telemetry Traces" subtitle={sessionLabel} accent>
          <EmptyState message="Load telemetry to see traces" hint="Select a session and click Load" />
        </PanelCard>
      ) : (
        <PanelCard title="Telemetry Traces" subtitle={sessionLabel} accent>
          <div className="flex flex-col gap-1 p-4">

            {/* Speed */}
            <div className="mb-1">
              <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">Speed (km/h)</span>
            </div>
            <TraceChart data={chartData} dataKey="speed"    stroke="#e8002d" unit=" km/h" domain={[0, "auto"]} ct={ct} height="h-36" heightPx={144} />

            {/* Throttle */}
            <div className="mt-3 mb-1">
              <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">Throttle (%)</span>
            </div>
            <TraceChart data={chartData} dataKey="throttle" stroke="#00c853" unit="%" domain={[0, 100]} ct={ct} />

            {/* Brake */}
            <div className="mt-3 mb-1">
              <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">Brake (%)</span>
            </div>
            <TraceChart data={chartData} dataKey="brakeNum" stroke="#ff6d00" unit="%" domain={[0, 100]} ct={ct} />

            {/* Gear */}
            <div className="mt-3 mb-1">
              <span className="text-[10px] uppercase tracking-widest dark:text-[#5a6a80] text-slate-400">Gear</span>
            </div>
            <TraceChart data={chartData} dataKey="gear"     stroke="#ffd700" unit="" domain={[0, 8]} ct={ct} />

          </div>
        </PanelCard>
      )}
    </div>
  );
}
