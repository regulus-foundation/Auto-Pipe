"""Utility API endpoints — runs listing, log files, markdown rendering"""

import os
import markdown as md
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from web.run_manager import run_manager, RunType
from web.shared import ROOT

router = APIRouter()


class MarkdownRequest(BaseModel):
    text: str


@router.post("/api/render-markdown")
async def render_markdown(req: MarkdownRequest):
    html = md.markdown(req.text, extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"])
    return {"html": html}


@router.get("/api/runs")
async def list_runs(run_type: str | None = None):
    """List all active/completed runs."""
    rt = RunType(run_type) if run_type else None
    runs = run_manager.list_runs(rt)
    return {"runs": [r.to_summary() for r in runs]}


@router.get("/api/projects/{project_name}/logs")
async def list_project_logs(project_name: str):
    """List log files for a project."""
    log_dir = ROOT / "projects" / project_name / "log"
    if not log_dir.exists():
        return {"logs": []}
    logs = []
    for f in sorted(log_dir.iterdir(), reverse=True):
        if f.suffix == ".log":
            logs.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
    return {"logs": logs}


@router.get("/api/projects/{project_name}/logs/{log_name}")
async def read_project_log(project_name: str, log_name: str):
    """Read a specific log file content."""
    log_path = ROOT / "projects" / project_name / "log" / log_name
    if not log_path.exists() or ".." in log_name or "/" in log_name:
        raise HTTPException(status_code=404, detail="Log not found")
    content = log_path.read_text(encoding="utf-8", errors="replace")
    return {"name": log_name, "content": content}
