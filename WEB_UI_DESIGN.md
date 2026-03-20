# Auto-Pipe Web UI Design

The Web UI is the **control tower** of the Auto-Pipe system.
All pipeline execution, decision-making, and monitoring happens through the web.

---

## 1. Design Philosophy

Inspired by **Vercel**, **Linear**, **Raycast**, and **shadcn/ui** — the current gold standard for developer tool UIs.

### Core Principles

1. **Rich flat** — Flat surfaces with single-pixel borders for structure. Glass effects only for floating overlays.
2. **Layered depth** — Background lightness increases with elevation (not shadows).
3. **High density** — 13-14px body text, 36px row heights. Developer tools need more content per screen than consumer apps.
4. **Borders over shadows** — Dark mode shadows barely register. Use `1px solid rgba(255,255,255,0.06)` instead.
5. **Monospace where it matters** — IDs, timestamps, URLs, paths, code, hashes.
6. **Status through color** — Small colored indicators (dots, left-borders, badges), not full-card color fills.
7. **Keyboard-first** — Command palette (Cmd+K), keyboard shortcuts visible in UI.

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend API | FastAPI (port 8502) | JSON REST + SSE for real-time streaming |
| Frontend | Next.js App Router (port 3100) | React + Tailwind CSS |
| Fonts | Inter + JetBrains Mono | UI / Code |
| Real-time | SSE (Server-Sent Events) | Pipeline log streaming via `useSSE` hook |
| Proxy | Next.js rewrites | `/api/*` → `localhost:8502` |

---

## 3. Color System

### Background Layers (Elevation through lightness)

```css
--bg-base:      #0A0A0C;    /* Level 0 — page background */
--bg-surface:   #111114;    /* Level 1 — cards, sidebar, panels */
--bg-raised:    #1A1A1F;    /* Level 2 — popovers, hover states */
--bg-overlay:   #222228;    /* Level 3 — dropdowns, modals, active states */
```

### Borders (Opacity-based for consistency)

```css
--border-subtle:  rgba(255, 255, 255, 0.06);   /* Dividers, separators */
--border-default: rgba(255, 255, 255, 0.10);   /* Cards, inputs, panels */
--border-strong:  rgba(255, 255, 255, 0.16);   /* Focused inputs, hover cards */
```

### Text Hierarchy (3 levels only)

```css
--text-primary:   #EDEDEF;   /* Headings, primary content */
--text-secondary: #8E8E93;   /* Body text, descriptions */
--text-tertiary:  #5A5A5E;   /* Labels, placeholders, muted */
```

### Accent / Status Colors

```css
/* Pipeline status */
--status-pending:  #71717A;   /* Zinc-500 — waiting */
--status-running:  #3B82F6;   /* Blue-500 — active, in progress */
--status-success:  #22C55E;   /* Green-500 — passed, complete */
--status-error:    #EF4444;   /* Red-500 — failed */
--status-warning:  #F59E0B;   /* Amber-500 — warning, attention */

/* Accent */
--accent-primary:  #3B82F6;   /* Blue — primary actions, links, progress */
--accent-purple:   #A855F7;   /* Purple — info, metrics */
--accent-cyan:     #06B6D4;   /* Cyan — build, deploy */
```

### Status Badge Pattern (Transparent background + bright foreground)

```css
.badge-success  { background: rgba(34, 197, 94, 0.15);  color: #4ADE80; }
.badge-error    { background: rgba(239, 68, 68, 0.15);  color: #F87171; }
.badge-running  { background: rgba(59, 130, 246, 0.15); color: #60A5FA; }
.badge-warning  { background: rgba(245, 158, 11, 0.15); color: #FBBF24; }
.badge-pending  { background: rgba(255, 255, 255, 0.06); color: #71717A; }
```

---

## 4. Typography

