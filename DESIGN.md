# FundamenTracker Design System

## Design mode

**Operate.** This is a frequently used application UI. Native expectations,
scanability, information density, and accessibility outrank visual expression.
The visual character is a quiet brokerage workspace with the warmth of a
personal research notebook.

## Visual direction

- Flat, calm surfaces with thin separators and very limited elevation.
- Tinted neutrals rather than pure black, white, or generic blue-grey.
- One evergreen accent for primary actions and positive state.
- Red and amber are reserved for negative and warning states.
- No gradients, glass panels, glow effects, hover lift, decorative icon tiles,
  oversized headlines, or nested-card layouts.
- Border radius is restrained. Pills are reserved for tags and compact statuses.

## Typography

The UI uses a humanist platform stack so it remains fast and self-hosted:

```css
font-family: Aptos, "Segoe UI Variable", "Segoe UI", "Helvetica Neue", sans-serif;
```

Numeric data uses tabular figures. The fixed scale is:

| Token | Size | Use |
| --- | ---: | --- |
| `--text-xs` | 0.75rem / 12px | Provenance and secondary metadata only |
| `--text-sm` | 0.875rem / 14px | Controls, table cells, helper text |
| `--text-md` | 1rem / 16px | Body and primary form inputs |
| `--text-lg` | 1.25rem / 20px | Section headings |
| `--text-xl` | 1.75rem / 28px | Product wordmark and key metric value support |
| `--text-display` | clamp(2.25rem, 6vw, 3.75rem) | Explorer metric value only |

Do not use tracked uppercase kickers. Keep paragraphs below roughly 70
characters per line.

## Colour tokens

### Light

| Token | Value |
| --- | --- |
| `--canvas` | `#f4f6f1` |
| `--surface` | `#ffffff` |
| `--surface-subtle` | `#eef1eb` |
| `--surface-strong` | `#e4e8e1` |
| `--text` | `#17201b` |
| `--text-muted` | `#5f6962` |
| `--text-subtle` | `#7c867f` |
| `--line` | `#d9ded7` |
| `--line-strong` | `#bcc5bd` |
| `--accent` | `#087a58` |
| `--accent-hover` | `#056346` |
| `--accent-soft` | `#dff1e9` |
| `--danger` | `#b93830` |
| `--danger-soft` | `#f8e7e4` |
| `--warning` | `#86610a` |
| `--warning-soft` | `#f5edd4` |
| `--focus` | `#1769c2` |

### Dark

| Token | Value |
| --- | --- |
| `--canvas` | `#101511` |
| `--surface` | `#171d18` |
| `--surface-subtle` | `#1d251f` |
| `--surface-strong` | `#263029` |
| `--text` | `#edf2ed` |
| `--text-muted` | `#a3ada5` |
| `--text-subtle` | `#7f8b82` |
| `--line` | `#303a32` |
| `--line-strong` | `#465248` |
| `--accent` | `#65d5aa` |
| `--accent-hover` | `#8be3c0` |
| `--accent-soft` | `#17372b` |
| `--danger` | `#ff8b80` |
| `--danger-soft` | `#3b211f` |
| `--warning` | `#e9c363` |
| `--warning-soft` | `#382f18` |
| `--focus` | `#78b7ff` |

Colour must never be the only indicator of state.

## Spatial system

Use the shared spacing ramp only: 4, 8, 12, 16, 24, 32, and 48px. The main
workspace is capped at 1280px with fluid side padding. Dense rows may use 12px
vertical spacing; forms and sections use 24–32px.

Radius tokens are 6px for controls, 10px for floating elements, and 12px for
primary surfaces. Shadows are reserved for floating autocomplete menus and
transient toasts.

## Layout

- Desktop: compact product header, horizontal primary navigation, then a fluid
  workspace.
- Watchlist: sortable table on wider screens and functionally equivalent cards
  on compact screens.
- Explorer: metric summary beside the chart, stacking below 900px.
- Mobile: primary navigation becomes a bottom bar that respects safe-area
  insets. Forms become a single column and horizontal data strips scroll.
- Do not remove functionality at smaller breakpoints; adapt its presentation.

## Components

### Buttons

Primary buttons are solid accent with verb-first labels. Secondary and quiet
buttons use neutral surfaces. Destructive actions are red but not filled unless
confirmation has already occurred. Icon-only buttons require an accessible label
and native tooltip. All interactive targets are at least 44px on touch devices.

### Forms

Labels are sentence case and remain visible. Help text explains units and
relative-alert behaviour. Focus uses a 3px outer ring. Autocomplete fields use
combobox/listbox semantics and support arrow keys, Enter, and Escape.

### Lists and tables

Use row separators rather than a card per item. Table headers contain real
buttons for sorting. Current values use tabular figures. Actions stay aligned and
use explicit labels where space allows.

### Alerts

An alert row presents, in order: active state, metric rule, current observation,
provenance, and actions. Trigger state includes text or an icon in addition to
colour. Historical charts are optional disclosures and only appear for metrics
with reliable history.

### Data provenance

Source, freshness, and confidence are visually quiet but reachable through a
native tooltip. Stale data is explicitly labelled. Generated research and SEC
facts are secondary disclosures, not competing primary cards.

## Motion

Use only opacity and transform for short feedback transitions (120–180ms). No
bounce, elastic easing, looping decoration, hover lift, or layout-property
animation. Respect `prefers-reduced-motion`.

## Accessibility

- Target WCAG 2.1 AA contrast.
- Preserve visible focus for keyboard users.
- Use semantic headings, landmarks, forms, lists, tables, and live regions.
- Provide skip navigation and descriptive button labels.
- Do not rely on hover for information or interaction.
- Maintain 44px touch targets and prevent horizontal page overflow.

## UX writing

Use concise, calm copy. State what happened and what the user can do next.
Examples:

- “Run scan”, not “Force Scan”.
- “Mark reviewed”, not “Acknowledge”.
- “No signals need review”, not “No open signals.”
- “History is not available for this metric”, not a generic fetch failure.
