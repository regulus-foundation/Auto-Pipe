interface MetricCardProps {
  label: string;
  value: string | number;
  color?: string;
}

export default function MetricCard({ label, value, color = "var(--accent-primary)" }: MetricCardProps) {
  return (
    <div
      className="rounded-lg p-4 transition-all duration-150 animate-fade-in"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--border-strong)"}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--border-default)"}
    >
      <div
        className="text-[11px] font-medium uppercase mb-1.5"
        style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}
      >
        {label}
      </div>
      <div className="text-2xl font-semibold" style={{ color, letterSpacing: "-0.02em" }}>
        {value}
      </div>
    </div>
  );
}