### Font Stack

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', ui-monospace, monospace;
```

### Scale

| Token | Size | Usage |
|-------|------|-------|
| `text-xs` | 12px | Badges, labels, timestamps |
| `text-sm` | 13px | Body text, table cells, descriptions |
| `text-base` | 14px | Primary content, inputs |
| `text-lg` | 18px | Section headers |
| `text-xl` | 20px | Page subtitles |
| `text-2xl` | 24px | Page titles |
| `text-3xl` | 30px | Dashboard hero numbers |

### Weight

| Weight | Usage |
|--------|-------|
| 400 (normal) | Body text, descriptions |
| 500 (medium) | Navigation items, labels, buttons |
| 600 (semibold) | Headings, section titles |

### Style Rules

- Headings: `font-semibold`, `tracking-tight` (`letter-spacing: -0.02em`) — Linear style
- Body: `font-normal`, `leading-relaxed` (`line-height: 1.5`)
- Labels: `text-xs font-medium uppercase tracking-wide` in `--text-tertiary`
- Monospace: use for all IDs, timestamps, file paths, URLs, hashes, code snippets

---

## 5. Spacing & Layout

### Grid System (4px base)

```
4px  = gap-1    (tight icon padding)
8px  = gap-2    (between inline elements)
12px = gap-3    (input internal padding, small gaps)
16px = gap-4    (card padding, standard gap)
20px = gap-5    (comfortable card padding)
24px = gap-6    (section padding)
32px = gap-8    (between page sections)
48px = gap-12   (major layout gaps)
```

### Component Heights (Consistent)

| Element | Height |
|---------|--------|
| Button | 36px |
| Input | 36px |
| Sidebar item | 34px |
| Table row | 40px |
| Top bar | 56px |

### Border Radius

```css
--radius-sm:   4px;     /* Badges, small chips */
--radius-md:   6px;     /* Buttons, inputs */
--radius-lg:   8px;     /* Cards, panels */
--radius-xl:   12px;    /* Modals, large containers */
--radius-full: 9999px;  /* Avatars, pills, circular elements */
```

Keep radii small (6-8px). No overly rounded corners — sharp and professional.

### Page Layout

```
+--sidebar(240px)--+--content(fluid, max-w-6xl, p-8)--+
|                   |                                     |
| Logo              |  Page Title                         |
| Nav items         |  Description                        |
|                   |                                     |
|                   |  [Stats Grid: 4-5 metric cards]     |
|                   |                                     |
|                   |  [Main Content Card / Tabs]         |
|                   |                                     |
|                   |  [Action Bar]                       |
+-------------------+-------------------------------------+
```

---

## 6. Components

### Card

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: border-color 150ms ease;
}
.card:hover {
  border-color: var(--border-strong);
}
```

### Button Variants

```
Primary:      bg: #EDEDEF (white-ish), color: #0A0A0C (black), h: 36px, rounded-md
              → Vercel style: inverted on dark background
Secondary:    bg: transparent, border: 1px solid border-default, color: text-secondary, h: 36px
              → hover: border-strong + text-primary
Ghost:        bg: transparent, no border, color: text-tertiary
              → hover: bg-raised + text-secondary
Destructive:  bg: rgba(239,68,68,0.15), color: #F87171, border: rgba(239,68,68,0.2)
              → hover: bg: rgba(239,68,68,0.25)
```

### Input

```css
.input {
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 13px;
  padding: 0 12px;
  height: 36px;
  outline: none;
  transition: border-color 150ms ease;
}
.input:focus {
  border-color: var(--border-strong);
  box-shadow: 0 0 0 2px var(--bg-base), 0 0 0 4px rgba(59,130,246,0.3);
}
.input::placeholder {
  color: var(--text-tertiary);
}
```

### Tabs (Linear/shadcn style)

```css
.tab-list {
  display: flex;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-base);
}
.tab {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
  transition: all 150ms;
}
.tab:hover { color: var(--text-secondary); }
.tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-primary);
  background: var(--bg-surface);
}
```

