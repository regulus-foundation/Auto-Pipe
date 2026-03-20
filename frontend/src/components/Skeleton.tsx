interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
}

export default function Skeleton({ className = "", width, height = "16px" }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width: width || "100%", height, borderRadius: "var(--radius-md)" }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg p-5 space-y-3" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
      <Skeleton height="14px" width="40%" />
      <Skeleton height="28px" width="60%" />
    </div>
  );
}

export function SkeletonPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="space-y-2">
        <Skeleton height="28px" width="200px" />
        <Skeleton height="14px" width="300px" />
      </div>
      <div className="grid grid-cols-5 gap-3">
        {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
      <div className="rounded-lg p-6 space-y-4" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
        <Skeleton height="14px" width="30%" />
        <Skeleton height="14px" width="80%" />
        <Skeleton height="14px" width="65%" />
        <Skeleton height="14px" width="70%" />
      </div>
    </div>
  );
}
