import { useState, useEffect, useCallback } from "react";
import OnboardingSlider from "./components/OnboardingSlider";
import Sidebar from "./components/dashboard/Sidebar";
import SessionHeader from "./components/dashboard/SessionHeader";
import TelemetryPanel from "./components/telemetry/TelemetryPanel";
import DriverComparisonPanel from "./components/dashboard/DriverComparisonPanel";
import TyreAnalysisPanel from "./components/dashboard/TyreAnalysisPanel";
import StrategyPanel from "./components/dashboard/StrategyPanel";
import TrackEvolutionPanel from "./components/dashboard/TrackEvolutionPanel";
import { fetchSchedule, fetchLaps, fetchLapTelemetry } from "./services/analyticsApi";
import { verstappenDriverNumber } from "./utils/driverMappings";

// fetchLapTelemetry returns the telemetry array (apiFetch unwraps json.data)
function findLapMeta(laps, lap) {
  if (!laps.length) return {};
  if (lap === "fastest") return laps.find((l) => l.isFastest) ?? laps[0];
  if (lap === "last") return laps[laps.length - 1];
  const n = Number(lap);
  return laps.find((l) => l.lapNumber === n) ?? {};
}

function parseLapTelemetry(result, lapMeta = {}) {
  if (Array.isArray(result)) {
    const speeds = result.map((r) => r.speed).filter((s) => s != null);
    return {
      rows: result,
      summary: {
        lapNumber: lapMeta.lapNumber,
        lapTime: lapMeta.lapTime,
        sector1S: lapMeta.sector1S,
        sector2S: lapMeta.sector2S,
        sector3S: lapMeta.sector3S,
        compound: lapMeta.compound,
        topSpeed: speeds.length ? Math.max(...speeds) : 0,
        avgSpeed: speeds.length
          ? Math.round((speeds.reduce((a, b) => a + b, 0) / speeds.length) * 10) / 10
          : 0,
        points: result.length,
      },
    };
  }
  const rows = Array.isArray(result?.data) ? result.data : [];
  const { data: _d, ...summary } = result ?? {};
  return { rows, summary };
}

const PANELS = {
  telemetry:  { label: "Live Telemetry",      component: TelemetryPanel },
  comparison: { label: "Driver Comparison",   component: DriverComparisonPanel },
  tyres:      { label: "Tyre Analysis",       component: TyreAnalysisPanel },
  strategy:   { label: "Strategy Simulation", component: StrategyPanel },
  evolution:  { label: "Track Evolution",     component: TrackEvolutionPanel },
};

