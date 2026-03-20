"use client";

import { useEffect, useRef } from "react";

interface LogViewerProps {
  logs: string[];
  height?: string;
}

export default function LogViewer({ logs, height = "h-[480px]" }: LogViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div
      ref={containerRef}
      className={`rounded-lg p-4 ${height} overflow-y-auto log-container`}
      style={{
        background: "#0A0A0C",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        fontFamily: "var(--font-mono)",
        fontSize: "12px",
        lineHeight: "1.7",
        color: "var(--text-secondary)",
      }}
    >
      {logs.map((line, i) => (
        <div
          key={i}
          className="flex transition-colors duration-100"
          style={{ padding: "1px 0" }}
          onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
        >
          <span
            className="select-none text-right shrink-0"
            style={{ color: "var(--text-tertiary)", minWidth: "4ch", marginRight: "16px" }}
          >
            {i + 1}
          </span>
          <span>{line}</span>
        </div>
      ))}
      {logs.length === 0 && (
        <span style={{ color: "var(--text-tertiary)" }}>Waiting for output...</span>
      )}
    </div>
  );
}
