"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/Toast";

interface Project {
  name: string;
  config: string;
}

interface QueueItem {
  run_id: string;
  position: number;
  phase: string;
}

export default function PipelinePage() {
  const router = useRouter();
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [requirements, setRequirements] = useState("");
  const [loading, setLoading] = useState(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);

  useEffect(() => {
    fetch("/api/bootstrap/configured-projects")
      .then((r) => r.json())
      .then((d) => {
        setProjects(d.projects || []);
        if (d.projects?.length > 0) setSelected(d.projects[0]);
      })
      .catch(() => {});
  }, []);

  // Load queue when project changes
  useEffect(() => {
    if (!selected) return;
    fetch(`/api/pipeline/queue/${selected.name}`)
      .then((r) => r.json())
      .then((d) => setQueue(d.queue || []))
      .catch(() => setQueue([]));
  }, [selected]);

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !requirements.trim()) return;
    setLoading(true);
    const res = await fetch("/api/pipeline/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        config_path: selected.config,
        requirements: requirements.trim(),
        project_name: selected.name,
      }),
    });
    const data = await res.json();

    if (data.queue_position > 0) {
      toast(`Queued at position #${data.queue_position}`, "info");
    }

    router.push(`/pipeline/${data.run_id}/running`);
  }

  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-semibold tracking-tight mb-1" style={{ color: "var(--text-primary)" }}>
        Pipeline
      </h2>
      <p className="text-sm mb-8" style={{ color: "var(--text-tertiary)" }}>
        Input requirements &rarr; Design &rarr; Dev &rarr; Test &rarr; Review &rarr; Docs
      </p>

      {projects.length === 0 ? (
        <div className="rounded-lg p-4" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)" }}>
          <p style={{ color: "#FBBF24" }}>
            No bootstrapped projects found. Run{" "}
            <a href="/bootstrap" style={{ color: "#60A5FA", textDecoration: "underline" }}>Bootstrap</a> first.
          </p>
        </div>
      ) : (
        <>
          <form onSubmit={handleStart}>
            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
              Project
            </label>
            <select
              value={selected?.name || ""}
              onChange={(e) => setSelected(projects.find((p) => p.name === e.target.value) || null)}
              className="w-full px-3 py-2 rounded-md text-sm mb-4 outline-none transition-colors duration-150 focus-ring"
              style={{
                background: "var(--bg-base)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                height: "36px",
              }}
            >
              {projects.map((p) => (
                <option key={p.name} value={p.name}>{p.name}</option>
              ))}
            </select>

            {/* Queue indicator */}
            {queue.length > 0 && (
              <div className="rounded-lg p-3 mb-4 text-sm"
                   style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)" }}>
                <div className="flex items-center gap-2 mb-1" style={{ color: "#60A5FA" }}>
                  <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#60A5FA" }} />
                  {queue.length} run(s) in queue for {selected?.name}
                </div>
                {queue.map((q) => (
                  <div key={q.run_id} className="text-xs ml-4" style={{ color: "var(--text-tertiary)" }}>
                    #{q.position}: {q.run_id} — {q.phase}
                  </div>
                ))}
                <p className="text-xs mt-1 ml-4" style={{ color: "var(--text-tertiary)" }}>
                  New run will be queued after current runs complete.
                </p>
              </div>
            )}

            <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
              Requirements
            </label>
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              rows={8}
              required
              placeholder={"Example: Implement user login API.\n- JWT token based auth\n- Lock account after 5 failed attempts"}
              className="w-full px-3 py-2 rounded-md text-sm outline-none transition-colors duration-150 focus-ring resize-y"
              style={{
                background: "var(--bg-base)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
              }}
            />

            <button
              type="submit"
              disabled={loading || !requirements.trim()}
              className="mt-4 px-4 py-2 rounded-md text-sm font-medium transition-opacity duration-150 disabled:opacity-40"
              style={{ background: "var(--text-primary)", color: "var(--bg-base)", height: "36px" }}
            >
              {loading ? "Starting..." : queue.length > 0 ? "Queue Pipeline" : "Run Pipeline"}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
