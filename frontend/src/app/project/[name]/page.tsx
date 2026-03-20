"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { useToast } from "@/components/Toast";
import Tabs from "@/components/Tabs";
import { SkeletonPage } from "@/components/Skeleton";

interface NodeInfo {
  id: string;
  label: string;
  executor: string;
  prompt_template: string;
  inputs: string[];
  outputs: string[];
  has_prompt: boolean;
}

interface PromptFile {
  name: string;
  size: number;
}

interface ProjectConfig {
  name: string;
  pipeline: any;
  analysis: any;
  prompts: PromptFile[];
  nodes: NodeInfo[];
}

const EXECUTOR_COLORS: Record<string, { bg: string; color: string }> = {
  api: { bg: "rgba(59,130,246,0.15)", color: "#60A5FA" },
  console: { bg: "rgba(168,85,247,0.15)", color: "#C084FC" },
  tool: { bg: "rgba(34,197,94,0.15)", color: "#4ADE80" },
};

export default function ProjectConfigPage() {
  const { name } = useParams<{ name: string }>();
  const { toast } = useToast();
  const [config, setConfig] = useState<ProjectConfig | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [promptContent, setPromptContent] = useState("");
  const [promptLoading, setPromptLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editedContent, setEditedContent] = useState("");

  useEffect(() => {
    fetch(`/api/projects/${name}/config`)
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => {});
  }, [name]);

  const loadPrompt = useCallback(async (promptName: string) => {
    setPromptLoading(true);
    try {
      const res = await fetch(`/api/projects/${name}/prompts/${promptName}`);
      const data = await res.json();
      setPromptContent(data.content);
      setEditedContent(data.content);
    } catch {
      setPromptContent("");
      setEditedContent("");
    }
    setPromptLoading(false);
  }, [name]);

  async function handleSave(promptName: string) {
    setSaving(true);
    try {
      const res = await fetch(`/api/projects/${name}/prompts/${promptName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editedContent }),
      });
      if (res.ok) {
        setPromptContent(editedContent);
        toast("Prompt saved", "success");
      } else {
        toast("Failed to save", "error");
      }
    } catch {
      toast("Failed to save", "error");
    }
    setSaving(false);
  }

  function selectNode(node: NodeInfo) {
    setSelectedNode(node);
    if (node.prompt_template) {
      const fileName = node.prompt_template.replace("prompts/", "");
      loadPrompt(fileName);
    } else {
      setPromptContent("");
      setEditedContent("");
    }
  }

  if (!config) return <SkeletonPage />;

  const project = config.analysis?.project || {};
  const hasChanges = editedContent !== promptContent;

  const tabs = [
    {
      id: "flow",
      label: "Pipeline Flow",
      content: (
        <div className="space-y-1">
          {config.nodes.map((node, i) => {
            const exec = EXECUTOR_COLORS[node.executor] || { bg: "var(--bg-overlay)", color: "var(--text-tertiary)" };
            const isSelected = selectedNode?.id === node.id;
            return (
              <div key={node.id}>
                {/* Node */}
                <button
                  onClick={() => selectNode(node)}
                  className="w-full text-left rounded-lg p-3 transition-all duration-150 flex items-center gap-3"
                  style={{
                    background: isSelected ? "var(--bg-raised)" : "transparent",
                    border: `1px solid ${isSelected ? "var(--border-strong)" : "var(--border-subtle)"}`,
                  }}
                  onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.borderColor = "var(--border-default)"; }}
                  onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.borderColor = "var(--border-subtle)"; }}
                >
                  {/* Node number */}
                  <span className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-semibold shrink-0"
                        style={{ background: exec.bg, color: exec.color }}>
                    {i + 1}
                  </span>

                  {/* Node info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                        {node.label}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium" style={{ background: exec.bg, color: exec.color }}>
                        {node.executor}
                      </span>
                      {node.has_prompt && (
                        <span className="text-[10px]" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                          {node.prompt_template}
                        </span>
                      )}
                    </div>
                    <div className="flex gap-4 mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                      <span>in: {node.inputs.join(", ")}</span>
                      <span>out: {node.outputs.join(", ")}</span>
                    </div>
                  </div>

                  {/* Arrow indicator */}
                  <span className="text-xs shrink-0" style={{ color: "var(--text-tertiary)" }}>
                    {isSelected ? "▸" : ""}
                  </span>
                </button>

                {/* Connector */}
                {i < config.nodes.length - 1 && (
                  <div className="flex justify-start ml-[22px] my-0.5">
                    <div className="w-0.5 h-3 rounded-full" style={{ background: "var(--border-default)" }} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ),
    },
    {
      id: "prompts",
      label: `Prompts (${config.prompts.length})`,
      content: (
        <div className="space-y-1">
          {config.prompts.map((p) => {
            const isActive = selectedNode?.prompt_template === `prompts/${p.name}`;
            return (
              <button
                key={p.name}
                onClick={() => {
                  const node = config.nodes.find((n) => n.prompt_template === `prompts/${p.name}`);
                  if (node) selectNode(node);
                  else loadPrompt(p.name);
                }}
                className="w-full text-left px-3 py-2.5 rounded-lg transition-all duration-150 flex items-center justify-between"
                style={{
                  background: isActive ? "var(--bg-raised)" : "transparent",
                  border: `1px solid ${isActive ? "var(--border-strong)" : "var(--border-subtle)"}`,
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.borderColor = "var(--border-default)"; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.borderColor = "var(--border-subtle)"; }}
              >
                <span className="text-[13px]" style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                  {p.name}
                </span>
                <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                  {(p.size / 1024).toFixed(1)} KB
                </span>
              </button>
            );
          })}
        </div>
      ),
    },
    {
      id: "config",
      label: "pipeline.yaml",
      content: (
        <pre className="rounded-lg p-4 text-xs overflow-auto max-h-[480px]"
             style={{ background: "#0A0A0C", border: "1px solid var(--border-subtle)", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", lineHeight: "1.7" }}>
          {config.pipeline ? yaml_stringify(config.pipeline) : "No pipeline.yaml"}
        </pre>
      ),
    },
  ];

  return (
    <div className="max-w-7xl animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          {name}
        </h2>
        <div className="flex gap-4 mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
          {project.language && <span>{project.language}</span>}
          {config.pipeline?.project?.framework && <span>{config.pipeline.project.framework}</span>}
          {project.path && (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>{project.path}</span>
          )}
        </div>
      </div>

      {/* Two-column layout: flow/prompts left, editor right */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Pipeline Flow + Prompts */}
        <div>
          <Tabs tabs={tabs} defaultTab="flow" />
        </div>

        {/* Right: Prompt Editor */}
        <div className="rounded-lg overflow-hidden" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}>
          {selectedNode ? (
            <>
              {/* Editor header */}
              <div className="px-4 py-3 flex items-center justify-between"
                   style={{ borderBottom: "1px solid var(--border-default)", background: "var(--bg-base)" }}>
                <div>
                  <div className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                    {selectedNode.label}
                  </div>
                  <div className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                    {selectedNode.prompt_template || "No prompt template"}
                  </div>
                </div>
                {selectedNode.has_prompt && (
                  <div className="flex gap-2 items-center">
                    {hasChanges && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full"
                            style={{ background: "rgba(245,158,11,0.15)", color: "#FBBF24" }}>
                        unsaved
                      </span>
                    )}
                    <button
                      onClick={() => handleSave(selectedNode.prompt_template.replace("prompts/", ""))}
                      disabled={saving || !hasChanges}
                      className="px-3 py-1.5 rounded-md text-xs font-medium transition-opacity duration-150 disabled:opacity-30"
                      style={{ background: "var(--text-primary)", color: "var(--bg-base)" }}
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                  </div>
                )}
              </div>

              {/* Input/Output info */}
              <div className="px-4 py-2 flex gap-6 text-[11px]"
                   style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-tertiary)" }}>
                <div>
                  <span className="font-medium uppercase" style={{ letterSpacing: "0.05em" }}>Input: </span>
                  {selectedNode.inputs.map((inp) => (
                    <span key={inp} className="px-1.5 py-0.5 rounded mr-1"
                          style={{ background: "var(--bg-overlay)", fontFamily: "var(--font-mono)" }}>
                      {inp}
                    </span>
                  ))}
                </div>
                <div>
                  <span className="font-medium uppercase" style={{ letterSpacing: "0.05em" }}>Output: </span>
                  {selectedNode.outputs.map((out) => (
                    <span key={out} className="px-1.5 py-0.5 rounded mr-1"
                          style={{ background: "var(--bg-overlay)", fontFamily: "var(--font-mono)" }}>
                      {out}
                    </span>
                  ))}
                </div>
              </div>

              {/* Editor content */}
              {selectedNode.has_prompt ? (
                promptLoading ? (
                  <div className="p-8 text-center text-sm" style={{ color: "var(--text-tertiary)" }}>Loading...</div>
                ) : (
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full p-4 text-xs outline-none resize-none"
                    style={{
                      background: "#0A0A0C",
                      color: "var(--text-secondary)",
                      fontFamily: "var(--font-mono)",
                      lineHeight: "1.7",
                      minHeight: "500px",
                      border: "none",
                    }}
                    spellCheck={false}
                  />
                )
              ) : (
                <div className="p-8 text-center text-sm" style={{ color: "var(--text-tertiary)" }}>
                  This node uses a {selectedNode.executor} executor with no prompt template.
                  {selectedNode.executor === "tool" && (
                    <div className="mt-2" style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>
                      Command: {config.pipeline?.nodes?.[selectedNode.id]?.command || "N/A"}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="p-12 text-center text-sm" style={{ color: "var(--text-tertiary)" }}>
              Select a pipeline node or prompt to view/edit
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function yaml_stringify(obj: any): string {
  // Simple YAML-like formatting
  return JSON.stringify(obj, null, 2)
    .replace(/[{}\[\]",]/g, (m) => {
      if (m === "{" || m === "}") return "";
      if (m === "[" || m === "]") return "";
      if (m === '"') return "";
      if (m === ",") return "";
      return m;
    })
    .split("\n")
    .filter((l) => l.trim())
    .join("\n");
}
