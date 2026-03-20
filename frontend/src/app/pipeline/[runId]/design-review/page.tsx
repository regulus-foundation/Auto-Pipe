"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Markdown from "@/components/Markdown";
import { SkeletonPage } from "@/components/Skeleton";

export default function DesignReview() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`/api/pipeline/${runId}/state`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => { if (!d.state) throw new Error(); setData(d); })
      .catch(() => router.replace("/pipeline"));
  }, [runId, router]);

  if (!data) return <SkeletonPage />;

  const state = data.state || {};
  const errors = state.errors || [];

  async function handleApprove() {
    setLoading(true);
    await fetch(`/api/pipeline/${runId}/approve-design`, { method: "POST" });
    router.push(`/pipeline/${runId}/running`);
  }

  async function handleReject() {
    setLoading(true);
    await fetch(`/api/pipeline/${runId}/reject-design`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback }),
    });
    router.push(`/pipeline/${runId}/running`);
  }

  return (
    <div className="max-w-5xl animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Design Review
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>
          Project: <strong style={{ color: "var(--text-secondary)" }}>{state.project_name || ""}</strong>
        </p>
      </div>

      <div className="rounded-lg p-6 mb-6" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
        <Markdown content={state.design_spec || ""} />
      </div>

      {errors.length > 0 && (
        <div className="rounded-lg p-4 mb-6" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <h4 className="text-sm font-semibold mb-2" style={{ color: "#F87171" }}>Errors</h4>
          {errors.map((e: string, i: number) => (
            <div key={i} className="text-sm" style={{ color: "#FCA5A5" }}>{e}</div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleApprove}
          disabled={loading}
          className="px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 disabled:opacity-40"
          style={{ background: "var(--text-primary)", color: "var(--bg-base)", height: "36px" }}
        >
          {loading ? "Starting..." : "Approve → Start Development"}
        </button>

        <div className="flex gap-2">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Feedback (optional)"
            className="px-3 py-2 rounded-md text-sm outline-none transition-colors duration-150 focus-ring"
            style={{
              background: "var(--bg-base)",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              height: "36px",
              width: "256px",
            }}
          />
          <button
            onClick={handleReject}
            disabled={loading}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 disabled:opacity-40"
            style={{ background: "transparent", border: "1px solid var(--border-default)", color: "var(--text-secondary)", height: "36px" }}
          >
            Request Changes
          </button>
        </div>

        <a href="/pipeline" className="px-3 py-2 text-sm transition-colors duration-150 ml-1" style={{ color: "var(--text-tertiary)" }}>
          Cancel
        </a>
      </div>
    </div>
  );
}
