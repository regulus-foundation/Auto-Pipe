# Auto-Pipe TODO List

Last updated: 2026-03-20

---

## 1. Bugs

| # | Item | Description |
|---|------|-------------|
| B-1 | `source_code` state empty | Console executor writes files directly to project but `parse_code_output` returns 0 from stdout. State tracking vs actual files mismatch |
| B-2 | Test error log lacking detail | `run_tests_node` shows only "exit code 1", actual test failure details not captured |

---

## 2. Web UI

| # | Item | Description |
|---|------|-------------|
| W-1 | Mermaid diagram component | Pipeline graph visualization in the UI |
| W-2 | Phase tracker component | Visual pipeline stage progress (stage dots + connectors) |
| W-3 | Run history persistence | Save run history to PostgreSQL (currently in-memory, lost on restart) |
| W-4 | Settings page | Environment config, model selection, project management |

---

## 3. Pipeline

| # | Item | Description |
|---|------|-------------|
| P-1 | `fix_code` dedicated prompt | Currently reuses `develop_code.md` — needs its own template focused on build errors |
| P-2 | `fix_code` scope awareness | fix_code repeats "already done" instead of focusing on the actual error |
| P-3 | Error handling improvements | LLM timeout exponential backoff, Console fallback, tool retry |
| P-4 | Incident response pipeline | Separate graph — log collection → root cause → action plan → execute |

---

## 4. Channel Gateway

| # | Item | Description |
|---|------|-------------|
| G-1 | Telegram bot (text) | Text commands for pipeline trigger + status + approval |
| G-2 | Voice support | Whisper STT → text → Intent Parser |
| G-3 | Human-in-the-Loop via channel | Design/review approval from Telegram |
| G-4 | Multi-channel expansion | Slack, Discord adapters |

---

## 5. Infrastructure

| # | Item | Description |
|---|------|-------------|
| I-1 | Run history DB table | PostgreSQL persistence for execution history + log references |
| I-2 | Git integration | Auto branch + PR creation after pipeline completion |
| I-3 | RAG integration | Vector DB for internal code/wiki reference in prompts |
| I-4 | Prompt A/B testing | Compare quality across different prompt templates |
| I-5 | Learning loop | Accumulate review/incident data → improve next project |

---

## Priority

```
1st: B-1, B-2, P-1, P-2   — fix_code quality (practical blocker)
2nd: W-3, I-1              — Run history persistence (restart 시 데이터 유지)
3rd: W-1, W-2              — UI components (Mermaid, Phase tracker)
4th: G-1                   — Telegram bot MVP
5th: I-2                   — Git auto-PR
```
