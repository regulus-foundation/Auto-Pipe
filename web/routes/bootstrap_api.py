"""Bootstrap API — start analysis, SSE stream, approve (JSON responses)"""

import asyncio
import json
import os
import uuid
import yaml
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from web.run_manager import run_manager, RunType

_ROOT = Path(__file__).resolve().parent.parent.parent
_executor = ThreadPoolExecutor(max_workers=4)

router = APIRouter()


class StartRequest(BaseModel):
    project_path: str

class LoadExistingRequest(BaseModel):
    project_name: str


def _run_bootstrap_graph(run):
    """Run bootstrap graph in background thread."""
    from bootstrap.graph import build_bootstrap_graph, set_log_callback
    from core.file_logger import start_file_logger, stop_file_logger
    from core.langfuse_callback import get_langfuse_handler

    project_path = run.state["project_path"]
    proj_name = os.path.basename(project_path.rstrip("/"))

    graph = build_bootstrap_graph()
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    initial_state = {
        "project_path": project_path,
        "scan_result": {},
        "collected_files": {},
        "deep_analysis": {},
        "analysis_approved": False,
        "gen_result": {},
        "steps": [],
        "current_step": "start",
        "progress": 0,
        "errors": [],
    }

    file_logger = start_file_logger(proj_name, "bootstrap")

    def on_log(line: str):
        run.push_log(line)

    set_log_callback(on_log)
    run.graph = graph
    run.thread_id = thread_id

    try:
        run.push_event("status", {"step": "Bootstrap pipeline starting..."})

        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        if step:
                            run.push_event("status", {"node": node_name, "step": step})

        final_state = graph.get_state(config)
        run.state = dict(final_state.values)
        run.phase = "review"
        run.push_event("phase", {"phase": "review", "redirect": f"/bootstrap/{run.run_id}/review"})

    except Exception as e:
        run.error = str(e)
        run.phase = "error"
        run.push_event("error", {"message": str(e)})
    finally:
        set_log_callback(None)
        stop_file_logger(success=run.phase != "error")
        run.push_event("done", {})


@router.post("/start")
async def start_bootstrap(req: StartRequest):
    path = req.project_path.strip()
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Invalid path")

    run = run_manager.create_run(RunType.BOOTSTRAP)
    run.phase = "analyzing"
    run.state = {"project_path": path}
    run.set_loop(asyncio.get_event_loop())

    _executor.submit(_run_bootstrap_graph, run)

    return {"run_id": run.run_id, "phase": "analyzing"}


@router.post("/load-existing")
async def load_existing(req: LoadExistingRequest):
    """Load existing analysis results directly to review."""
    projects_dir = _ROOT / "projects" / req.project_name

    analysis_path = projects_dir / "project_analysis.yaml"
    if not analysis_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    with open(analysis_path, "r") as f:
        scan = yaml.safe_load(f)

    deep = {"steps": {}, "total_tokens": 0, "total_duration": 0, "files_analyzed": 0}
    analysis_dir = projects_dir / "analysis"
    if analysis_dir.is_dir():
        step_filenames = {
            "01_dependencies.md": "dependencies",
            "02_architecture.md": "architecture",
            "03_testing.md": "testing",
            "04_summary.md": "summary",
        }
        for filename, step_key in step_filenames.items():
            fpath = analysis_dir / filename
            if fpath.exists():
                deep["steps"][step_key] = fpath.read_text(encoding="utf-8")
        meta_path = analysis_dir / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                deep["files_analyzed"] = meta.get("files_analyzed", 0)
                deep["total_duration"] = meta.get("total_duration", 0)
                deep["total_tokens"] = meta.get("total_tokens", 0)
            except (json.JSONDecodeError, OSError):
                pass

    run = run_manager.create_run(RunType.BOOTSTRAP)
    run.phase = "review"
    run.state = {"scan_result": scan, "deep_analysis": deep}

    return {"run_id": run.run_id, "phase": "review"}


@router.get("/{run_id}/stream")
async def stream_logs(run_id: str):
    """SSE endpoint for real-time log streaming."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(run.log_queue.get(), timeout=30.0)
                yield {"event": event["type"], "data": json.dumps(event["data"], ensure_ascii=False)}
                if event["type"] in ("done", "error", "phase"):
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}

    return EventSourceResponse(event_generator())


@router.get("/{run_id}/state")
async def get_run_state(run_id: str):
    """Get full run state for rendering review/done pages."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run.run_id, "phase": run.phase, "state": run.state, "error": run.error}


@router.post("/{run_id}/approve")
async def approve_bootstrap(run_id: str):
    """Human review approved → generate config."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not run.graph:
        from core.config_generator import generate_config
        scan = run.state.get("scan_result", {})
        project_name = scan.get("project", {}).get("name", "unknown")
        output_dir = str(_ROOT / "projects" / project_name)
        gen_result = generate_config(scan, output_dir)
        run.state["gen_result"] = gen_result
        run.phase = "done"
        return {"run_id": run_id, "phase": "done"}

    config = {"configurable": {"thread_id": run.thread_id}}

    from core.langfuse_callback import get_langfuse_handler
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    run.graph.update_state(config, {"analysis_approved": True})

    for chunk in run.graph.stream(None, config, stream_mode="updates"):
        if isinstance(chunk, dict):
            for node_name, update in chunk.items():
                if isinstance(update, dict) and "gen_result" in update:
                    run.state["gen_result"] = update["gen_result"]

    final = run.graph.get_state(config)
    run.state = dict(final.values)
    run.phase = "done"

    return {"run_id": run_id, "phase": "done"}


@router.get("/projects")
async def list_projects():
    """List existing analyzed projects."""
    projects_dir = _ROOT / "projects"
    results = []
    if projects_dir.exists():
        for d in sorted(projects_dir.iterdir()):
            if d.is_dir() and d.name != ".gitkeep" and (d / "project_analysis.yaml").exists():
                has_pipeline = (d / "pipeline.yaml").exists()
                results.append({"name": d.name, "has_pipeline": has_pipeline})
    return {"projects": results}


@router.get("/configured-projects")
async def list_configured_projects():
    """List projects with pipeline.yaml (for pipeline page)."""
    projects_dir = _ROOT / "projects"
    results = []
    if projects_dir.exists():
        for d in sorted(projects_dir.iterdir()):
            pipeline_yaml = d / "pipeline.yaml"
            if d.is_dir() and pipeline_yaml.exists():
                results.append({"name": d.name, "config": str(pipeline_yaml)})
    return {"projects": results}
