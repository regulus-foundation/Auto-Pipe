# Auto-Pipe Automation System -- Architecture Overview

---

## 1. System Overview

```
+-------------------------------------------------------------------+
|                       Auto-Pipe System                             |
|                                                                    |
|  [ Layer 0: Bootstrap Pipeline (one-time) ]                        |
|                                                                    |
|  "Just input project path - auto-analyzes and generates config"    |
|                                                                    |
|  scan_files --> analyze_deps --> analyze_arch --> analyze_tests     |
|    (tool)       (console)       (console)        (console)         |
|      --> analyze_summary --> [Human Review] --> generate_config     |
|            (console)                              (api)            |
|                                                                    |
|  >> BOOTSTRAP_DESIGN.md                                            |
|                                                                    |
|  ------------ generated once | used repeatedly ------------        |
|                                                                    |
|  [ Layer 1: Auto-Pipe Pipeline (repeated execution) ]              |
|                                                                    |
|  pre_build_check --> Design --> [Human Review] --> Dev+Test         |
|     (tool)        (api+console)                  (console||)       |
|       --> Build+Test --> Review --> [Human Review] --> Docs         |
|          (tool,cycle)  (api||)                      (api||)        |
|                                                                    |
|  >> AUTO_PIPE_DESIGN.md                                            |
|                                                                    |
|  [ Layer 2: Shared Infrastructure ]                                |
|                                                                    |
|  [Executor]  [Checkpointer]  [Streaming]    [File Logger]          |
|   api/        state save      realtime       per-project           |
|   console/    pause/resume    progress       timestamped logs      |
|   tool                                                             |
|                                                                    |
|  [Web UI]         [Project Detection]                              |
|   control tower    App: Java/Node/Python/Go/Rust/Flutter           |
|   input/monitor    IaC: Terraform/Helm/Kustomize/Ansible           |
|   decisions/logs                                                   |
|                                                                    |
|  >> WEB_UI_DESIGN.md                                               |
|                                                                    |
+-------------------------------------------------------------------+
```

---

## 2. Document Map

| Document | Role | Content |
|----------|------|---------|
| **ARCHITECTURE_OVERVIEW.md** (this) | Overview | Structure, document relations, tech decisions, execution flow |
| **BOOTSTRAP_DESIGN.md** | Bootstrap detail | Project analysis + config generation pipeline |
| **AUTO_PIPE_DESIGN.md** | Auto-Pipe detail | Design->Dev->Test->Review->Docs pipeline |
| **WEB_UI_DESIGN.md** | Web UI detail | Page structure, realtime monitoring, Human-in-the-Loop UI |
| **CHANNEL_GATEWAY_DESIGN.md** | Channel Gateway | Multi-channel interface (Telegram, Slack, voice) |
| **TODO_LIST.md** | Task tracking | Current status, priorities, roadmap |

```
ARCHITECTURE_OVERVIEW.md     <-- start here (this doc)
        |
        +--> BOOTSTRAP_DESIGN.md      <-- Layer 0 detail
        |
        +--> AUTO_PIPE_DESIGN.md      <-- Layer 1 detail
        |
        +--> WEB_UI_DESIGN.md         <-- Web UI detail
        |
        +--> CHANNEL_GATEWAY_DESIGN.md <-- Layer 3 (future)
```

---

## 3. Execution Flow

### 3.1 One-time: Bootstrap

