# UI Design Principles

Inspired by **Vercel**, **Linear**, **Raycast**, **shadcn/ui** — the gold standard for developer tool UIs.

## Design Philosophy

1. **Rich flat** — Flat surfaces + single-pixel borders. Glass effects only for floating overlays.
2. **Layered depth** — Background lightness increases with elevation, not shadows.
3. **High density** — 13px body, 36px component height, 40px row height.
4. **Borders over shadows** — `1px solid rgba(255,255,255,0.10)` instead of box-shadow.
5. **Monospace where it matters** — IDs, timestamps, paths, code, hashes.
6. **Status through small indicators** — Colored dots, left-borders, pill badges. Not full-card color.
7. **150ms transitions** — Subtle, not sluggish. Hover = border-color change.

## Architecture

- **Backend**: FastAPI (port 8502) — JSON API + SSE
- **Frontend**: Next.js App Router (port 3100) — React + Tailwind CSS
- **Fonts**: Inter (sans) + JetBrains Mono (mono)
- **Real-time**: SSE via `useSSE` custom hook

## Color System

### Background Layers

```css
--bg-base:    #0A0A0C   /* Level 0 — page */
--bg-surface: #111114   /* Level 1 — cards, sidebar */
--bg-raised:  #1A1A1F   /* Level 2 — hover, popovers */
--bg-overlay: #222228   /* Level 3 — dropdowns, active */
```

### Borders (Opacity-based)

```css
--border-subtle:  rgba(255, 255, 255, 0.06)   /* Dividers */
--border-default: rgba(255, 255, 255, 0.10)   /* Cards, inputs */
--border-strong:  rgba(255, 255, 255, 0.16)   /* Focus, hover */
```

### Text (3 levels only)

```css
--text-primary:   #EDEDEF   /* Headings, primary */
--text-secondary: #8E8E93   /* Body, descriptions */
--text-tertiary:  #5A5A5E   /* Labels, placeholders */
```

### Status / Accent

```css
--status-running: #3B82F6   /* Blue — active */
--status-success: #22C55E   /* Green — passed */
--status-error:   #EF4444   /* Red — failed */
--status-warning: #F59E0B   /* Amber — attention */
--status-pending: #71717A   /* Zinc — waiting */
--accent-purple:  #A855F7
--accent-cyan:    #06B6D4
```

### Badge Pattern

```css
success:  bg rgba(34,197,94,0.15), color #4ADE80
error:    bg rgba(239,68,68,0.15), color #F87171
running:  bg rgba(59,130,246,0.15), color #60A5FA
warning:  bg rgba(245,158,11,0.15), color #FBBF24
pending:  bg var(--bg-overlay), color var(--text-tertiary)
```

## Typography

- **Sans**: Inter (400, 500, 600)
- **Mono**: JetBrains Mono
- Body: 13px, `--text-secondary`
- Headings: `font-semibold`, `tracking-tight` (-0.02em), `--text-primary`
- Labels: `text-[11px] font-medium uppercase tracking-[0.05em]`, `--text-tertiary`

## Spacing & Sizing

- Border radius: sm=4px, md=6px, lg=8px, xl=12px
- Component height: 36px (buttons, inputs)
- Row height: 40px (tables, sidebar items 34px)
- Page padding: p-8 (32px)
- Card padding: 16-20px

## Hover & Transitions

```
Card:             border-color → border-strong
Button (primary): opacity → 0.9
Button (secondary): border-color → border-strong, color → text-primary
Sidebar item:     bg → bg-raised, color → text-primary
Table/log row:    bg → rgba(255,255,255,0.03)
Tab:              color → text-secondary
All: transition 150ms ease
```

## Glow Effects (Accent elements only)

```css
/* Active card */
border-color: rgba(59,130,246,0.3);
box-shadow: 0 0 0 1px rgba(59,130,246,0.1), 0 0 40px -10px rgba(59,130,246,0.15);

/* Focus ring */
box-shadow: 0 0 0 2px var(--bg-base), 0 0 0 4px rgba(59,130,246,0.3);
```

## Skeleton Loading

```css
background: linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-raised) 50%, var(--bg-surface) 75%);
background-size: 200% 100%;
animation: shimmer 1.5s infinite;
```

## Glassmorphism (Overlays only)

```css
background: rgba(17,17,20,0.85);
backdrop-filter: blur(16px) saturate(150%);
border: 1px solid rgba(255,255,255,0.08);
border-radius: var(--radius-xl);
box-shadow: 0 25px 50px -12px rgba(0,0,0,0.6);
```

## Button Variants

```
Primary:     bg #EDEDEF, color #0A0A0C, h 36px — Vercel style inverted
Secondary:   bg transparent, border border-default, color text-secondary
Ghost:       no border, color text-tertiary
Destructive: bg rgba(239,68,68,0.15), color #F87171, border rgba(239,68,68,0.2)
```
