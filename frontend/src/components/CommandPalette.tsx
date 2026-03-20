"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

interface Command {
  id: string;
  label: string;
  description: string;
  href: string;
}

const STATIC_COMMANDS: Command[] = [
  { id: "bootstrap", label: "Bootstrap", description: "Analyze a new project", href: "/bootstrap" },
  { id: "pipeline", label: "Pipeline", description: "Run development pipeline", href: "/pipeline" },
  { id: "history", label: "History", description: "View execution history", href: "/history" },
];

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [commands, setCommands] = useState<Command[]>(STATIC_COMMANDS);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelected(0);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      // Load project commands dynamically
      fetch("/api/bootstrap/projects")
        .then((r) => r.json())
        .then((d) => {
          const projectCmds = (d.projects || []).map((p: any) => ({
            id: `project-${p.name}`,
            label: p.name,
            description: "Project config & prompts",
            href: `/project/${p.name}`,
          }));
          setCommands([...STATIC_COMMANDS, ...projectCmds]);
        })
        .catch(() => {});
    }
  }, [open]);

  if (!open) return null;

  const filtered = commands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.description.toLowerCase().includes(query.toLowerCase())
  );

  function handleSelect(href: string) {
    setOpen(false);
    router.push(href);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((prev) => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && filtered[selected]) {
      handleSelect(filtered[selected].href);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50"
        style={{ background: "rgba(0,0,0,0.5)" }}
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div
        className="fixed top-[20%] left-1/2 -translate-x-1/2 z-50 w-[560px]"
        style={{
          background: "rgba(17,17,20,0.95)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.6)",
          overflow: "hidden",
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
          onKeyDown={handleKeyDown}
          placeholder="Type a command..."
          className="w-full px-4 text-[15px] outline-none"
          style={{
            background: "transparent",
            color: "var(--text-primary)",
            height: "48px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        />

        <div className="max-h-[300px] overflow-y-auto p-1">
          {filtered.map((cmd, i) => (
            <button
              key={cmd.id}
              onClick={() => handleSelect(cmd.href)}
              className="w-full flex items-center gap-3 px-4 rounded-md text-left transition-colors duration-100"
              style={{
                height: "40px",
                background: i === selected ? "rgba(255,255,255,0.06)" : "transparent",
                color: i === selected ? "var(--text-primary)" : "var(--text-secondary)",
              }}
              onMouseEnter={() => setSelected(i)}
            >
              <span className="text-sm font-medium">{cmd.label}</span>
              <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>{cmd.description}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-6 text-center text-sm" style={{ color: "var(--text-tertiary)" }}>
              No results
            </div>
          )}
        </div>

        <div className="px-4 py-2 text-[11px] flex gap-4" style={{ borderTop: "1px solid rgba(255,255,255,0.06)", color: "var(--text-tertiary)" }}>
          <span><kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: "var(--bg-overlay)" }}>↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: "var(--bg-overlay)" }}>↵</kbd> select</span>
          <span><kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: "var(--bg-overlay)" }}>esc</kbd> close</span>
        </div>
      </div>
    </>
  );
}
