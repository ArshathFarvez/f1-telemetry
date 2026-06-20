import { useTheme } from "../context/ThemeContext";

/**
 * Returns Recharts-compatible color tokens that react to the active theme.
 * Use these for grid stroke, axis tick fill, and tooltip styles.
 */
export function useChartTheme() {
  const { theme } = useTheme();
  const dark = theme === "dark";

  return {
    grid:        dark ? "#1c2333" : "#e2e8f0",
    axisText:    dark ? "#5a6a80" : "#64748b",
    tooltipBg:   dark ? "#0f1623" : "#ffffff",
    tooltipBorder: dark ? "#1c2333" : "#e2e8f0",
    tooltipText: dark ? "#e8eaf0" : "#0f172a",
  };
}
