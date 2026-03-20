"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { SkeletonPage } from "@/components/Skeleton";

export default function BootstrapDone() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch(`/api/bootstrap/${runId}/state`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => { if (!d.state) throw new Error(); setData(d); })
      .catch(() => router.replace("/bootstrap"));
  }, [runId, router]);

  if (!data) return <SkeletonPage />;

  const genResult = data.state?.gen_result || {};
  const scan = data.state?.scan_result || {};
  const projectName = scan.project?.name || "unknown";

  return (
    <div className="max-w-4xl animate-fade-in">
      {/* Success Banner */}
      <div className="rounded-lg p-5 mb-6" style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)" }}>
        <h2 className="text-xl font-semibold" style={{ color: "#4ADE80", letterSpacing: "-0.02em" }}>
          {projectName} Bootstrap Complete!
        </h2>
      </div>

      {/* Generated Files */}
      <div className="rounded-lg p-6 mb-6" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
        <h3 className="font-semibold mb-3" style={{ color: "var(--text-primary)" }}>Generated Files</h3>
        <code className="block px-3 py-2 rounded-md text-sm mb-4"
              style={{ background: "var(--bg-base)", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
          {genResult.output_dir || ""}
        </code>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h4 className="text-[11px] font-medium uppercase mb-2" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
              Config Files
            </h4>
            <ul className="text-sm space-y-1" style={{ color: "var(--text-secondary)" }}>
              <li><code style={{ fontFamily: "var(--font-mono)" }}>project_analysis.yaml</code></li>
              <li><code style={{ fontFamily: "var(--font-mono)" }}>pipeline.yaml</code></li>
            </ul>
          </div>
          <div>
            <h4 className="text-[11px] font-medium uppercase mb-2" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
              Prompt Templates
            </h4>
            <ul className="text-sm space-y-1" style={{ color: "var(--text-secondary)" }}>
              {(genResult.files?.prompts || []).map((p: string) => (
                <li key={p}><code style={{ fontFamily: "var(--font-mono)" }}>prompts/{p}</code></li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Link href="/bootstrap"
              className="px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 inline-flex items-center"
              style={{ background: "var(--text-primary)", color: "var(--bg-base)", height: "36px" }}>
          Analyze Another Project
        </Link>
        <Link href={`/bootstrap/${runId}/review`}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 inline-flex items-center"
              style={{ background: "transparent", border: "1px solid var(--border-default)", color: "var(--text-secondary)", height: "36px" }}>
          View Analysis Again
        </Link>
        <Link href="/pipeline"
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 inline-flex items-center"
              style={{ background: "rgba(34,197,94,0.15)", color: "#4ADE80", height: "36px" }}>
          Go to Pipeline
        </Link>
      </div>
    </div>
  );
}
