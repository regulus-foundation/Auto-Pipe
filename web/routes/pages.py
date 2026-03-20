"""Utility API endpoints — runs, logs, project config, prompt editor"""

import os
import yaml
import markdown as md
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from web.run_manager import run_manager, RunType
from web.shared import ROOT

router = APIRouter()


class MarkdownRequest(BaseModel):
    text: str

class PromptUpdateRequest(BaseModel):
    content: str


@router.post("/api/render-markdown")
async def render_markdown(req: MarkdownRequest):
    html = md.markdown(req.text, extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"])
    return {"html": html}


@router.get("/api/runs")
async def list_runs(run_type: str | None = None):
    rt = RunType(run_type) if run_type else None
    runs = run_manager.list_runs(rt)
    return {"runs": [r.to_summary() for r in runs]}


# ─── Project Config ───

@router.get("/api/projects/{project_name}/config")
async def get_project_config(project_name: str):
    """Get full project configuration — pipeline.yaml + analysis + prompt list."""
    project_dir = ROOT / "projects" / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    result = {"name": project_name, "pipeline": None, "analysis": None, "prompts": [], "nodes": []}

    # pipeline.yaml
    pipeline_path = project_dir / "pipeline.yaml"
    if pipeline_path.exists():
        with open(pipeline_path, "r", encoding="utf-8") as f:
            pipeline = yaml.safe_load(f)
        result["pipeline"] = pipeline

        # Extract nodes with their input/output mapping
        nodes_config = pipeline.get("nodes", {})
        node_order = [
            ("pre_build_check", "Pre-build Check", "tool", ["project_path"], ["pre_build_result", "pre_build_errors"]),
            ("generate_design", "Design", "console", ["requirements", "config_path"], ["design_spec"]),
            ("develop_code", "Code Dev", "console", ["design_spec", "requirements"], ["source_code", "code_files_created"]),
            ("write_tests", "Tests", "console", ["requirements", "source_code"], ["test_code", "code_files_created"]),
            ("build", "Build", "tool", ["project_path"], ["build_result", "build_log"]),
            ("run_tests", "Test Run", "tool", ["project_path"], ["test_result", "test_log", "test_errors"]),
            ("fix_code", "Fix Code", "console", ["design_spec", "source_code", "test_errors", "build_log"], ["source_code"]),
            ("review_quality", "Quality Review", "api", ["source_code", "requirements"], ["review_report"]),
            ("review_security", "Security Review", "api", ["source_code"], ["security_report"]),
            ("generate_api_doc", "API Docs", "api", ["source_code", "requirements"], ["api_doc"]),
            ("generate_ops_manual", "Ops Manual", "api", ["source_code", "requirements"], ["ops_manual"]),
            ("generate_changelog", "Changelog", "api", ["source_code", "requirements"], ["changelog"]),
        ]

        nodes = []
        for node_id, label, default_executor, inputs, outputs in node_order:
            nc = nodes_config.get(node_id, {})
            prompt_file = nc.get("prompt_template", "")
            nodes.append({
                "id": node_id,
                "label": label,
                "executor": nc.get("executor", default_executor),
                "prompt_template": prompt_file,
                "inputs": inputs,
                "outputs": outputs,
                "has_prompt": bool(prompt_file),
            })
        result["nodes"] = nodes

    # project_analysis.yaml
    analysis_path = project_dir / "project_analysis.yaml"
    if analysis_path.exists():
        with open(analysis_path, "r", encoding="utf-8") as f:
            result["analysis"] = yaml.safe_load(f)

    # List prompt files
    prompts_dir = project_dir / "prompts"
    if prompts_dir.exists():
        for f in sorted(prompts_dir.iterdir()):
            if f.suffix == ".md":
                result["prompts"].append({
                    "name": f.name,
                    "size": f.stat().st_size,
                })

    return result


@router.get("/api/projects/{project_name}/prompts/{prompt_name}")
async def read_prompt(project_name: str, prompt_name: str):
    """Read a prompt template file."""
    if ".." in prompt_name or "/" in prompt_name:
        raise HTTPException(status_code=400, detail="Invalid name")
    prompt_path = ROOT / "projects" / project_name / "prompts" / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"name": prompt_name, "content": prompt_path.read_text(encoding="utf-8")}


@router.put("/api/projects/{project_name}/prompts/{prompt_name}")
async def update_prompt(project_name: str, prompt_name: str, req: PromptUpdateRequest):
    """Update a prompt template file."""
    if ".." in prompt_name or "/" in prompt_name:
        raise HTTPException(status_code=400, detail="Invalid name")
    prompt_path = ROOT / "projects" / project_name / "prompts" / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt_path.write_text(req.content, encoding="utf-8")
    return {"name": prompt_name, "size": len(req.content), "saved": True}


# ─── Project Logs ───

@router.get("/api/projects/{project_name}/logs")
async def list_project_logs(project_name: str):
    log_dir = ROOT / "projects" / project_name / "log"
    if not log_dir.exists():
        return {"logs": []}
    logs = []
    for f in sorted(log_dir.iterdir(), reverse=True):
        if f.suffix == ".log":
            logs.append({"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return {"logs": logs}


@router.get("/api/projects/{project_name}/logs/{log_name}")
async def read_project_log(project_name: str, log_name: str):
    log_path = ROOT / "projects" / project_name / "log" / log_name
    if not log_path.exists() or ".." in log_name or "/" in log_name:
        raise HTTPException(status_code=404, detail="Log not found")
    content = log_path.read_text(encoding="utf-8", errors="replace")
    return {"name": log_name, "content": content}
