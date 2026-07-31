# FundamenTracker design system

## Direction

A quiet personal research desk: warm graphite surfaces, paper-like text, restrained sage and amber accents, and dense information with enough breathing room to scan. The interface should feel maintained by a careful investor, not assembled from generic dashboard templates.

## Anti-references

Do not use:

- gradient text or purple/cyan gradients;
- glassmorphism, glowing borders, or blurred translucent panels;
- cards nested inside cards without a clear hierarchy;
- every datum presented as a pill;
- icon-only actions where a short label fits;
- all-caps labels or tiny body text;
- hover lifts, bounce motion, or transitions on every property;
- generic headings such as “Unlock your potential” or buttons such as “Continue”.

## Typography

- UI: `Aptos`, `Segoe UI Variable`, `Segoe UI`, system sans-serif.
- Financial values and ticker symbols: system monospace.
- Body text: 15–16px on desktop and never below 14px for essential information.
- Use sentence case. Headings are compact, left-aligned, and functional.
- Numbers use tabular figures.

## Color tokens

- Canvas: `#101416`
- Surface: `#171c1f`
- Raised surface: `#1d2327`
- Border: `#2b3337`
- Primary text: `#edf0e9`
- Secondary text: `#a4ada6`
- Accent: `#d0a45d`
- Positive: `#78b58c`
- Negative: `#d77b76`
- Informational: `#7f9fba`

Color communicates meaning but never carries meaning alone.

## Shape and depth

- Main surfaces use 8–12px radii.
- Small controls use 8px radii.
- Prefer borders and tonal separation to heavy shadows.
- Use one subtle shadow only for overlays, menus, and sticky navigation.

## Layout

- Maximum workspace width: 1360px.
- Desktop: compact product header, sticky view navigation, then one primary work surface.
- Tablet/mobile: single column, horizontally scrollable market strip and tabs, table rows converted to stacked records.
- Keep related controls together and avoid forcing horizontal table scrolling for core work.

## Components

- Primary button: filled accent, dark text, one per local action group.
- Secondary button: neutral border and surface.
- Destructive button: neutral until intent is clear, then red text/background on hover/focus.
- Inputs: visible labels, 44px minimum height, strong focus ring.
- Status: one concise status marker per object; avoid chip soup.
- Empty state: one sentence explaining the state and, where useful, the next action.
- Data quality: quiet inline provenance with a detailed native tooltip.

## Motion

- Use 120–180ms opacity and color transitions only.
- Respect `prefers-reduced-motion`.
- No layout-shifting hover transforms.
