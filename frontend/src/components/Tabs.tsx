"use client";

import { useState, ReactNode } from "react";

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
}

export default function Tabs({ tabs, defaultTab }: TabsProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.id);

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-lg)" }}
    >
      <div
        className="flex overflow-x-auto"
        style={{ borderBottom: "1px solid var(--border-default)", background: "var(--bg-base)" }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className="px-4 py-2.5 text-[13px] font-medium whitespace-nowrap transition-all duration-150 -mb-px"
            style={{
              borderBottom: `2px solid ${active === tab.id ? "var(--accent-primary)" : "transparent"}`,
              color: active === tab.id ? "var(--text-primary)" : "var(--text-tertiary)",
              background: active === tab.id ? "var(--bg-surface)" : "transparent",
            }}
            onMouseEnter={(e) => {
              if (active !== tab.id) e.currentTarget.style.color = "var(--text-secondary)";
            }}
            onMouseLeave={(e) => {
              if (active !== tab.id) e.currentTarget.style.color = "var(--text-tertiary)";
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="p-5">
        {tabs.map((tab) => (
          <div key={tab.id} className={active === tab.id ? "animate-fade-in" : "hidden"}>
            {tab.content}
          </div>
        ))}
      </div>
    </div>
  );
}