export default function App() {
  const [onboardingComplete, setOnboardingComplete] = useState(() => {
    try {
      return localStorage.getItem("pitwall_onboarding_complete") === "true";
    } catch {
      return false;
    }
  });
  const [year, setYear]           = useState("2024");
  const [gp, setGp]               = useState("");
  const [gpList, setGpList]       = useState([]);
  const [gpLoading, setGpLoading] = useState(false);
  const [session, setSession]     = useState("Q");
  const [driver, setDriver]       = useState("VER");

  // Lap list state
  const [lapList, setLapList]         = useState([]);   // [{lapNumber, lapTime, isFastest, ...}]
  const [selectedLap, setSelectedLap] = useState("fastest");
  const [lapLoading, setLapLoading]   = useState(false);

  // Telemetry data + lap summary
  const [data, setData]           = useState([]);
  const [lapSummary, setLapSummary] = useState(null);
  const [loading, setLoading]     = useState(false);

  const [activePanel, setActivePanel] = useState("telemetry");

  // Fetch GP schedule whenever year changes
  useEffect(() => {
    let cancelled = false;
    setGpLoading(true);

    fetchSchedule({ year })
      .then((scheduleData) => {
        if (cancelled) return;
        const names = Array.isArray(scheduleData)
          ? scheduleData
          : Array.isArray(scheduleData?.data)
            ? scheduleData.data
            : [];

        setGpList(names);
        setGp((prev) => names.includes(prev) ? prev : (names[0] ?? ""));
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("[App] Schedule fetch error:", err);
        setGpList([]);
        setGp("");
      })
      .finally(() => { if (!cancelled) setGpLoading(false); });

    return () => { cancelled = true; };
  }, [year]);

  // Fetches telemetry for a given lap and updates state.
  // Does NOT manage loading state, expects caller to do it.
  const fetchAndSetTelemetry = useCallback(async (lap, lapsSource) => {
    const num = verstappenDriverNumber(year);
    try {
      const result = await fetchLapTelemetry({ driver: num, year, gp, session, lap });
      const { rows, summary } = parseLapTelemetry(result, findLapMeta(lapsSource, lap));
      setData(rows);
      setLapSummary(summary);
      console.log(`[App] lap=${lap} points=${rows.length}`, summary);
    } catch (err) {
      console.error(`[App] Telemetry fetch error for lap ${lap}:`, err);
      setData([]);
      setLapSummary(null);
      // Re-throw so caller can know about it if needed
      throw err;
    }
  }, [year, gp, session]); // Dependencies for the fetch call

  // Fetch lap list + telemetry for the selected lap
  // Called when Load button is clicked OR when selectedLap changes (after initial load)
  const loadLapsAndTelemetry = useCallback(async (lapOverride) => {
    if (!gp) return;
    const lapToLoad = lapOverride ?? selectedLap;

    setLoading(true);
    setLapLoading(true);

    try {
      const num = verstappenDriverNumber(year);
      // 1. Fetch lap list (lightweight — no telemetry)
      const lapData = await fetchLaps({ driver: num, year, gp, session });
      // With the apiFetch fix, the full object is returned.
      // The lap list is expected to be nested under a 'data' property.
      const laps = lapData?.data?.laps ?? lapData?.laps ?? [];
      setLapList(laps);

      // 2. Fetch telemetry for the selected lap
      await fetchAndSetTelemetry(lapToLoad, laps);
    } catch (err) {
      console.error("[App] load error:", err);
      setLapList([]); // Also clear lap list on full load failure
    } finally {
      setLoading(false);
      setLapLoading(false);
    }
  }, [gp, year, session, selectedLap, fetchAndSetTelemetry]);

  // Re-fetch telemetry when the user picks a different lap (lap list already loaded)
  const handleLapChange = useCallback(async (lap) => {
    setSelectedLap(lap);
    if (!gp || lapList.length === 0) return;
    setLoading(true);
    try {
      await fetchAndSetTelemetry(lap, lapList);
    } catch (err) {
      // Error is already logged by the helper
    } finally {
      setLoading(false);
    }
  }, [gp, lapList, fetchAndSetTelemetry]);

  const sessionObj = { year: parseInt(year, 10), gp, session, driver };
  const ActiveComponent = PANELS[activePanel]?.component ?? TelemetryPanel;

  if (!onboardingComplete) {
    return <OnboardingSlider onComplete={() => setOnboardingComplete(true)} />;
  }

  return (
    <div className="flex min-h-screen transition-colors duration-300
      dark:bg-[radial-gradient(circle_at_top_left,rgba(232,0,45,0.14),transparent_34%),linear-gradient(135deg,#04070d_0%,#080d18_45%,#05080f_100%)]
      bg-[radial-gradient(circle_at_top_left,rgba(232,0,45,0.08),transparent_32%),linear-gradient(135deg,#f8fafc_0%,#eef2f7_48%,#e2e8f0_100%)]">
      <Sidebar active={activePanel} onSelect={setActivePanel} />

      <div className="flex flex-col flex-1 min-w-0 min-h-screen">
        <SessionHeader
          year={year}           onYearChange={setYear}
          gp={gp}               onGpChange={setGp}
          gpList={gpList}       gpLoading={gpLoading}
          session={session}     onSessionChange={setSession}
          driver={driver}       onDriverChange={setDriver}
          lapList={lapList}
          selectedLap={selectedLap}
          onLapChange={handleLapChange}
          lapLoading={lapLoading}
          onFetch={() => loadLapsAndTelemetry("fastest")}
          loading={loading}
          dataPoints={data.length}
        />

        <div className="px-4 sm:px-6 py-4 shrink-0 transition-all duration-300
          dark:border-b dark:border-[#20283a] dark:bg-[#070b14]/88
          border-b border-slate-200 bg-white/85 backdrop-blur">
          <div className="flex items-center gap-3">
            <span className="h-6 w-1 rounded-full bg-[#e8002d] shadow-[0_0_18px_rgba(232,0,45,0.55)]" />
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-[#e8002d]">
                Pitwall Module
              </p>
              <h1 className="text-sm sm:text-base font-black uppercase tracking-widest dark:text-[#e8eaf0] text-slate-800">
                {PANELS[activePanel]?.label}
              </h1>
            </div>
          </div>
        </div>

        <main className="flex-1 p-3 sm:p-4 lg:p-6">
          <ActiveComponent
            data={data}
            session={sessionObj}
            lapSummary={lapSummary}
          />
        </main>
      </div>
    </div>
  );
}
