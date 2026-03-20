"""Pipeline API — start pipeline, SSE stream, approve/reject, queuing"""

import asyncio
import json
import uuid
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from web.run_manager import run_manager, RunType

_ROOT = Path(__file__).resolve().parent.parent.parent

router = APIRouter()


class StartRequest(BaseModel):
    config_path: str
    requirements: str
    project_name: str

class FeedbackRequest(BaseModel):
    feedback: str = ""


def _get_project_path(config_path: str) -> str:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("project", {}).get("path", "")
    except Exception:
        return ""


def _run_full_pipeline(run):
    """Run the entire pipeline: design → [human] → dev → build → test → [human] → docs.
    Called by the project queue when it's this run's turn."""
    _run_design_phase(run)
    # After design phase, run is in "design_review" — waiting for human
    # The queue does NOT advance until run.phase becomes "done" or "error"


def _run_design_phase(run):
    from pipeline.graph import build_pipeline_graph
    from pipeline.utils import set_log_callback
    from core.file_logger import start_file_logger
    from core.langfuse_callback import get_langfuse_handler

    state_data = run.state
    graph = build_pipeline_graph()
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
    except Exception:
        pass

    initial_state = {
        "requirements": state_data["requirements"],
        "project_name": state_data["project_name"],
        "project_path": state_data["project_path"],
        "config_path": state_data["config_path"],
        "pre_build_result": "", "pre_build_errors": "",
        "pre_test_result": "", "pre_test_errors": "",
        "requirements_analysis": "", "design_spec": "",
        "api_spec": "", "db_schema": "", "ui_spec": "",
        "design_approved": False, "design_feedback": state_data.get("design_feedback", ""),
        "source_code": {}, "test_code": {}, "code_files_created": [],
        "build_result": "", "build_log": "",
        "test_result": "", "test_log": "", "test_errors": [],
        "fix_iteration": 0, "max_fix_iterations": 5,
        "review_report": "", "security_report": "", "merged_review": "",
        "review_approved": False, "review_feedback": "",
        "review_iteration": 0, "max_review_iterations": 3,
        "api_doc": "", "ops_manual": "", "changelog": "",
        "deliverables": [],
        "current_phase": "design", "current_step": "start",
        "progress": 0, "messages": [], "errors": [],
    }

    start_file_logger(state_data["project_name"], "pipeline")

    def on_log(line: str):
        run.push_log(line)

    set_log_callback(on_log)
    run.graph = graph
    run.thread_id = thread_id
    run.phase = "running_design"

    try:
        run.push_event("status", {"step": "Design phase starting..."})

        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        progress = update.get("progress", 0)
                        if step:
                            run.push_event("status", {"node": node_name, "step": step, "progress": progress})
                        for msg in update.get("messages", []):
                            run.push_event("message", {"text": msg})

        final_state = graph.get_state(config)
        run.state.update(dict(final_state.values))
        run.phase = "design_review"
        run.touch()
        run.push_event("phase", {"phase": "design_review", "redirect": f"/pipeline/{run.run_id}/design-review"})

    except Exception as e:
        run.error = str(e)
        run.phase = "error"
        run.push_event("error", {"message": str(e)})
    finally:
        set_log_callback(None)


def _run_main_phase(run):
    from pipeline.utils import set_log_callback
    from core.file_logger import get_file_logger, start_file_logger, stop_file_logger
    from core.langfuse_callback import get_langfuse_handler

    config = {"configurable": {"thread_id": run.thread_id}}

    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
    except Exception:
        pass

    run.graph.update_state(config, {"design_approved": True}, as_node="generate_design")

    if not get_file_logger():
        start_file_logger(run.state.get("project_name", "unknown"), "pipeline")

    def on_log(line: str):
        run.push_log(line)

    set_log_callback(on_log)

    try:
        run.push_event("status", {"step": "Development phase starting..."})

        for chunk in run.graph.stream(None, config, stream_mode="updates"):
            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        progress = update.get("progress", 0)
                        if step:
                            run.push_event("status", {"node": node_name, "step": step, "progress": progress})
                        for msg in update.get("messages", []):
                            run.push_event("message", {"text": msg})

        final_state = run.graph.get_state(config)
        run.state.update(dict(final_state.values))
        run.touch()

        if final_state.next:
            run.phase = "code_review"
            run.push_event("phase", {"phase": "code_review", "redirect": f"/pipeline/{run.run_id}/code-review"})
        else:
            run.phase = "done"
            run.push_event("phase", {"phase": "done", "redirect": f"/pipeline/{run.run_id}/done"})
            # Pipeline done — advance project queue
            run_manager.complete_pipeline(run)

    except Exception as e:
        run.error = str(e)
        run.phase = "error"
        run.push_event("error", {"message": str(e)})
        run_manager.complete_pipeline(run)
    finally:
        set_log_callback(None)
        stop_file_logger(success=run.phase != "error")