```
User: "Analyze this project"
         |
         v
+-- Bootstrap Pipeline -----------------------------------------+
|                                                                |
|  1. scan_files (tool)         <-- local file scan, free        |
|         |                                                      |
|         v                                                      |
|  2. analyze_deps (console)    <-- Step 1/4: dependencies       |
|  3. analyze_arch (console)    <-- Step 2/4: architecture       |
|  4. analyze_tests (console)   <-- Step 3/4: test strategy      |
|  5. analyze_summary (console) <-- Step 4/4: overall assessment |
|         |                                                      |
|         v                                                      |
|  6. [Human Review]            <-- review analysis results      |
|         |                                                      |
|         v                                                      |
|  7. generate_config (api)     <-- lightweight config gen       |
|         |                        + Deep Analysis injected      |
|         v                        into prompt templates         |
|  8. Save to projects/{name}/                                   |
|                                                                |
+-------------------+--------------------------------------------+
                    |
                    v
     Output: projects/{name}/
             +-- project_analysis.yaml
             +-- pipeline.yaml
             +-- prompts/*.md
             +-- analysis/*.md
```

### 3.2 Repeated: Auto-Pipe Pipeline

```
User: "Implement this requirement"
         |
         v
+-------------------------------------------------------------------+
|                                                                    |
|  Load projects/{name}/ config                                      |
|         |                                                          |
|         v                                                          |
|  Pre-build check (tool)        <-- baseline build+test status      |
|         |                                                          |
|         v                                                          |
|  Phase 1: Design                                                   |
|    analyze_requirements (api)  <-- lightweight analysis            |
|    generate_design (console)   <-- reads project code directly     |
|         |                                                          |
|         v                                                          |
|  [Human Review]                <-- design approval                 |
|         |                                                          |
|         v                                                          |
|  Phase 2: Dev+Test (parallel)  <-- console (code gen)              |
|         |                                                          |
|         v                                                          |
|  Phase 3: Build+Test (cycle)                                       |
|    build (tool) --> run_tests (tool) --> check_test_result          |
|      ^                                     |                       |
|      |   pre-existing error? --> skip      |                       |
|      +-- fix_code (console) <-- new error--+                       |
|                                     pass --> Phase 4                |
|         |                                                          |
|         v                                                          |
|  Phase 4: Review (parallel)    <-- api (quality + security)        |
|         |                                                          |
|         v                                                          |
|  [Human Review]                <-- review approval                 |
|         |                                                          |
|         v                                                          |
|  Phase 5: Docs (parallel)      <-- api (docs gen)                  |
|         |                                                          |
|         v                                                          |
|  Package + Done                                                    |
|                                                                    |
+-------------------------------------------------------------------+
```

---

## 4. Technical Decisions (ADR)

### 4.1 Executor 3-Type Separation

| Executor | Use Case | Implementation | Cost Model | Nodes |
|----------|----------|----------------|------------|-------|
| **api** | Lightweight analysis/gen | OpenAI/Claude API | Per-token | Requirements, review, docs, config gen |
| **console** | Bulk code gen/analysis | Claude Code CLI (`claude --print`) | Subscription (fixed) | Project analysis, design, code dev, test writing |
| **tool** | Local execution | `subprocess` | Free | Build, test, file ops |

**Console Executor**:
- Calls Claude Code CLI via `subprocess` (`claude --print --dangerously-skip-permissions`)
- Auto fallback to API(gpt-4o) if CLI not installed
- Unlimited tokens under subscription -> ideal for bulk code generation

**Interface**: `core/executor.py` with `BaseExecutor` abstract class + `create_executor()` factory.
All executors share `run(prompt_or_command) -> ExecutorResult` interface.

### 4.2 Why LangGraph

```
Simple scripts       ->  no branching/loops, restart from scratch on error
LangChain only       ->  linear chains only, hard to manage state
LangGraph            ->  conditional branching, loops, parallel, state save,
                         pause/resume all supported
                         -> naturally expresses all Auto-Pipe patterns
```

| Auto-Pipe Requirement | LangGraph Feature |
|-----------------------|-------------------|
| Human review after design | Human-in-the-Loop (interrupt_before) |
| Dev/test in parallel | Parallel (Annotated + operator.add) |
| Test fail -> fix -> rerun | Cycle (conditional_edges -> self) |
| Pre-existing error skip | Conditional routing in check_test_result |
| Realtime progress | Streaming (stream_mode="updates") |
| Pause and resume | Checkpointer (MemorySaver -> SQLite -> Postgres) |

