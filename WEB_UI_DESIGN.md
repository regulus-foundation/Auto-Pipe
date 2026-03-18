# Auto-Pipe Web UI Design

The Web UI is the **control tower** of the Auto-Pipe system.
All pipeline execution, decision-making, and monitoring happens through the web.

---

## 1. Role

```
Web UI = Input + Monitoring + Decision-making + Logs

+-----------------------------------------------------------+
|                    Auto-Pipe Web UI                         |
|                                                             |
|  +---------+  +----------+  +----------+  +----------+     |
|  | Input   |  | Monitor  |  | Decision |  | Logs     |     |
|  |         |  |          |  |          |  |          |     |
|  | Project |  | Realtime |  | Design   |  | Exec log |     |
|  | path    |  | progress |  | approval |  | Error log|     |
|  | Require |  | Per-step |  | Review   |  | LLM log  |     |
|  | ments   |  | status   |  | approval |  | Cost     |     |
|  +---------+  +----------+  +----------+  +----------+     |
+-----------------------------------------------------------+
```

---

## 2. Tech Stack

| Item | Choice | Reason |
|------|--------|--------|
| Framework | **Streamlit** | Python-based, same language as LangGraph, rapid prototyping |
| Realtime updates | Streamlit streaming + `st.empty()` | Reflects LangGraph `stream()` results in realtime |
| State management | `st.session_state` | Persists across page transitions/rerenders |
| Diagrams | Mermaid.js | Graph visualization (LangGraph `draw_mermaid()` integration) |
| Port | 8502 | Default execution port |

---

## 3. Page Structure

```
Sidebar                          Main Area
+--------------+                +------------------------------+
|              |                |                              |
|  Auto-Pipe   |                |  (Selected page rendering)   |
|              |                |                              |
|  ----------  |                |                              |
|              |                |                              |
|  * Bootstrap | <-- Project    |  Bootstrap / Pipeline /      |
|  o Pipeline  |    analysis    |  Examples                    |
|  o Examples  |                |                              |
|              |                |                              |
|  ----------  |                |                              |
|              |                |                              |
|  Configured  |                |                              |
|  projects    |                |                              |
|   my-erp     |                |                              |
|   my-api     |                |                              |
|              |                |                              |
+--------------+                +------------------------------+
```

### 3.1 Bootstrap Page (Implemented)

Project registration and analysis page.

```
Phase: input -> analyzing -> review -> generating -> done

[input]
  +------------------------------------------+
  |  Existing projects: [my-erp] [my-api]    | <-- click to review
  |  ----------------------------------------|
  |  New project analysis                    |
  |  Project path: [/path/to/project      ]  |
  |  [Start Analysis]                        |
  +------------------------------------------+

[analyzing]
  +------------------------------------------+
  |  Bootstrap pipeline running...           |
  |  +------------------------------------+  |
  |  | [10:14:01] scan_files -- complete  |  |  <-- live log
  |  | [10:14:15] analyze_deps -- ...     |  |
  |  | [10:14:30] Step 1/4: dependencies  |  |
  |  +------------------------------------+  |
  +------------------------------------------+

[review]
  +------------------------------------------+
  |  Project: my-erp                         |
  |                                          |
  |  Source 834 | Test 156 | 98K LOC         | <-- metric cards
  |                                          |
  |  [Lang/FW] [Structure] [Build] [Test]    | <-- tabs
  |                                          |
  |  +------------------------------------+  |
  |  |  Java 72% ############....         |  |
  |  |  YAML 15% ###............         |  |
  |  |  SQL   8% ##.............         |  |
  |  +------------------------------------+  |
  |                                          |
  |  Deep Analysis:                          |
  |  [Dependencies] [Architecture] [Testing] |
  |  [Summary]                               |
  |                                          |
  |  [Generate Config] [Re-analyze] [Cancel] |
  +------------------------------------------+

[done]
  +------------------------------------------+
  |  my-erp Bootstrap complete!              |
  |                                          |
  |  Generated files:                        |
  |    projects/my-erp/                      |
  |    +-- project_analysis.yaml             |
  |    +-- pipeline.yaml                     |
  |    +-- prompts/ (6 templates)            |
  |    +-- analysis/ (4 documents)           |
  |                                          |
  |  [Go to Pipeline] [Analyze another]      |
  +------------------------------------------+
```

### 3.2 Pipeline Page (Implemented)

Requirements input, pipeline execution, and monitoring.

