interface ProgressIndicatorProps {
  step: string;
  progress?: number;
  node?: string;
}

export default function ProgressIndicator({ step, progress = 5, node }: ProgressIndicatorProps) {
  const label = node ? `${node} — ${step}` : step;

  return (
    <div
      className="rounded-lg p-4 mb-4"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-center gap-3 mb-3">
        <div
          className="animate-spin h-4 w-4 rounded-full"
          style={{ border: "2px solid var(--accent-primary)", borderTopColor: "transparent" }}
        />
        <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
          {label || "Starting..."}
        </span>
      </div>
      <div className="w-full h-[3px] rounded-sm" style={{ background: "var(--bg-overlay)" }}>
        <div
          className="h-[3px] rounded-sm transition-all duration-500"
          style={{ width: `${progress}%`, background: "var(--accent-primary)" }}
        />
      </div>
    </div>
  );
}