### 4.3 Checkpointer Strategy

```
Dev phase:            MemorySaver (in-memory, reset on restart)  <-- current
        |
        v
Local production:     SqliteSaver (file-based, persists on restart)
        |
        v
Team production:      PostgresSaver (server-based, multi-user)
```

### 4.4 Bootstrap Separation Decision

1. **Different execution cycle** -- Bootstrap is per-project once, Auto-Pipe repeats per requirement
2. **Different executor needs** -- Bootstrap requires Console (deep analysis), Auto-Pipe is mixed
3. **Separation of concerns** -- "understanding a project" vs "building code" are separate responsibilities
4. **Reusability** -- Bootstrap output (projects/{name}/) works with any pipeline

---

## 5. Supported Project Types

### Application

| Type | Detection Files | Build | Test |
|------|----------------|-------|------|
| Java (Spring Boot) | build.gradle + spring-boot markers | `./gradlew build` | `./gradlew test` |
| Node.js (NestJS/Express/Next) | package.json + framework markers | `npm run build` | `npm test` |
| Python (Django/FastAPI/Flask) | requirements.txt + framework markers | `pip install` | `pytest` |
| Go | go.mod | `go build ./...` | `go test ./...` |
| Rust | Cargo.toml | `cargo build` | `cargo test` |
| Flutter | pubspec.yaml | flutter/dart | -- |

### Infrastructure / IaC

| Type | Detection Files | Validate | Plan/Dry-run |
|------|----------------|----------|--------------|
| Terraform | main.tf, variables.tf | `terraform validate` | `terraform plan` |
| Helm | Chart.yaml | `helm lint` | `helm template --dry-run` |
| Kustomize | kustomization.yaml | `kustomize build` | `kubectl --dry-run` |
| Ansible | ansible.cfg, site.yml | `ansible-lint` | `ansible-playbook --check` |
| ArgoCD | application.yaml + argoproj.io | -- | -- |

All types share the same pipeline flow. Bootstrap detects the type and configures appropriate commands in `pipeline.yaml`.

---

## 6. Data Flow

```
[Input]                   [Bootstrap]                    [Auto-Pipe]
                          (one-time)                     (repeated)

Project path      -->   project_analysis.yaml   --+
                        + analysis/*.md            |
                        + Deep Analysis            +--->  Load pipeline.yaml
                          (arch, conventions,       |     Load prompts/*.md
                           test strategy)           |     (with Deep Analysis context)
                                                   |          |
Requirements doc  ----------------------------------------->  |
                                                              v
                                                     Pre-build check
                                                     Design -> Dev -> Build/Test
                                                     -> Review -> Docs
                                                              |
                                                              v
                                                     [Deliverables]
                                                     - Modified project code
                                                     - Design docs
                                                     - Execution logs
```

---

## 7. Project Structure (Current)

