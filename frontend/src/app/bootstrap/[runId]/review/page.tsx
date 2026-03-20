"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import MetricCard from "@/components/MetricCard";
import Tabs from "@/components/Tabs";
import Markdown from "@/components/Markdown";
import { SkeletonPage } from "@/components/Skeleton";

export default function BootstrapReview() {
  const { runId } = useParams<{ runId: string }>();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    fetch(`/api/bootstrap/${runId}/state`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then((d) => {
        if (!d.state) throw new Error("No state");
        setData(d);
      })
      .catch(() => router.replace("/bootstrap"));
  }, [runId, router]);

  if (!data) return <SkeletonPage />;

  const scan = data.state?.scan_result || {};
  const deep = data.state?.deep_analysis || {};
  const deepSteps = deep.steps || {};
  const project = scan.project || {};
  const structure = scan.structure || {};
  const languages = scan.languages || {};
  const frameworks = scan.frameworks || [];
  const build = scan.build || {};
  const infra = scan.infrastructure || {};
  const testing = scan.testing || {};
  const conventions = scan.conventions || {};
  const breakdown = languages.breakdown || {};
  const total = Object.values(breakdown).reduce((a: number, b: any) => a + (b as number), 0) as number;

  async function handleApprove() {
    setApproving(true);
    await fetch(`/api/bootstrap/${runId}/approve`, { method: "POST" });
    router.push(`/bootstrap/${runId}/done`);
  }

  const tabs = [
    {
      id: "summary", label: "Summary",
      content: (
        <div>
          {deepSteps.summary && (
            <div className="flex gap-6 text-xs mb-5 pb-3 border-b" style={{ borderColor: "var(--border-default)", color: "var(--text-tertiary)" }}>
              <span>Files: <strong style={{ color: "var(--text-secondary)" }}>{deep.files_analyzed || 0}</strong></span>
              <span>Duration: <strong style={{ color: "var(--text-secondary)" }}>{(deep.total_duration || 0).toFixed(1)}s</strong></span>
              <span>Tokens: <strong style={{ color: "var(--text-secondary)" }}>{(deep.total_tokens || 0).toLocaleString()}</strong></span>
            </div>
          )}
          <Markdown content={deepSteps.summary || ""} />
        </div>
      ),
    },
    { id: "deps", label: "Dependencies", content: <Markdown content={deepSteps.dependencies || ""} /> },
    { id: "arch", label: "Architecture", content: <Markdown content={deepSteps.architecture || ""} /> },
    { id: "testing", label: "Testing", content: <Markdown content={deepSteps.testing || ""} /> },
    {
      id: "overview", label: "Overview",
      content: (
        <div className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Languages */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>Languages</h4>
              {Object.entries(breakdown).sort(([, a], [, b]) => (b as number) - (a as number)).map(([lang, count]) => {
                const pct = Math.round(((count as number) / (total || 1)) * 100);
                return (
                  <div key={lang} className="mb-2">
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="font-medium" style={{ color: "var(--text-secondary)" }}>{lang}</span>
                      <span style={{ color: "var(--text-tertiary)" }}>{count as number} ({pct}%)</span>
                    </div>
                    <div className="w-full rounded-full h-1" style={{ background: "var(--bg-elevated)" }}>
                      <div className="h-1 rounded-full" style={{ width: `${pct}%`, background: "var(--accent-blue)" }} />
                    </div>
                  </div>
                );
              })}
            </div>
            {/* Frameworks */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>Frameworks</h4>
              {frameworks.map((fw: any) => (
                <div key={fw.name} className="flex items-center gap-3 rounded-md px-3 py-2 mb-2 border"
                     style={{ background: "rgba(34,197,94,0.08)", borderColor: "rgba(34,197,94,0.2)" }}>
                  <span className="text-sm font-medium" style={{ color: "#4ADE80" }}>{fw.name}</span>
                  <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>({fw.language})</span>
                </div>
              ))}
              {frameworks.length === 0 && <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>No frameworks detected.</p>}
            </div>
          </div>

          <div className="border-t" style={{ borderColor: "var(--border-default)" }} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>Structure</h4>
              <div className="space-y-2 text-sm">
                <div className="flex gap-2">
                  <span style={{ color: "var(--text-tertiary)" }}>Type:</span>
                  <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ background: "rgba(59,130,246,0.15)", color: "#60A5FA" }}>
                    {structure.type || "single"}
                  </span>
                </div>
                {conventions.architecture && (
                  <div className="flex gap-2">
                    <span style={{ color: "var(--text-tertiary)" }}>Arch:</span>
                    <span style={{ color: "var(--text-secondary)" }}>{conventions.architecture}</span>
                  </div>
                )}
              </div>
              {structure.directories?.length > 0 && (
                <pre className="mt-3 rounded-md border p-2 text-xs max-h-40 overflow-auto"
                     style={{ background: "var(--bg-root)", borderColor: "var(--border-default)", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                  {structure.directories.slice(0, 20).map((d: string) => `${d}/`).join("\n")}
                </pre>
              )}
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>Build & Infra</h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>Build: </span>
                  <span className="font-medium" style={{ color: "var(--text-secondary)" }}>{build.tool || "N/A"}</span>
                </div>
                {Object.entries(build.commands || {}).map(([name, cmd]) => (
                  <div key={name} className="rounded-md border px-2 py-1 text-xs"
                       style={{ background: "var(--bg-root)", borderColor: "var(--border-default)", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                    <span style={{ color: "var(--text-tertiary)" }}>{name}:</span> {cmd as string}
                  </div>
                ))}
                <div className="flex flex-wrap gap-2 mt-2">
                  {["docker", "docker_compose"].map((key) => (
                    <span key={key} className="px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            background: infra[key] ? "rgba(34,197,94,0.15)" : "var(--bg-elevated)",
                            color: infra[key] ? "#4ADE80" : "var(--text-tertiary)",
                          }}>
                      {key.replace("_", " ")} {infra[key] ? "Yes" : "No"}
                    </span>
                  ))}
                  {infra.ci_cd && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{ background: "rgba(59,130,246,0.15)", color: "#60A5FA" }}>
                      CI: {infra.ci_cd}
                    </span>
                  )}
                </div>
                {testing.frameworks?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {testing.frameworks.map((fw: string) => (
                      <span key={fw} className="px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{ background: "rgba(34,197,94,0.15)", color: "#4ADE80" }}>{fw}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "yaml", label: "Raw Data",
      content: (
        <pre className="rounded-lg border p-4 text-xs overflow-auto max-h-[32rem] leading-relaxed"
             style={{ background: "var(--bg-root)", borderColor: "var(--border-default)", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
          {JSON.stringify(scan, null, 2)}
        </pre>
      ),
    },
  ];

  return (
    <div className="max-w-6xl">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
          {project.name || "unknown"}
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>{project.path || ""}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <MetricCard label="Source Files" value={structure.source_files || 0} color="var(--accent-blue)" />
        <MetricCard label="Test Files" value={structure.test_files || 0} color="var(--accent-green)" />
        <MetricCard label="Lines of Code" value={(structure.lines_of_code || 0).toLocaleString()} color="var(--accent-purple)" />
        <MetricCard label="Total Files" value={structure.total_files || 0} color="var(--accent-amber)" />
        <MetricCard label="Analyzed" value={deep.files_analyzed || 0} color="var(--accent-red)" />
      </div>

      <Tabs tabs={tabs} defaultTab="summary" />

      {/* Actions */}
      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleApprove}
          disabled={approving}
          className="px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 disabled:opacity-40"
          style={{ background: "var(--text-primary)", color: "var(--bg-root)", height: "36px" }}
        >
          {approving ? "Generating..." : "Approve → Generate Config"}
        </button>
        <a href="/bootstrap"
           className="px-4 py-2 rounded-md border text-sm font-medium transition-colors duration-150"
           style={{ borderColor: "var(--border-default)", color: "var(--text-secondary)", height: "36px", lineHeight: "20px" }}>
          Re-analyze
        </a>
        <a href="/bootstrap" className="px-3 py-2 text-sm transition-colors duration-150 ml-1"
           style={{ color: "var(--text-tertiary)" }}>
          Cancel
        </a>
      </div>
    </div>
  );
}
