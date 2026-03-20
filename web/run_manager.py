"""Per-run state management + log streaming + project queuing

Each pipeline run gets its own log queue for SSE streaming.
Per-project queue ensures only one pipeline runs at a time per project.
"""

import asyncio
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class RunType(str, Enum):
    BOOTSTRAP = "bootstrap"
    PIPELINE = "pipeline"


@dataclass
class RunState:
    run_id: str
    run_type: RunType
    phase: str = ""
    graph: Any = None
    thread_id: str = ""
    state: dict = field(default_factory=dict)
    log_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    resume_event: threading.Event = field(default_factory=threading.Event)
    approval_data: dict = field(default_factory=dict)
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    queue_position: int = 0  # 0 = running, 1+ = waiting
    _loop: Optional[asyncio.AbstractEventLoop] = field(default=None, repr=False)

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def push_log(self, message: str):
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self.log_queue.put_nowait, {"type": "log", "data": message})

    def push_event(self, event_type: str, data: Any = None):
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                self.log_queue.put_nowait, {"type": event_type, "data": data}
            )

    def touch(self):
        self.updated_at = datetime.now().isoformat()

    def to_summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "run_type": self.run_type.value,
            "phase": self.phase,
            "project_name": self.state.get("project_name") or self.state.get("scan_result", {}).get("project", {}).get("name", ""),
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "queue_position": self.queue_position,
        }


@dataclass
class QueuedTask:
    """A task waiting in the project queue."""
    run: RunState
    start_fn: Callable  # function to call when it's this task's turn
    start_args: tuple = ()


class ProjectQueue:
    """Per-project FIFO queue. Only one run executes at a time per project."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self._lock = threading.Lock()
        self._queue: deque[QueuedTask] = deque()
        self._active: Optional[QueuedTask] = None

    @property
    def active_run(self) -> Optional[RunState]:
        return self._active.run if self._active else None

    @property
    def size(self) -> int:
        return len(self._queue) + (1 if self._active else 0)

    def enqueue(self, task: QueuedTask) -> int:
        """Add a task. Returns queue position (0 = starts immediately)."""
        with self._lock:
            if self._active is None:
                # No active run — start immediately
                self._active = task
                task.run.queue_position = 0
                self._start_active()
                return 0
            else:
                # Queue behind active run
                pos = len(self._queue) + 1
                task.run.queue_position = pos
                task.run.phase = "queued"
                self._queue.append(task)
                return pos

    def complete_active(self):
        """Mark active run as done, start next in queue if any."""
        with self._lock:
            self._active = None
            if self._queue:
                next_task = self._queue.popleft()
                self._active = next_task
                next_task.run.queue_position = 0
                # Update positions for remaining
                for i, t in enumerate(self._queue):
                    t.run.queue_position = i + 1
                self._start_active()

    def _start_active(self):
        """Start the active task in a background thread."""
        task = self._active
        if task:
            thread = threading.Thread(
                target=self._run_task,
                args=(task,),
                daemon=True,
            )
            thread.start()

    def _run_task(self, task: QueuedTask):
        try:
            task.start_fn(task.run, *task.start_args)
        except Exception as e:
            task.run.error = str(e)
            task.run.phase = "error"
            task.run.push_event("error", {"message": str(e)})
        finally:
            # Only auto-advance if the run is truly done (done or error)
            # If it's waiting for human approval, don't advance
            if task.run.phase in ("done", "error"):
                self.complete_active()

    def get_queue_info(self) -> list[dict]:
        """Return queue status for API."""
        result = []
        if self._active:
            result.append({"run_id": self._active.run.run_id, "position": 0, "phase": self._active.run.phase})
        for i, t in enumerate(self._queue):
            result.append({"run_id": t.run.run_id, "position": i + 1, "phase": "queued"})
        return result


class RunManager:
    """Manages all runs + per-project queues."""

    def __init__(self):
        self._runs: dict[str, RunState] = {}
        self._project_queues: dict[str, ProjectQueue] = {}
        self._lock = threading.Lock()

    def create_run(self, run_type: RunType) -> RunState:
        run_id = str(uuid.uuid4())[:8]
        run = RunState(run_id=run_id, run_type=run_type)
        with self._lock:
            self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> Optional[RunState]:
        return self._runs.get(run_id)

    def remove_run(self, run_id: str):
        with self._lock:
            self._runs.pop(run_id, None)

    def list_runs(self, run_type: Optional[RunType] = None) -> list[RunState]:
        runs = list(self._runs.values())
        if run_type:
            runs = [r for r in runs if r.run_type == run_type]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def get_project_queue(self, project_name: str) -> ProjectQueue:
        with self._lock:
            if project_name not in self._project_queues:
                self._project_queues[project_name] = ProjectQueue(project_name)
            return self._project_queues[project_name]

    def enqueue_pipeline(self, run: RunState, start_fn: Callable, *args) -> int:
        """Enqueue a pipeline run for a project. Returns queue position."""
        project_name = run.state.get("project_name", "unknown")
        queue = self.get_project_queue(project_name)
        task = QueuedTask(run=run, start_fn=start_fn, start_args=args)
        return queue.enqueue(task)

    def complete_pipeline(self, run: RunState):
        """Signal that a pipeline run is fully done (advance queue)."""
        project_name = run.state.get("project_name", "unknown")
        if project_name in self._project_queues:
            self._project_queues[project_name].complete_active()

    def get_queue_info(self, project_name: str) -> list[dict]:
        if project_name in self._project_queues:
            return self._project_queues[project_name].get_queue_info()
        return []


# Module-level singleton
run_manager = RunManager()
