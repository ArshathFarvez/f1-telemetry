const RBR = {
  bg: "#0a0e1a",
  card: "#0f1623",
  border: "#1c2333",
  red: "#e8002d",
  navy: "#1e3a5f",
  text: "#e8eaf0",
  muted: "#5a6a80",
  yellow: "#ffd700",
};

function Bar({ value, max = 100, color }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ background: RBR.border, borderRadius: 3, height: 6, overflow: "hidden" }}>
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: color,
          borderRadius: 3,
          transition: "width 0.2s ease",
        }}
      />
    </div>
  );
}

function Stat({ label, value, unit, max, barColor }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: RBR.muted, textTransform: "uppercase" }}>
          {label}
        </span>
        <span style={{ fontSize: 22, fontWeight: 700, color: RBR.text, fontVariantNumeric: "tabular-nums" }}>
          {value ?? "—"}
          {unit && <span style={{ fontSize: 12, color: RBR.muted, marginLeft: 3 }}>{unit}</span>}
        </span>
      </div>
      {barColor && <Bar value={value ?? 0} max={max} color={barColor} />}
    </div>
  );
}

export default function TelemetryCard({ speed, throttle, brake, gear, driver }) {
  return (
    <div
      style={{
        background: RBR.card,
        border: `1px solid ${RBR.border}`,
        borderTop: `3px solid ${RBR.red}`,
        borderRadius: 8,
        padding: "20px 24px",
        width: 280,
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", color: RBR.red, textTransform: "uppercase" }}>
          Live Telemetry
        </span>
        {driver && (
          <span style={{ fontSize: 11, color: RBR.muted, fontWeight: 600 }}>
            #{driver}
          </span>
        )}
      </div>

      {/* Gear — hero stat */}
      <div
        style={{
          background: RBR.bg,
          border: `1px solid ${RBR.navy}`,
          borderRadius: 6,
          padding: "10px 0",
          textAlign: "center",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: RBR.muted, textTransform: "uppercase", marginBottom: 4 }}>
          Gear
        </div>
        <div style={{ fontSize: 48, fontWeight: 800, color: RBR.yellow, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
          {gear ?? "—"}
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Stat label="Speed" value={speed} unit="km/h" max={380} barColor={RBR.red} />
        <Stat label="Throttle" value={throttle} unit="%" max={100} barColor="#00c853" />
        <Stat label="Brake" value={brake} unit="%" max={100} barColor="#ff6d00" />
      </div>
    </div>
  );
}
