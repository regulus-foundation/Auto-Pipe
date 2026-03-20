# Auto-Pipe TODO List

Last updated: 2026-03-20

---

## 1. Bugs / Fixes

| # | Item | Status | Description |
|---|------|--------|-------------|
| B-1 | Build error log not shown | Done | Added `_emit_log` with error details in `build_node` |
| B-2 | `fix_code` prompt `{design_spec}` not substituted | Done | Added `design_spec` to `render_prompt` variables |
| B-3 | `source_code` state empty dict | Open | Console executor writes files directly to project, `parse_code_output` returns 0 from stdout summary. State tracking vs actual files mismatch |
| B-4 | Bootstrap language detection wrong | Done | Added `PRIMARY_LANG_EXTS` (programming-only) + framework-based override |
| B-5 | `generate_config` ignoring Deep Analysis | Done | Now passes `deep_analysis` to prompt template generation |
| B-6 | Test error log lacking detail | Open | `run_tests_node` shows only "exit code 1", actual test failure details not captured |

---

## 2. Recently Completed

| # | Item | Date | Description |
|---|------|------|-------------|
| C-1 | File logging system | 03-17 | `projects/{name}/log/pipeline-{ts}.log`, `bootstrap-{ts}.log` |
| C-2 | Design node consolidation | 03-18 | 3 API nodes -> 1 Console node (`generate_design`). Reads project code directly |
| C-3 | Pre-build + pre-test check | 03-18 | Baseline check before pipeline. Pre-existing errors skip fix loop |
| C-4 | Infra/IaC project support | 03-18 | Terraform, Helm, Kustomize, Ansible, ArgoCD detection + command mapping |
| C-5 | Deep Analysis in prompts | 03-18 | Architecture/conventions/test strategy injected into prompt templates |
| C-6 | Web UI: Streamlit → FastAPI + Next.js | 03-20 | Full migration to FastAPI backend (JSON API + SSE) + Next.js React frontend |
| C-7 | Dark theme design system | 03-20 | Vercel/Linear/shadcn-inspired: zinc palette, Inter + JetBrains Mono, component library |
| C-8 | History page | 03-20 | Execution history table + project log viewer with pagination |
| C-9 | Pipeline queuing | 03-20 | Per-project FIFO queue, sequential execution, queue status in UI |
| C-10 | Design phase scoping | 03-20 | API pre-analysis extracts relevant code paths before Console design generation |
| C-11 | Command palette (Cmd+K) | 03-20 | Glassmorphism overlay, keyboard navigation |
| C-12 | Toast notifications | 03-20 | Success/error/info with auto-dismiss |
| C-13 | Skeleton loading | 03-20 | Shimmer animation for data-fetching pages |
| C-14 | SSE auto-reconnect | 03-20 | Exponential backoff retry on connection loss |
| C-15 | PostgresSaver checkpointer | 03-18 | LangGraph state persistence via PostgreSQL |

---

## 3. Web UI

| # | Item | File | Status | Description |
|---|------|------|--------|-------------|
| W-1 | Mermaid diagram | `frontend/src/components/MermaidDiagram.tsx` | Open | Pipeline graph visualization component |
| W-2 | Phase tracker | `frontend/src/components/PhaseTracker.tsx` | Open | Visual pipeline stage progress (stage dots + connectors) |
| W-3 | Run history persistence | DB table | Open | Save run history to PostgreSQL (currently in-memory only) |
| W-4 | Settings page | `frontend/src/app/settings/` | Open | Environment config, model selection, project management |

---

## 4. Pipeline Features (AUTO_PIPE_DESIGN.md)

| # | Item | Status | Description |
|---|------|--------|-------------|
| P-1 | Phase 6: Incident response | Open | Separate graph -- log collection -> root cause -> action plan -> execute |
| P-2 | Error handling improvements | Open | LLM timeout exponential backoff, Console fallback, tool retry |
| P-3 | `fix_code` dedicated prompt | Open | Currently reuses `develop_code.md` -> needs dedicated `fix_code.md` template |
| P-4 | fix_code scope awareness | Open | fix_code should focus on build errors, not repeat "already done" |

---

## 5. Channel Gateway (CHANNEL_GATEWAY_DESIGN.md)

| # | Phase | Item | Status | Description |
|---|-------|------|--------|-------------|
| G-1 | Phase 1 | Telegram bot (text) | Open | Text commands for pipeline trigger + status + approval |
| G-2 | Phase 2 | Voice support | Open | Whisper STT -> text -> Intent Parser |
| G-3 | Phase 3 | Human-in-the-Loop via channel | Open | Design/review approval from Telegram |
| G-4 | Phase 4 | Multi-channel expansion | Open | Slack, Discord adapters |

---

## 6. Infrastructure / Expansion (ARCHITECTURE_OVERVIEW.md)

| # | Item | Timeline | Status | Description |
|---|------|----------|--------|-------------|
| I-1 | Multi-project support | Mid | Done | `projects/{name}/` structure |
| I-2 | Execution history persistence | Mid | Open | PostgreSQL table + History page integration |
| I-3 | Git integration (auto PR) | Long | Open | Auto branch + PR after pipeline completion |
| I-4 | Slack/Teams notification | Long | Open | Integrate with channel gateway |
| I-5 | RAG integration | Long | Open | Vector DB for internal code/wiki reference |
| I-6 | Prompt A/B testing | Long | Open | Compare quality across different prompts |
| I-7 | Learning loop | Long | Open | Accumulate review/incident data -> improve next project |

---

## Priority Suggestion

```
1st: B-3, B-6, P-4  -- fix_code quality (practical blocker)
2nd: P-3             -- fix_code dedicated prompt
3rd: W-3, I-2        -- Run history persistence (DB)
4th: W-1, W-2        -- Mermaid diagram + Phase tracker
5th: G-1             -- Telegram bot MVP
```