### Badge (Pill-shaped status indicator)

```css
.badge {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
/* Prepend a colored dot */
.badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
```

### Metric Card

```css
.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}
.metric-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}
.metric-value {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  /* color: assigned per metric */
}
```

### Log Viewer (Terminal)

```css
.log-viewer {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  background: #0A0A0C;
  padding: 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  overflow-y: auto;
  max-height: 480px;
}
.log-line {
  display: flex;
  padding: 1px 0;
}
.log-line:hover {
  background: rgba(255, 255, 255, 0.03);
}
.log-line-number {
  color: var(--text-tertiary);
  user-select: none;
  min-width: 4ch;
  text-align: right;
  margin-right: 16px;
}
```

### Code File Viewer (Collapsible)

```css
.file-block {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.file-header {
  background: var(--bg-raised);
  padding: 10px 16px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 150ms;
}
.file-header:hover { background: var(--bg-overlay); }
.file-content {
  background: #0A0A0C;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  color: #D4D4D8;
  overflow-x: auto;
  max-height: 480px;
}
```

### Progress Indicator

```css
.progress-bar {
  width: 100%;
  height: 3px;
  background: var(--bg-overlay);
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent-primary);
  border-radius: 2px;
  transition: width 500ms ease;
}
```

### Pipeline Stage Indicator

```css
.stage {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
}
.stage.active {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.08);
}
.stage.complete {
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.08);
}
.stage.error {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}
.stage-connector {
  width: 2px;
  height: 20px;
  background: var(--border-default);
  margin-left: 19px;
}
.stage-connector.complete { background: var(--status-success); }
```

---

## 7. Hover & Transitions

All interactive elements use `transition: all 150ms ease`.

| Element | Hover Effect |
|---------|-------------|
| Card | `border-color: var(--border-strong)` |
| Button (primary) | `opacity: 0.9` |
| Button (secondary) | `border-color: var(--border-strong)`, `color: var(--text-primary)` |
| Sidebar item | `background: var(--bg-raised)`, `color: var(--text-primary)` |
| Table row | `background: rgba(255,255,255,0.03)` |
| Log line | `background: rgba(255,255,255,0.03)` |
| Tab | `color: var(--text-secondary)` |

### Glow Effects (Accent elements only)

```css
/* Active card with blue glow */
.card-active {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.1),
              0 0 40px -10px rgba(59, 130, 246, 0.15);
}

/* Focus ring (inputs, buttons) */
.focus-ring:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--bg-base), 0 0 0 4px rgba(59, 130, 246, 0.3);
}
```

### Skeleton Loading

