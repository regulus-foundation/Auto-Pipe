"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface RunSummary {
  run_id: string;
  run_type: string;
  phase: string;
  project_name: string;
  error: string | null;
  created_at: string;
  updated_at: string;
  queue_position?: number;
}

interface LogFile {
  name: string;
  size: number;
  modified: number;
}

const PAGE_SIZE = 10;

const PHASE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  queued: { label: "Queued", color: "#A78BFA", bg: "rgba(167,139,250,0.15)" },
  analyzing: { label: "Analyzing", color: "#60A5FA", bg: "rgba(59,130,246,0.15)" },
  review: { label: "Review", color: "#FBBF24", bg: "rgba(245,158,11,0.15)" },
  done: { label: "Done", color: "#4ADE80", bg: "rgba(34,197,94,0.15)" },
  running_design: { label: "Design", color: "#60A5FA", bg: "rgba(59,130,246,0.15)" },
  design_review: { label: "Design Review", color: "#FBBF24", bg: "rgba(245,158,11,0.15)" },
  running_main: { label: "Running", color: "#60A5FA", bg: "rgba(59,130,246,0.15)" },
  code_review: { label: "Code Review", color: "#FBBF24", bg: "rgba(245,158,11,0.15)" },
  error: { label: "Error", color: "#F87171", bg: "rgba(239,68,68,0.15)" },
};

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsPage, setRunsPage] = useState(0);
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogFile[]>([]);
  const [logsPage, setLogsPage] = useState(0);
  const [logContent, setLogContent] = useState<string | null>(null);
  const [logName, setLogName] = useState("");

  useEffect(() => {
    fetch("/api/runs").then((r) => r.json()).then((d) => setRuns(d.runs || [])).catch(() => {});
    fetch("/api/bootstrap/projects").then((r) => r.json()).then((d) => {
      setProjects((d.projects || []).map((p: any) => p.name));
    }).catch(() => {});
  }, []);

  function loadLogs(projectName: string) {
    setSelectedProject(projectName);
    setLogContent(null);
    setLogsPage(0);
    fetch(`/api/projects/${projectName}/logs`)
      .then((r) => r.json())
      .then((d) => setLogs(d.logs || []))
      .catch(() => setLogs([]));
  }

  function openLog(projectName: string, name: string) {
    setLogName(name);
    fetch(`/api/projects/${projectName}/logs/${name}`)
      .then((r) => r.json())
      .then((d) => setLogContent(d.content || ""))
      .catch(() => setLogContent("Failed to load log."));
  }

  function getRunLink(run: RunSummary): string {
    const base = run.run_type === "bootstrap" ? "/bootstrap" : "/pipeline";
    if (run.phase === "done") return `${base}/${run.run_id}/done`;
    if (run.phase === "review") return `${base}/${run.run_id}/review`;
    if (run.phase === "design_review") return `${base}/${run.run_id}/design-review`;
    if (run.phase === "code_review") return `${base}/${run.run_id}/code-review`;
    if (["analyzing", "running_design", "running_main"].includes(run.phase)) return `${base}/${run.run_id}/running`;
    return base;
  }

  // Pagination
  const runsTotal = Math.ceil(runs.length / PAGE_SIZE);
  const pagedRuns = runs.slice(runsPage * PAGE_SIZE, (runsPage + 1) * PAGE_SIZE);
  const logsTotal = Math.ceil(logs.length / PAGE_SIZE);
  const pagedLogs = logs.slice(logsPage * PAGE_SIZE, (logsPage + 1) * PAGE_SIZE);

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-semibold mb-1" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
        History
      </h2>
      <p className="text-sm mb-8" style={{ color: "var(--text-tertiary)" }}>
        Execution history and project logs
      </p>

      {/* Active Runs */}
      <div className="mb-8">
        <h3 className="text-[11px] font-medium uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
          Runs ({runs.length})
        </h3>

        {runs.length === 0 ? (
          <div className="rounded-lg p-6 text-center text-sm" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", color: "var(--text-tertiary)" }}>
            No runs yet. Start from Bootstrap or Pipeline.
          </div>
        ) : (
          <>
            <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--border-default)" }}>
              <table className="w-full text-[13px]">
                <thead>
                  <tr style={{ background: "var(--bg-surface)" }}>
                    {["Project", "Type", "Status", "Started", "ID"].map((h) => (
                      <th key={h} className="text-left px-4 py-2.5 font-medium"
                          style={{ color: "var(--text-tertiary)", borderBottom: "1px solid var(--border-default)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pagedRuns.map((run) => {
                    const phase = PHASE_LABELS[run.phase] || { label: run.phase, color: "var(--text-tertiary)", bg: "var(--bg-overlay)" };
                    return (
                      <tr key={run.run_id}
                          className="transition-colors duration-100"
                          style={{ borderBottom: "1px solid var(--border-subtle)" }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
                        <td className="px-4 py-3">
                          <Link href={getRunLink(run)} className="font-medium hover:underline" style={{ color: "var(--text-primary)" }}>
                            {run.project_name || "—"}
                          </Link>
                        </td>
                        <td className="px-4 py-3" style={{ color: "var(--text-secondary)" }}>{run.run_type}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                                style={{ background: phase.bg, color: phase.color }}>
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: phase.color }} />
                            {phase.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                          {new Date(run.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                          {run.run_id}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Runs Pagination */}
            {runsTotal > 1 && (
              <Pagination current={runsPage} total={runsTotal} onChange={setRunsPage} />
            )}
          </>
        )}
      </div>

      {/* Project Logs */}
      <div>
        <h3 className="text-[11px] font-medium uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
          Project Logs
        </h3>

        <div className="flex gap-2 mb-4 flex-wrap">
          {projects.map((name) => (
            <button
              key={name}
              onClick={() => loadLogs(name)}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150"
              style={{
                background: selectedProject === name ? "var(--accent-primary)" : "var(--bg-surface)",
                color: selectedProject === name ? "#fff" : "var(--text-secondary)",
                border: `1px solid ${selectedProject === name ? "var(--accent-primary)" : "var(--border-default)"}`,
              }}
            >
              {name}
            </button>
          ))}
          {projects.length === 0 && (
            <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>No projects found.</p>
          )}
        </div>

        {selectedProject && (
          <>
            <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--border-default)" }}>
              {pagedLogs.length === 0 ? (
                <div className="p-4 text-sm text-center" style={{ color: "var(--text-tertiary)", background: "var(--bg-surface)" }}>
                  No logs for {selectedProject}
                </div>
              ) : (
                <div style={{ background: "var(--bg-surface)" }}>
                  {pagedLogs.map((log) => (
                    <button
                      key={log.name}
                      onClick={() => openLog(selectedProject, log.name)}
                      className="w-full flex items-center justify-between px-4 py-2.5 text-left transition-colors duration-100"
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        background: logName === log.name ? "var(--bg-raised)" : "transparent",
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-raised)"}
                      onMouseLeave={(e) => e.currentTarget.style.background = logName === log.name ? "var(--bg-raised)" : "transparent"}
                    >
                      <span className="text-[13px]" style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                        {log.name}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                          {new Date(log.modified * 1000).toLocaleString()}
                        </span>
                        <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                          {(log.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Logs Pagination */}
            {logsTotal > 1 && (
              <Pagination current={logsPage} total={logsTotal} onChange={setLogsPage} />
            )}
          </>
        )}

        {logContent !== null && (
          <div className="mt-4 rounded-lg overflow-hidden log-container" style={{ border: "1px solid var(--border-subtle)" }}>
            <div className="px-4 py-2 text-xs font-medium flex justify-between items-center"
                 style={{ background: "var(--bg-raised)", color: "var(--text-secondary)", borderBottom: "1px solid var(--border-subtle)" }}>
              <span style={{ fontFamily: "var(--font-mono)" }}>{logName}</span>
              <button onClick={() => setLogContent(null)} className="hover:opacity-70" style={{ color: "var(--text-tertiary)" }}>
                Close
              </button>
            </div>
            <pre className="p-4 text-xs overflow-auto max-h-[480px]"
                 style={{ background: "#0A0A0C", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", lineHeight: "1.7" }}>
              {logContent}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}


function Pagination({ current, total, onChange }: { current: number; total: number; onChange: (p: number) => void }) {
  return (
    <div className="flex items-center justify-between mt-3 px-1">
      <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>
        Page {current + 1} of {total}
      </span>
      <div className="flex gap-1">
        <button
          onClick={() => onChange(Math.max(0, current - 1))}
          disabled={current === 0}
          className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150 disabled:opacity-30"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", color: "var(--text-secondary)" }}
        >
          Prev
        </button>
        {Array.from({ length: Math.min(total, 5) }, (_, i) => {
          // Show pages around current
          let page: number;
          if (total <= 5) {
            page = i;
          } else if (current < 3) {
            page = i;
          } else if (current > total - 4) {
            page = total - 5 + i;
          } else {
            page = current - 2 + i;
          }
          return (
            <button
              key={page}
              onClick={() => onChange(page)}
              className="w-8 h-8 rounded-md text-xs font-medium transition-colors duration-150"
              style={{
                background: page === current ? "var(--accent-primary)" : "var(--bg-surface)",
                color: page === current ? "#fff" : "var(--text-secondary)",
                border: `1px solid ${page === current ? "var(--accent-primary)" : "var(--border-default)"}`,
              }}
            >
              {page + 1}
            </button>
          );
        })}
        <button
          onClick={() => onChange(Math.min(total - 1, current + 1))}
          disabled={current === total - 1}
          className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150 disabled:opacity-30"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", color: "var(--text-secondary)" }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