```
Phase: input -> running_design -> design_review -> running_main
       -> code_review -> done

[input]
  +------------------------------------------+
  |  Project: [my-erp v]                     |
  |                                          |
  |  Requirements:                           |
  |  +------------------------------------+  |
  |  | Implement user login API            |  |
  |  | - JWT token auth                    |  |
  |  | - Lock account after 5 failures     |  |
  |  +------------------------------------+  |
  |                                          |
  |  [Run Pipeline]                          |
  +------------------------------------------+

[running_design]
  +------------------------------------------+
  |  Pre-build check: passed                 |
  |  Phase 1: Design                         |
  |  +------------------------------------+  |
  |  | [10:13:34] Requirements analysis.. |  |  <-- live log
  |  | [10:13:49] Design generation...    |  |
  |  | [10:14:54] Design complete         |  |
  |  +------------------------------------+  |
  +------------------------------------------+

[design_review]
  +------------------------------------------+
  |  Design Review                           |
  |  Project: my-erp                         |
  |                                          |
  |  [Requirements Analysis] [Full Design]   | <-- tabs
  |                                          |
  |  +------------------------------------+  |
  |  | # Detailed Design                  |  |
  |  | ## API Design                      |  |
  |  | POST /api/v1/auth/login            |  |
  |  | ...                                |  |
  |  | ## DB Schema                       |  |
  |  | ...                                |  |
  |  +------------------------------------+  |
  |                                          |
  |  [Approve] [Request Changes] [Cancel]    |
  +------------------------------------------+

[running_main]
  +------------------------------------------+
  |  Phase 2: Development... (35%)           |
  |  +------------------------------------+  |
  |  | develop_code -- coding...          |  |
  |  | write_tests -- writing tests...    |  |
  |  +------------------------------------+  |
  |                                          |
  |  Phase 3: Build/Test (cycle)             |
  |  Pre-existing errors: 2 (will skip fix)  |
  +------------------------------------------+

[done]
  +------------------------------------------+
  |  my-erp Pipeline complete!               |
  |                                          |
  |  [Full execution log]                    |
  |  [Error log]                             |
  +------------------------------------------+
```

### 3.3 Monitor Page (Planned)

Realtime monitoring of running pipelines and history.

```
+----------------------------------------------+
|  Running                                      |
|  +------------------------------------------+|
|  | my-erp | Login API | Phase 3 building    ||
|  | Start: 14:30 | Elapsed: 12min            ||
|  +------------------------------------------+|
|                                               |
|  Recent Executions                            |
|  +------------------------------------------+|
|  | my-erp | Signup API | Complete | 23min   ||
|  | my-api | Payment    | Failed  | 45min    ||
|  +------------------------------------------+|
|                                               |
|  Log Viewer                                   |
|  +------------------------------------------+|
|  | 14:30:01 [Pre-check] Build passed        ||
|  | 14:30:15 [Design] Requirements analysis  ||
|  | 14:31:05 [Design] Complete -> approval    ||
|  | 14:32:00 [Design] User approved           ||
|  | ...                                       ||
|  +------------------------------------------+|
+----------------------------------------------+
```

---

## 4. Web UI <-> LangGraph Integration

### 4.1 Realtime Streaming

```python
# LangGraph stream() -> Streamlit realtime display
live_lines = []
live_container = st.empty()

def on_live_output(line: str):
    live_lines.append(line)

set_log_callback(on_live_output)

with st.status("Pipeline running...", expanded=True) as status:
    for chunk in graph.stream(initial_state, config, stream_mode="updates"):
        # Main thread: display logs
        if live_lines:
            live_container.code("\n".join(live_lines[-30:]), language="markdown")

        for node_name, update in chunk.items():
            step = update.get("current_step", "")
            status.update(label=f"{node_name} -- {step}")
```

### 4.2 Human-in-the-Loop

```python
# 1. Graph runs -> stops at interrupt point
# (graph.stream() completes, state saved via checkpointer)

# 2. Web shows approval UI (session_state preserves graph + thread_id)
if st.button("Approve"):
    graph.update_state(config, {"design_approved": True}, as_node="generate_design")
    # Resume execution
    for chunk in graph.stream(None, config, stream_mode="updates"):
        ...
```

### 4.3 File Logging

```python
# File logger creates per-execution log files
# projects/{name}/log/pipeline-{YYYYMMDD_HHmmss}.log
# projects/{name}/log/bootstrap-{YYYYMMDD_HHmmss}.log

from core.file_logger import start_file_logger, stop_file_logger

file_logger = start_file_logger(project_name, "pipeline")
# ... pipeline runs, _emit_log() writes to both UI callback and file ...
stop_file_logger(success=True)
```

---

## 5. Implementation Status

### 5.1 Implemented

| File | Role | Status |
|------|------|--------|
| `web/app.py` | Main entry + sidebar navigation | Done |
| `web/pages/bootstrap.py` | Bootstrap page (input -> analyze -> review -> config) | Done |
| `web/pages/pipeline.py` | Pipeline page (requirements -> design -> dev -> done) | Done |
| `web/pages/examples.py` | LangGraph learning examples (9 patterns) | Done |
| `core/file_logger.py` | Per-project file logging | Done |

### 5.2 Planned

| File | Role | Status |
|------|------|--------|
| `web/pages/monitor.py` | Realtime monitor + log viewer | Planned |
| `web/pages/history.py` | Execution history browser | Planned |
| `web/components/mermaid.py` | Mermaid diagram component | Planned |
| `web/components/log_viewer.py` | Log file viewer component | Planned |
| `web/components/phase_tracker.py` | Pipeline progress display | Planned |

---

## 6. Run

```bash
# Start
./run.sh
# or
streamlit run web/app.py --server.port 8502 --server.headless true

# Access
http://localhost:8502
```
