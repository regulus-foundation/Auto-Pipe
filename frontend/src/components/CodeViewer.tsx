"use client";

import { useState } from "react";

interface CodeViewerProps {
  files: Record<string, string>;
}

export default function CodeViewer({ files }: CodeViewerProps) {
  const entries = Object.entries(files);

  if (entries.length === 0) {
    return <p className="text-center py-8 text-[13px]" style={{ color: "var(--text-tertiary)" }}>No source code generated.</p>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([filepath, content]) => (
        <FileBlock key={filepath} filepath={filepath} content={content} />
      ))}
    </div>
  );
}

function FileBlock({ filepath, content }: { filepath: string; content: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2.5 text-left text-[13px] flex items-center gap-2 transition-all duration-150"
        style={{
          background: "var(--bg-raised)",
          color: "var(--text-secondary)",
          fontFamily: "var(--font-mono)",
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-overlay)"}
        onMouseLeave={(e) => e.currentTarget.style.background = "var(--bg-raised)"}
      >
        <span style={{ color: "var(--text-tertiary)" }} className="text-xs">{open ? "▾" : "▸"}</span>
        {filepath}
      </button>
      {open && (
        <pre
          className="p-4 text-xs overflow-auto max-h-[480px]"
          style={{
            background: "#0A0A0C",
            color: "#D4D4D8",
            fontFamily: "var(--font-mono)",
            lineHeight: "1.7",
          }}
        >
          {content}
        </pre>
      )}
    </div>
  );
}