```css
.skeleton {
  background: linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-raised) 50%, var(--bg-surface) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## 8. Glassmorphism (Overlays only)

Used **only** for command palette, modals, and dropdown menus — not for content surfaces.

```css
.glass-overlay {
  background: rgba(17, 17, 20, 0.85);
  backdrop-filter: blur(16px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-xl);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
}
```

### Command Palette (Cmd+K)

```css
.command-palette {
  width: 560px;
  max-height: 400px;
  background: rgba(17, 17, 20, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-xl);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
}
.command-input {
  height: 48px;
  font-size: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 16px;
}
.command-item {
  height: 40px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: var(--radius-md);
}
.command-item:hover { background: rgba(255, 255, 255, 0.06); }
```

---

## 9. Markdown / Prose Rendering

```css
.prose {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}
.prose h1, .prose h2, .prose h3, .prose h4 {
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.prose code {
  background: var(--bg-raised);
  color: #F472B6;  /* Pink for inline code */
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.85em;
}
.prose pre {
  background: #0A0A0C;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 12px;
}
.prose table {
  border-collapse: collapse;
  width: 100%;
}
.prose thead { background: var(--bg-surface); }
.prose th, .prose td {
  border: 1px solid var(--border-default);
  padding: 8px 12px;
  font-size: 13px;
}
.prose th {
  font-weight: 600;
  color: var(--text-primary);
}
.prose tbody tr:hover { background: rgba(255, 255, 255, 0.03); }
```

---

## 10. Page Structure

### Routes

| Route | Page | Description |
|-------|------|-------------|
| `/bootstrap` | Input | Enter project path or select existing |
| `/bootstrap/[runId]/running` | Running | SSE log stream + progress |
| `/bootstrap/[runId]/review` | Review | Analysis tabs + metrics + approve |
| `/bootstrap/[runId]/done` | Done | Generated config summary |
| `/history` | History | Execution history + project logs viewer |
| `/pipeline` | Input | Select project + enter requirements + queue status |
| `/pipeline/[runId]/running` | Running | SSE log stream + progress |
| `/pipeline/[runId]/design-review` | Design Review | Design markdown + approve |
| `/pipeline/[runId]/code-review` | Code Review | Review tabs + code viewer + approve |
| `/pipeline/[runId]/done` | Done | Deliverables + generated code |

### API Endpoints

Key API patterns:
- `POST /api/{type}/start` → `{ run_id, phase, queue_position }`
- `GET /api/{type}/{runId}/stream` → SSE events (queued runs get position updates until started)
- `GET /api/{type}/{runId}/state` → full state for rendering
- `POST /api/{type}/{runId}/approve-*` → `{ run_id, phase }`
- `GET /api/runs` → list all active/completed runs
- `GET /api/pipeline/queue/{project}` → queue status for a project
- `GET /api/projects/{name}/logs` → list log files
- `GET /api/projects/{name}/logs/{file}` → read log content

### SSE Event Protocol

| Event | Data | Frontend Action |
|-------|------|-----------------|
| `log` | string | Append to `LogViewer` |
| `status` | `{node, step, progress}` | Update `ProgressIndicator` |
| `message` | `{text}` | Append to messages |
| `phase` | `{phase, redirect}` | `router.push(redirect)` |
| `error` | `{message}` | Show error, close SSE |
| `done` | `{}` | Close connection |

---

## 11. Frontend File Structure

```
frontend/src/
+-- app/
|   +-- layout.tsx          # Root shell (Sidebar + main area)
|   +-- globals.css         # Design tokens, prose styles, animations
|   +-- bootstrap/          # Bootstrap pages (input, [runId]/{running,review,done})
|   +-- pipeline/           # Pipeline pages (input+queue, [runId]/{running,design-review,code-review,done})
|   +-- history/            # History page (runs table, project log viewer)
|
+-- components/
|   +-- Sidebar.tsx          # Fixed left nav with icon badges + Cmd+K hint
|   +-- LogViewer.tsx        # Terminal-style log with line numbers + hover
|   +-- ProgressIndicator.tsx # Spinner + label + progress bar
|   +-- MetricCard.tsx       # KPI number + label card
|   +-- Tabs.tsx             # Tab navigation with fade-in animation
|   +-- Markdown.tsx         # react-markdown + remark-gfm renderer
|   +-- CodeViewer.tsx       # Collapsible file viewer with dark code blocks
|   +-- Toast.tsx            # Toast notifications (success/error/info, 4s auto-dismiss)
|   +-- Skeleton.tsx         # Shimmer loading skeletons (card, page)
|   +-- CommandPalette.tsx   # Cmd+K command palette (glassmorphism overlay)
|
+-- lib/
    +-- api.ts               # Fetch helpers
    +-- useSSE.ts            # SSE React hook with auto-reconnect (exponential backoff)
```

---

## 12. Run

```bash
./run.sh
# Starts: Docker (PostgreSQL + Langfuse), Backend API (:8502), Frontend UI (:3100)

# Or separately:
uvicorn web.app:app --host 0.0.0.0 --port 8502 --reload
cd frontend && npx next dev --port 3100

# Open http://localhost:3100
```
