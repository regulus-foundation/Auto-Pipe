# File-to-UI Impact Mapping

This document defines which backend file changes should trigger which UI updates.
Used by the Dev Pipeline to determine what to regenerate.

## Core Mappings

| Backend File | Impact Scope | UI Files Affected |
|---|---|---|
| `pipeline/state.py` | All pipeline UI | `pipeline/running.html`, `pipeline/design_review.html`, `pipeline/code_review.html`, `pipeline/done.html` |
| `pipeline/graph.py` | Pipeline flow | `pipeline/running.html`, `web/routes/pipeline_api.py` |
| `pipeline/nodes/design.py` | Design phase | `pipeline/design_review.html` |
| `pipeline/nodes/develop.py` | Code generation | `pipeline/code_review.html`, `pipeline/done.html` |
| `pipeline/nodes/build_test.py` | Build/test phase | `pipeline/running.html` (progress display) |
| `pipeline/nodes/review.py` | Review phase | `pipeline/code_review.html` |
| `pipeline/nodes/docs.py` | Docs phase | `pipeline/done.html` |
| `pipeline/utils.py` | Log streaming | `web/run_manager.py`, `web/routes/pipeline_api.py` |
| `bootstrap/graph.py` | Bootstrap flow | `bootstrap/running.html`, `web/routes/bootstrap_api.py` |
| `core/executor.py` | All execution | `web/run_manager.py` |
| `core/config_loader.py` | Config display | `bootstrap/review.html`, `bootstrap/done.html` |
| `core/config_generator.py` | Config output | `bootstrap/done.html` |
| `core/analyzer.py` | Analysis results | `bootstrap/review.html` |

## Change Categories

### State Changes (pipeline/state.py)
When new fields are added to `AutoPipeState`:
- Add display logic in the relevant review/done template
- May need new tabs or sections

### New Pipeline Nodes
When a new node is added to the graph:
- Update `running.html` progress display if needed
- Add display section in the appropriate review template
- Update `page_templates.md` mapping

### Executor Changes
When executor behavior changes:
- Update SSE event handling if output format changes
- Update log viewer if log format changes

### New Pages
When adding a new page:
1. Create template in `web/templates/{section}/`
2. Add route in `web/routes/pages.py`
3. Add API route if needed in `web/routes/{section}_api.py`
4. Add sidebar link in `base.html`
5. Update this mapping document

## Prompt Template for UI Generation

When the dev pipeline detects a file change, use this template to construct the LLM prompt:

```
You are an Auto-Pipe UI developer. Generate or modify Jinja2 + HTMX templates.

## Design Guide
{content of ui_principles.md}

## Component Patterns
{content of component_patterns.md}

## Change Context
File changed: {changed_file}
Change summary: {diff_summary}

## Affected UI Files
{list from mapping table}

## Current UI Code
{content of affected template files}

## Task
Update the affected UI templates to reflect the backend changes.
Follow the design guide exactly. Use existing component patterns.
Return only the modified template files.
```
