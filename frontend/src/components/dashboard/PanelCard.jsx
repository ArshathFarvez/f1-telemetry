export default function PanelCard({ title, subtitle, accent = false, children, className = "" }) {
  return (
    <div
      className={[
        "relative rounded-lg overflow-hidden flex flex-col transition-all duration-300",
        "dark:bg-[#0d1422]/95 dark:border dark:border-[#263147] dark:shadow-[0_18px_48px_rgba(0,0,0,0.28)]",
        "bg-white border border-slate-200 shadow-[0_14px_34px_rgba(15,23,42,0.08)]",
        "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/50 dark:before:bg-white/10",
        accent ? "border-t-2 border-t-[#e8002d] dark:shadow-[0_18px_52px_rgba(232,0,45,0.08)]" : "",
        className,
      ].join(" ")}
    >
      {(title || subtitle) && (
        <div className="relative flex items-center justify-between px-4 py-3 shrink-0 dark:border-b dark:border-[#263147] border-b border-slate-100
          dark:bg-[#101827]/80 bg-slate-50/80">
          {accent && <span className="absolute left-4 top-0 h-px w-16 bg-[#e8002d] shadow-[0_0_14px_rgba(232,0,45,0.7)]" />}
          <div>
            {title && (
              <h2 className="text-xs font-black uppercase tracking-widest dark:text-[#e8eaf0] text-slate-800">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="text-[10px] mt-0.5 dark:text-[#7b879d] text-slate-500">{subtitle}</p>
            )}
          </div>
        </div>
      )}
      <div className="relative flex-1 min-h-0">{children}</div>
    </div>
  );
}
