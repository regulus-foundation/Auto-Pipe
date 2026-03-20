"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useSSE } from "@/lib/useSSE";
import LogViewer from "@/components/LogViewer";
import ProgressIndicator from "@/components/ProgressIndicator";

export default function PipelineRunning() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const { logs, status, messages, phase, error } = useSSE(`/api/pipeline/${runId}/stream`);

  useEffect(() => {
    if (phase?.redirect) {
      router.push(phase.redirect);
    }
  }, [phase, router]);

  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-semibold mb-1" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
        Pipeline
      </h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-tertiary)" }}>Running...</p>

      <ProgressIndicator
        step={status.step || "Starting..."}
        node={status.node}
        progress={status.progress}
      />

      {messages.length > 0 && (
        <div className="rounded-lg p-3 mb-4 text-sm space-y-1"
             style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)" }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ color: "#60A5FA" }}>{msg}</div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg p-4 mb-4"
             style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <div className="text-sm" style={{ color: "#F87171" }}>{error}</div>
        </div>
      )}

      <LogViewer logs={logs} />
    </div>
  );
}
