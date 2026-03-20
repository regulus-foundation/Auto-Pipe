"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Project {
  name: string;
  has_pipeline: boolean;
}

export default function BootstrapPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/bootstrap/projects")
      .then((r) => r.json())
      .then((d) => setProjects(d.projects || []))
      .catch(() => {});
  }, []);

  async function handleLoadExisting(name: string) {
    setLoading(true);
    const res = await fetch("/api/bootstrap/load-existing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_name: name }),
    });
    const data = await res.json();
    router.push(`/bootstrap/${data.run_id}/review`);
  }

  async function handleStartAnalysis(e: React.FormEvent) {
    e.preventDefault();
    if (!path.trim()) return;
    setLoading(true);
    const res = await fetch("/api/bootstrap/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_path: path.trim() }),
    });
    if (!res.ok) {
      setLoading(false);
      alert("Invalid path");
      return;
    }
    const data = await res.json();
    router.push(`/bootstrap/${data.run_id}/running`);
  }

  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-semibold tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
        Bootstrap
      </h2>
      <p className="text-sm mb-8" style={{ color: "var(--text-tertiary)" }}>
        Analyze a project and generate pipeline configuration
      </p>

      {projects.length > 0 && (
        <>
          <div className="mb-8">
            <h3 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>
              Existing Projects
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {projects.map((p) => (
                <button
                  key={p.name}
                  onClick={() => handleLoadExisting(p.name)}
                  disabled={loading}
                  className="px-4 py-3 rounded-lg border text-sm font-medium transition-all duration-150 text-left disabled:opacity-50"
                  style={{ background: "var(--bg-surface)", borderColor: "var(--border-default)", color: "var(--text-secondary)" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--text-tertiary)"; e.currentTarget.style.color = "var(--text-primary)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border-default)"; e.currentTarget.style.color = "var(--text-secondary)"; }}
                >
                  {p.name}
                  {p.has_pipeline && (
                    <span className="block text-xs mt-0.5" style={{ color: "var(--accent-green)" }}>configured</span>
                  )}
                </button>
              ))}
            </div>
          </div>
          <div className="mb-8 border-t" style={{ borderColor: "var(--border-default)" }} />
        </>
      )}

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--text-tertiary)" }}>
          New Analysis
        </h3>

        <details className="mb-4 rounded-lg border"
                 style={{ background: "var(--bg-surface)", borderColor: "var(--border-default)" }}>
          <summary className="px-4 py-3 cursor-pointer text-sm" style={{ color: "var(--text-tertiary)" }}>
            Pipeline Structure
          </summary>
          <pre className="px-4 pb-4 text-xs whitespace-pre-wrap"
               style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
{`scan_files (tool)       → File structure scan
analyze_deps (console)  → Dependencies & Build
analyze_arch (console)  → Architecture & Code patterns
analyze_tests (console) → Test strategy
analyze_summary (console) → Summary
[Human Review]          → Review results
generate_config (api)   → pipeline.yaml + prompts`}
          </pre>
        </details>

        <form onSubmit={handleStartAnalysis}>
          <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
            Project Path
          </label>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/Users/.../my-project"
            className="w-full px-3 py-2 rounded-md border text-sm mb-4 outline-none transition-colors duration-150 focus-ring"
            style={{
              background: "var(--bg-input)",
              borderColor: "var(--border-default)",
              color: "var(--text-primary)",
              height: "36px",
            }}
          />
          <button
            type="submit"
            disabled={loading || !path.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 disabled:opacity-40"
            style={{ background: "var(--text-primary)", color: "var(--bg-root)", height: "36px" }}
          >
            {loading ? "Starting..." : "Start Analysis"}
          </button>
        </form>
      </div>
    </div>
  );
}
