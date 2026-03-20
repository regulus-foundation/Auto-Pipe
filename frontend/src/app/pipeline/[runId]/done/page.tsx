"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import CodeViewer from "@/components/CodeViewer";
import { SkeletonPage } from "@/components/Skeleton";

export default function PipelineDone() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`/api/pipeline/${runId}/state`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => { if (!d.state) throw new Error(); setData(d); })
      .catch(() => router.replace("/pipeline"));
  }, [runId, router]);

  if (!data) return <SkeletonPage />;

  const state = data.state || {};
  const messages = state.messages || [];
  const errors = state.errors || [];
  const deliverables = state.deliverables || [];
  const sourceCode = state.source_code || {};

  return (
    <div className="max-w-5xl animate-fade-in">
      {/* Success Banner */}
      <div className="rounded-lg p-5 mb-6" style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)" }}>
        <h2 className="text-xl font-semibold" style={{ color: "#4ADE80", letterSpacing: "-0.02em" }}>
          {state.project_name || "unknown"} — Pipeline Complete
        </h2>
      </div>

      {/* Execution Log */}
      {messages.length > 0 && (
        <details className="rounded-lg mb-4" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
            Execution Log ({messages.length} entries)
          </summary>
          <div className="px-4 pb-4 max-h-60 overflow-auto text-xs space-y-0.5"
               style={{ fontFamily: "var(--font-mono)", color: "var(--text-tertiary)" }}>
            {messages.map((msg: string, i: number) => <div key={i}>{msg}</div>)}
          </div>
        </details>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <div className="rounded-lg p-4 mb-4" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
          <h4 className="text-sm font-semibold mb-2" style={{ color: "#F87171" }}>Errors</h4>
          {errors.map((e: string, i: number) => <div key={i} className="text-sm" style={{ color: "#FCA5A5" }}>{e}</div>)}
        </div>
      )}

      {/* Deliverables */}
      {deliverables.length > 0 && (
        <div className="rounded-lg p-5 mb-4" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
          <h3 className="text-[11px] font-medium uppercase mb-3" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
            Deliverables
          </h3>
          <ul className="space-y-1">
            {deliverables.map((d: string, i: number) => (
              <li key={i} className="text-sm flex items-center gap-2" style={{ color: "var(--text-secondary)" }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--status-success)" }} />{d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Source Code */}
      {Object.keys(sourceCode).length > 0 && (
        <div className="rounded-lg p-5 mb-6" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
          <h3 className="text-[11px] font-medium uppercase mb-3" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
            Generated Code ({Object.keys(sourceCode).length} files)
          </h3>
          <CodeViewer files={sourceCode} />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Link href="/pipeline"
              className="px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 inline-flex items-center"
              style={{ background: "var(--text-primary)", color: "var(--bg-base)", height: "36px" }}>
          New Requirements
        </Link>
        <Link href={`/pipeline/${runId}/code-review`}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 inline-flex items-center"
              style={{ background: "transparent", border: "1px solid var(--border-default)", color: "var(--text-secondary)", height: "36px" }}>
          View Review Again
        </Link>
      </div>
    </div>
  );
}
