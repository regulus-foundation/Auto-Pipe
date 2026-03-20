"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/bootstrap", label: "Bootstrap", icon: "B" },
  { href: "/pipeline", label: "Pipeline", icon: "P" },
  { href: "/history", label: "History", icon: "H" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-60 flex flex-col min-h-screen fixed"
      style={{ background: "var(--bg-surface)", borderRight: "1px solid var(--border-default)" }}
    >
      <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
        <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Auto-Pipe
        </h1>
        <p className="text-xs mt-0.5" style={{ color: "var(--text-tertiary)" }}>
          Development Automation
        </p>
      </div>

      <nav className="flex-1 p-2 space-y-0.5 mt-1">
        <p className="px-3 pt-2 pb-1.5 text-[11px] font-medium uppercase"
           style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
          Workspace
        </p>
        {NAV_ITEMS.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-[7px] rounded-md text-[13px] font-medium transition-all duration-150"
              style={{
                color: active ? "var(--text-primary)" : "var(--text-secondary)",
                background: active ? "var(--bg-raised)" : "transparent",
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.background = "var(--bg-raised)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }
              }}
            >
              <span
                className="w-[22px] h-[22px] rounded flex items-center justify-center text-[11px] font-semibold"
                style={{
                  background: active ? "var(--accent-primary)" : "var(--bg-overlay)",
                  color: active ? "#fff" : "var(--text-tertiary)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {icon}
              </span>
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-3" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <div className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          <kbd className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: "var(--bg-overlay)" }}>⌘K</kbd>
          <span>Command palette</span>
        </div>
      </div>
    </aside>
  );
}