def _run_after_review(run, approved: bool, feedback: str = ""):
    from pipeline.utils import set_log_callback
    from core.file_logger import start_file_logger, stop_file_logger, get_file_logger
    from core.langfuse_callback import get_langfuse_handler

    config = {"configurable": {"thread_id": run.thread_id}}

    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
    except Exception:
        pass

    update_values = {"review_approved": approved}
    if not approved:
        update_values["review_feedback"] = feedback
    run.graph.update_state(config, update_values, as_node="merge_reviews")

    if not get_file_logger():
        start_file_logger(run.state.get("project_name", "unknown"), "pipeline")

    def on_log(line: str):
        run.push_log(line)

    set_log_callback(on_log)

    try:
        for chunk in run.graph.stream(None, config, stream_mode="updates"):
            if isinstance(chunk, dict):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        step = update.get("current_step", "")
                        progress = update.get("progress", 0)
                        if step:
                            run.push_event("status", {"node": node_name, "step": step, "progress": progress})

        final_state = run.graph.get_state(config)
        run.state.update(dict(final_state.values))
        run.touch()

        if final_state.next:
            run.phase = "code_review"
            run.push_event("phase", {"phase": "code_review", "redirect": f"/pipeline/{run.run_id}/code-review"})
        else:
            run.phase = "done"
            run.push_event("phase", {"phase": "done", "redirect": f"/pipeline/{run.run_id}/done"})
            run_manager.complete_pipeline(run)

    except Exception as e:
        run.error = str(e)
        run.phase = "error"
        run.push_event("error", {"message": str(e)})
        run_manager.complete_pipeline(run)
    finally:
        set_log_callback(None)
        stop_file_logger(success=run.phase != "error")


# ─── API Endpoints ───

@router.post("/start")
async def start_pipeline(req: StartRequest):
    run = run_manager.create_run(RunType.PIPELINE)
    run.state = {
        "requirements": req.requirements.strip(),
        "project_name": req.project_name,
        "project_path": _get_project_path(req.config_path),
        "config_path": req.config_path,
    }
    run.set_loop(asyncio.get_event_loop())

    # Enqueue — will start immediately if no other run for this project, or wait
    position = run_manager.enqueue_pipeline(run, _run_full_pipeline)

    return {
        "run_id": run.run_id,
        "phase": run.phase,
        "queue_position": position,
    }


@router.get("/{run_id}/stream")
async def stream_logs(run_id: str):
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # If queued, send queue position events until it starts
    async def event_generator():
        # Wait for run to leave "queued" state
        while run.phase == "queued":
            yield {
                "event": "status",
                "data": json.dumps({"step": f"Queued (position #{run.queue_position})", "progress": 0}),
            }
            await asyncio.sleep(2)

        # Stream actual events
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
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "phase": run.phase,
        "state": run.state,
        "error": run.error,
        "queue_position": run.queue_position,
    }


@router.post("/{run_id}/approve-design")
async def approve_design(run_id: str):
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.phase = "running_main"
    run.set_loop(asyncio.get_event_loop())
    run.log_queue = asyncio.Queue(maxsize=1000)
    # Run in the same project queue thread context
    import threading
    threading.Thread(target=_run_main_phase, args=(run,), daemon=True).start()
    return {"run_id": run_id, "phase": "running_main"}


@router.post("/{run_id}/reject-design")
async def reject_design(run_id: str, req: FeedbackRequest):
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.phase = "running_design"
    run.state["design_feedback"] = req.feedback
    run.graph = None
    run.thread_id = ""
    run.set_loop(asyncio.get_event_loop())
    run.log_queue = asyncio.Queue(maxsize=1000)
    import threading
    threading.Thread(target=_run_design_phase, args=(run,), daemon=True).start()
    return {"run_id": run_id, "phase": "running_design"}


@router.post("/{run_id}/approve-review")
async def approve_review(run_id: str):
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.phase = "running_main"
    run.set_loop(asyncio.get_event_loop())
    run.log_queue = asyncio.Queue(maxsize=1000)
    import threading
    threading.Thread(target=_run_after_review, args=(run, True), daemon=True).start()
    return {"run_id": run_id, "phase": "running_main"}


@router.post("/{run_id}/reject-review")
async def reject_review(run_id: str, req: FeedbackRequest):
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.phase = "running_main"
    run.set_loop(asyncio.get_event_loop())
    run.log_queue = asyncio.Queue(maxsize=1000)
    import threading
    threading.Thread(target=_run_after_review, args=(run, False, req.feedback), daemon=True).start()
    return {"run_id": run_id, "phase": "running_main"}


@router.get("/queue/{project_name}")
async def get_queue(project_name: str):
    """Get queue status for a project."""
    return {"project": project_name, "queue": run_manager.get_queue_info(project_name)}
