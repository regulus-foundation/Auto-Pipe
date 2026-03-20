"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/bootstrap", label: "Bootstrap", icon: "B" },
  { href: "/pipeline", label: "Pipeline", icon: "P" },
  { href: "/history", label: "History", icon: "H" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [projects, setProjects] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/bootstrap/projects")
      .then((r) => r.json())
      .then((d) => setProjects((d.projects || []).map((p: any) => p.name)))
      .catch(() => {});
  }, []);

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

      <nav className="flex-1 p-2 space-y-0.5 mt-1 overflow-y-auto">
        <SectionLabel>Workspace</SectionLabel>
        {NAV_ITEMS.map(({ href, label, icon }) => (
          <NavItem key={href} href={href} label={label} icon={icon} pathname={pathname} />
        ))}

        {projects.length > 0 && (
          <>
            <SectionLabel className="mt-4">Projects</SectionLabel>
            {projects.map((name) => (
              <NavItem
                key={name}
                href={`/project/${name}`}
                label={name}
                icon={name[0].toUpperCase()}
                pathname={pathname}
                small
              />
            ))}
          </>
        )}
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

function SectionLabel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={`px-3 pt-2 pb-1.5 text-[11px] font-medium uppercase ${className}`}
       style={{ color: "var(--text-tertiary)", letterSpacing: "0.05em" }}>
      {children}
    </p>
  );
}

function NavItem({ href, label, icon, pathname, small }: {
  href: string; label: string; icon: string; pathname: string; small?: boolean;
}) {
  const active = pathname === href || (pathname.startsWith(href + "/") && href !== "/");

  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-3 rounded-md text-[13px] font-medium transition-all duration-150 ${small ? "py-[5px]" : "py-[7px]"}`}
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
        className={`rounded flex items-center justify-center font-semibold ${small ? "w-[18px] h-[18px] text-[9px]" : "w-[22px] h-[22px] text-[11px]"}`}
        style={{
          background: active ? "var(--accent-primary)" : "var(--bg-overlay)",
          color: active ? "#fff" : "var(--text-tertiary)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        {icon}
      </span>
      <span className={small ? "truncate" : ""}>{label}</span>
    </Link>
  );
}
