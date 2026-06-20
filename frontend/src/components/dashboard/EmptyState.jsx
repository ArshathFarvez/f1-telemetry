export default function EmptyState({ icon = null, message = "No data loaded", hint }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 py-12 text-center px-4">
      {icon && <span className="text-4xl opacity-30">{icon}</span>}
      <p className="text-sm font-medium dark:text-[#5a6a80] text-slate-400">{message}</p>
      {hint && <p className="text-xs dark:text-[#5a6a80]/60 text-slate-300">{hint}</p>}
    </div>
  );
}
