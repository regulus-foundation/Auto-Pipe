"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useSSE } from "@/lib/useSSE";
import LogViewer from "@/components/LogViewer";
import ProgressIndicator from "@/components/ProgressIndicator";

export default function BootstrapRunning() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const { logs, status, phase, error } = useSSE(`/api/bootstrap/${runId}/stream`);

  useEffect(() => {
    if (phase?.redirect) router.push(phase.redirect);
  }, [phase, router]);

  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-semibold tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
        Bootstrap
      </h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-tertiary)" }}>Analyzing project...</p>

      <ProgressIndicator step={status.step || "Starting..."} node={status.node} progress={status.progress} />

      {error && (
        <div className="rounded-lg p-4 mb-4 border" style={{ background: "rgba(239,68,68,0.1)", borderColor: "rgba(239,68,68,0.2)" }}>
          <div className="text-sm" style={{ color: "#F87171" }}>{error}</div>
        </div>
      )}

      <LogViewer logs={logs} />
    </div>
  );
}
