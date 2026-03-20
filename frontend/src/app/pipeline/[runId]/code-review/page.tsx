"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Tabs from "@/components/Tabs";
import Markdown from "@/components/Markdown";
import CodeViewer from "@/components/CodeViewer";
import { SkeletonPage } from "@/components/Skeleton";

export default function CodeReview() {
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
  const iteration = state.review_iteration || 0;

  async function handleApprove() {
    setLoading(true);
    await fetch(`/api/pipeline/${runId}/approve-review`, { method: "POST" });
    router.push(`/pipeline/${runId}/running`);
  }

  async function handleReject() {
    if (!feedback.trim()) return;
    setLoading(true);
    await fetch(`/api/pipeline/${runId}/reject-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback }),
    });
    router.push(`/pipeline/${runId}/running`);
  }

  const tabs = [
    { id: "merged", label: "Merged Review", content: <Markdown content={state.merged_review || ""} /> },
    { id: "quality", label: "Quality", content: <Markdown content={state.review_report || ""} /> },
    { id: "security", label: "Security", content: <Markdown content={state.security_report || ""} /> },
    { id: "code", label: "Source Code", content: <CodeViewer files={state.source_code || {}} /> },
  ];

  return (
    <div className="max-w-6xl animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Code Review
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>
          {state.project_name || ""}
          {iteration > 0 && ` — Iteration #${iteration}`}
        </p>
      </div>

      <div className="mb-6">
        <Tabs tabs={tabs} defaultTab="merged" />
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
          {loading ? "Processing..." : "Approve → Generate Docs"}
        </button>

        <div className="flex gap-2">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Feedback"
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
            disabled={loading || !feedback.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 disabled:opacity-40"
            style={{ background: "transparent", border: "1px solid var(--border-default)", color: "var(--text-secondary)", height: "36px" }}
          >
            Request Fixes
          </button>
        </div>

        <a href="/pipeline" className="px-3 py-2 text-sm transition-colors duration-150 ml-1" style={{ color: "var(--text-tertiary)" }}>
          Force Stop
        </a>
      </div>
    </div>
  );
}