```
Auto-Pipe/
+-- ARCHITECTURE_OVERVIEW.md          # Architecture overview (this doc)
+-- BOOTSTRAP_DESIGN.md               # Bootstrap pipeline design
+-- AUTO_PIPE_DESIGN.md               # Auto-Pipe pipeline design
+-- WEB_UI_DESIGN.md                  # Web UI design
+-- CHANNEL_GATEWAY_DESIGN.md         # Channel gateway design (future)
+-- TODO_LIST.md                      # Task tracking
+-- CLAUDE.md                         # Project context for AI assistants
+-- requirements.txt                  # Python dependencies
+-- run.sh                            # Launcher (Docker + Backend + Frontend)
+-- docker-compose.yml                # PostgreSQL + Langfuse services
+-- .gitignore                        # Security-aware gitignore
|
+-- core/                             # Shared infrastructure
|   +-- analyzer.py                   # Project analyzer (file scan + detection rules)
|   +-- config_generator.py           # pipeline.yaml + prompt template generator
|   +-- config_loader.py              # pipeline.yaml loader -> Executor mapping
|   +-- executor.py                   # Executor abstraction (api/console/tool)
|   +-- llm.py                        # Central LLM instance manager
|   +-- file_logger.py                # Per-project file logging
|   +-- langfuse_callback.py          # Langfuse observability handler
|
+-- bootstrap/                        # Bootstrap Pipeline (Layer 0)
|   +-- graph.py                      # LangGraph: scan -> analyze -> review -> config
|
+-- pipeline/                         # Auto-Pipe Pipeline (Layer 1)
|   +-- graph.py                      # LangGraph: 5-phase pipeline builder
|   +-- state.py                      # TypedDict state with reducers
|   +-- utils.py                      # Common utils (logging, prompt, code parsing)
|   +-- nodes/
|       +-- design.py                 # Phase 1: Requirements (api) + Design (console)
|       +-- develop.py                # Phase 2: Code dev + test writing (console)
|       +-- build_test.py             # Phase 3: Pre-check + build/test/fix cycle
|       +-- review.py                 # Phase 4: Quality + security review (api)
|       +-- docs.py                   # Phase 5: Docs + packaging (api)
|
+-- web/                              # FastAPI Backend (JSON API + SSE)
|   +-- app.py                        # FastAPI entry point + CORS
|   +-- run_manager.py                # Per-run state + async log queue
|   +-- routes/
|       +-- bootstrap_api.py          # Bootstrap REST API + SSE
|       +-- pipeline_api.py           # Pipeline REST API + SSE
|
+-- frontend/                         # Next.js Frontend (React + Tailwind)
|   +-- src/app/                      # App Router pages (bootstrap, pipeline)
|   +-- src/components/               # Reusable UI components
|   +-- src/lib/                      # API helpers, SSE hook
|
+-- projects/                         # Per-project output
    +-- {name}/
        +-- project_analysis.yaml     # Analysis results
        +-- pipeline.yaml             # Pipeline config
        +-- prompts/*.md              # Project-specific prompt templates
        +-- analysis/*.md             # Deep analysis documents
        +-- log/                      # Execution logs (timestamped)
        +-- output/                   # Generated artifacts
```

---

## 8. Cost Structure

### 8.1 Bootstrap (one-time)

| Step | Executor | Est. Tokens | Cost |
|------|----------|-------------|------|
| Project analysis (4 steps) | console | 100K+ | Subscription (W0) |
| Config generation | api | ~5,000 | ~W50 |
| **Total** | | | **~W50** |

### 8.2 Auto-Pipe (per execution)

| Phase | Executor | Est. Tokens | Cost |
|-------|----------|-------------|------|
| Requirements analysis | api | ~3,000 | ~W30 |
| Design generation | console | 50K+ | Subscription (W0) |
| Code development | console | 50K+ | Subscription (W0) |
| Test writing | console | 30K+ | Subscription (W0) |
| Build/Test | tool | 0 | W0 |
| Code fix (on failure) | console | 20K+ | Subscription (W0) |
| Code review | api | ~5,000 | ~W50 |
| Security check | api | ~3,000 | ~W30 |
| Documentation | api | ~5,000 | ~W50 |
| **Total** | | | **~W160** |

**Key**: Design + code generation (most expensive) runs on Console (subscription) -> 80%+ cost reduction.

---

## 9. Core Principles

1. **Console for heavy work, API for light work** -- Cost optimization core
2. **Bootstrap once, Pipeline repeats** -- Separation of concerns
3. **Config-driven** -- Change pipeline.yaml to change behavior (no code change needed)
4. **Human always decides** -- Human-in-the-Loop balances automation and control
5. **Safe to interrupt** -- Checkpointer enables resume from anywhere
6. **Project-aware** -- Bootstrap understands the project and creates tailored config
7. **Pre-existing errors are not pipeline's fault** -- Pre-build check distinguishes baseline failures
