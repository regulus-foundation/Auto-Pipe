# Page Templates

## Template Hierarchy

```
base.html
├── bootstrap/
│   ├── input.html          # Project path form + existing project buttons
│   ├── running.html         # SSE log stream + progress
│   ├── review.html          # Analysis results + approve/reject
│   └── done.html            # Config generation results
├── pipeline/
│   ├── input.html           # Project select + requirements textarea
│   ├── running.html         # SSE log stream + progress + messages
│   ├── design_review.html   # Design spec + approve/reject
│   ├── code_review.html     # Review tabs + code viewer + approve/reject
│   └── done.html            # Deliverables + source code
├── examples/
│   └── index.html           # Tab-based example browser
└── error.html               # Generic error page
```

## Base Template Structure

Every page extends `base.html` which provides:
- `<head>`: Tailwind CDN, HTMX, Alpine.js, custom CSS
- Sidebar navigation with active state via `nav_active` variable
- `{% block content %}` for main content area
- `{% block scripts %}` for page-specific JavaScript

## Page Types

### Input Page
- Form with validation
- No SSE/HTMX needed
- POST to `/api/{type}/start`
- Server responds with 303 redirect to running page

### Running Page
- SSE connection on page load (`x-init="connect()"`)
- Log viewer (terminal style)
- Progress indicator
- Auto-redirect on phase change event

### Review Page
- Static content display (data comes from run.state)
- Tabbed interface for multiple data views
- Action bar at bottom: approve / reject with feedback / cancel
- POST forms to `/api/{type}/{run_id}/approve` or `/reject`

### Done Page
- Success banner
- Collapsible logs/deliverables
- Navigation to restart or review

## Route-Template Mapping

| Route | Template | Data Source |
|-------|----------|-------------|
| `GET /bootstrap` | `bootstrap/input.html` | `_get_existing_analyses()` |
| `GET /bootstrap/{id}/running` | `bootstrap/running.html` | `run_manager.get_run(id)` |
| `GET /bootstrap/{id}/review` | `bootstrap/review.html` | `run.state` (scan_result, deep_analysis) |
| `GET /bootstrap/{id}/done` | `bootstrap/done.html` | `run.state` (gen_result) |
| `GET /pipeline` | `pipeline/input.html` | `_get_configured_projects()` |
| `GET /pipeline/{id}/running` | `pipeline/running.html` | `run_manager.get_run(id)` |
| `GET /pipeline/{id}/design-review` | `pipeline/design_review.html` | `run.state` (design_spec) |
| `GET /pipeline/{id}/code-review` | `pipeline/code_review.html` | `run.state` (reviews, source_code) |
| `GET /pipeline/{id}/done` | `pipeline/done.html` | `run.state` (deliverables, source_code) |

## SSE Event Protocol

Events sent from backend to frontend via `/api/{type}/{run_id}/stream`:

| Event | Data | Action |
|-------|------|--------|
| `log` | `string` | Append to logs array |
| `status` | `{node, step, progress}` | Update progress indicator |
| `message` | `{text}` | Append to messages array |
| `phase` | `{phase, redirect}` | `window.location.href = redirect` |
| `error` | `{message}` | Display error, close SSE |
| `done` | `{}` | Close SSE connection |
| `ping` | `""` | Keep-alive (every 30s) |
