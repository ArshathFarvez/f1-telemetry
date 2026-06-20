import { useTheme } from "../../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <div className="flex items-center gap-1.5 sm:gap-2 rounded-full border px-2 py-1 transition-all duration-300
      dark:border-[#263147] dark:bg-[#0b1220]/90
      border-slate-200 bg-white/90 shadow-[0_8px_22px_rgba(15,23,42,0.06)]">
      <span className={`text-[8px] sm:text-[9px] font-black uppercase tracking-widest transition-colors duration-300 ${isDark ? "text-[#e8eaf0]" : "text-slate-400"}`}>
        Dark
      </span>
      <button
        type="button"
        onClick={toggleTheme}
        aria-label="Toggle color theme"
        aria-pressed={isDark}
        className="group relative h-6 w-12 shrink-0 overflow-hidden rounded-full border transition-all duration-300 ease-out
          dark:border-[#33415f] dark:bg-[#080d17] dark:hover:border-[#e8002d]/60 dark:hover:shadow-[0_0_18px_rgba(232,0,45,0.2)]
          border-slate-200 bg-slate-100 hover:border-[#e8002d]/50 hover:bg-white hover:shadow-[0_8px_20px_rgba(15,23,42,0.1)]
          focus:outline-none focus:ring-2 focus:ring-[#e8002d]/40"
      >
        <span className="absolute inset-0 rounded-full bg-gradient-to-r from-[#e8002d]/20 via-transparent to-[#ffd700]/20 opacity-70 transition-opacity duration-300 group-hover:opacity-100" />
        <span
          className={[
            "absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-[#e8002d] shadow-[0_0_16px_rgba(232,0,45,0.4)] transition-transform duration-300 ease-out will-change-transform",
            isDark ? "translate-x-0" : "translate-x-6",
          ].join(" ")}
        />
      </button>
      <span className={`text-[8px] sm:text-[9px] font-black uppercase tracking-widest transition-colors duration-300 ${isDark ? "text-[#5a6a80]" : "text-slate-900"}`}>
        Light
      </span>
    </div>
  );
}
